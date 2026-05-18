"""
Router de Administración — gestión de usuarios, compliance, auditoría.
Acceso exclusivo: ADMIN y DPO.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.dependencies import CurrentUser, get_current_user
from db.database_pg import get_pool
from services import audit_service
from db.rls import make_session_hash

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


def _require_admin_or_dpo(current_user: CurrentUser):
    if current_user.role not in ("ADMIN", "DPO"):
        raise HTTPException(403, "Acceso restringido a ADMIN y DPO")


# ── Usuarios ───────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    role: str | None = None,
    is_active: bool | None = None,
):
    _require_admin_or_dpo(current_user)
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, email, role, is_active, phone_whatsapp,
                      whatsapp_opt_in, last_login_at, created_at
               FROM users
               WHERE ($1::text IS NULL OR role = $1)
                 AND ($2::boolean IS NULL OR is_active = $2)
               ORDER BY created_at DESC LIMIT 200""",
            role, is_active,
        )
    return [
        {
            "user_id": str(r["id"]),
            "email": r["email"],
            "role": r["role"],
            "is_active": r["is_active"],
            "has_whatsapp": bool(r["phone_whatsapp"]),
            "whatsapp_opt_in": r["whatsapp_opt_in"],
            "last_login_at": r["last_login_at"].isoformat() if r["last_login_at"] else None,
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


class UpdateUserRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    req: UpdateUserRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    if current_user.role != "ADMIN":
        raise HTTPException(403, "Solo ADMIN puede modificar usuarios")

    valid_roles = {"PATIENT", "STAFF", "DOCTOR", "ANALYST", "ADMIN", "DPO"}
    if req.role and req.role not in valid_roles:
        raise HTTPException(400, f"Rol inválido: {req.role}")

    pool = await get_pool()
    async with pool.acquire() as conn:
        updates = []
        values = []
        idx = 1
        if req.role:
            updates.append(f"role = ${idx}"); values.append(req.role); idx += 1
        if req.is_active is not None:
            updates.append(f"is_active = ${idx}"); values.append(req.is_active); idx += 1
        if updates:
            values.append(user_id)
            await conn.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = ${idx}", *values,
            )

    await audit_service.log_event(
        session_hash=make_session_hash(current_user.user_id),
        event_type=audit_service.AuditEvent.DATA_MODIFIED,
        resource="users",
        resource_id=user_id,
        details={"action": "admin_update", "changes": req.model_dump(exclude_none=True)},
    )
    return {"ok": True}


# ── Auditoría (DPO) ────────────────────────────────────────────────────────

@router.get("/audit-log")
async def get_audit_log(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    event_type: str | None = None,
    limit: int = 100,
):
    _require_admin_or_dpo(current_user)
    if limit > 1000:
        limit = 1000

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, event_type, resource, resource_id, details, created_at
               FROM audit_log
               WHERE ($1::text IS NULL OR event_type = $1)
               ORDER BY created_at DESC LIMIT $2""",
            event_type, limit,
        )
    return [
        {
            "id": r["id"],
            "event_type": r["event_type"],
            "resource": r["resource"],
            "resource_id": r["resource_id"],
            "details": r["details"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


# ── ARCO requests (DPO) ────────────────────────────────────────────────────

@router.get("/arco-requests")
async def list_arco_requests(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    status: str | None = None,
):
    _require_admin_or_dpo(current_user)
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, reason, status, requested_at, processed_at, reject_reason
               FROM data_deletion_requests
               WHERE ($1::text IS NULL OR status = $1)
               ORDER BY requested_at DESC""",
            status,
        )
    return [
        {
            "id": str(r["id"]),
            "reason": r["reason"],
            "status": r["status"],
            "requested_at": r["requested_at"].isoformat(),
            "processed_at": r["processed_at"].isoformat() if r["processed_at"] else None,
        }
        for r in rows
    ]


class ProcessArcoRequest(BaseModel):
    status: str   # COMPLETED | REJECTED
    reject_reason: str | None = None


@router.patch("/arco-requests/{request_id}")
async def process_arco_request(
    request_id: str,
    req: ProcessArcoRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    _require_admin_or_dpo(current_user)
    if req.status not in ("COMPLETED", "REJECTED"):
        raise HTTPException(400, "Estado debe ser COMPLETED o REJECTED")

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE data_deletion_requests
               SET status=$1, processed_at=NOW(), reject_reason=$2
               WHERE id=$3""",
            req.status, req.reject_reason, request_id,
        )
    await audit_service.log_event(
        session_hash=make_session_hash(current_user.user_id),
        event_type=audit_service.AuditEvent.ARCO_REQUEST,
        resource="data_deletion_requests",
        resource_id=request_id,
        details={"action": "process_arco", "new_status": req.status},
    )
    return {"ok": True}


# ── WhatsApp broadcast (ADMIN) ─────────────────────────────────────────────

class BroadcastRequest(BaseModel):
    role_filter: str | None = None   # solo enviar a un rol específico
    template: str
    variables: dict


@router.post("/broadcast/whatsapp")
async def broadcast_whatsapp(
    req: BroadcastRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    if current_user.role != "ADMIN":
        raise HTTPException(403, "Solo ADMIN puede enviar broadcast")

    from services.whatsapp_service import send_whatsapp
    from services.encryption import encrypt

    pool = await get_pool()
    async with pool.acquire() as conn:
        users = await conn.fetch(
            """SELECT id, phone_whatsapp FROM users
               WHERE whatsapp_opt_in = TRUE
                 AND phone_whatsapp IS NOT NULL
                 AND is_active = TRUE
                 AND ($1::text IS NULL OR role = $1)""",
            req.role_filter,
        )
        sent = 0
        for u in users:
            nq_id = await conn.fetchval(
                """INSERT INTO notifications_queue
                   (user_id, template_name, payload_enc, scheduled_at)
                   VALUES ($1, $2, $3, NOW()) RETURNING id""",
                u["id"], req.template, encrypt(req.variables),
            )
            sent += 1

    await audit_service.log_event(
        session_hash=make_session_hash(current_user.user_id),
        event_type=audit_service.AuditEvent.DATA_MODIFIED,
        resource="notifications_queue",
        resource_id=None,
        details={"action": "broadcast", "template": req.template, "recipients": sent},
    )
    return {"ok": True, "queued_messages": sent}
