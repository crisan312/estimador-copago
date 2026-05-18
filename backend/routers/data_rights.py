"""
Derechos ARCO — LOPDP Arts. 14-19.
GET    /api/v1/my-data  — Acceso (Art. 14)
DELETE /api/v1/my-data  — Cancelación/Supresión (Art. 16)
Plazo legal de respuesta: 15 días hábiles (Art. 21) — aquí es inmediato.
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel
from db.rls import make_session_hash
from services import data_subject_service, audit_service

router = APIRouter(prefix="/api/v1/my-data", tags=["LOPDP — Derechos ARCO"])


class DeletionRequest(BaseModel):
    reason: str | None = None


@router.get("")
async def get_my_data(request: Request):
    session_id = request.headers.get("X-Session-Id", "")
    if not session_id:
        return {"detail": "Sesión no encontrada. Inicia una nueva consulta."}

    session_hash = make_session_hash(session_id)

    await audit_service.log_event(
        session_hash=session_hash,
        event_type=audit_service.AuditEvent.ARCO_REQUEST,
        resource="my_data",
        ip=request.headers.get("X-Forwarded-For", request.client.host if request.client else None),
        details={"right": "ACCESO"},
    )

    return await data_subject_service.get_my_data(session_hash)


@router.delete("")
async def delete_my_data(body: DeletionRequest, request: Request):
    session_id = request.headers.get("X-Session-Id", "")
    if not session_id:
        return {"detail": "Sesión no encontrada."}

    session_hash = make_session_hash(session_id)
    ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else None)

    await audit_service.log_event(
        session_hash=session_hash,
        event_type=audit_service.AuditEvent.ARCO_REQUEST,
        resource="my_data",
        ip=ip,
        details={"right": "SUPRESION", "reason": body.reason},
    )

    return await data_subject_service.request_deletion(session_hash, body.reason, ip)
