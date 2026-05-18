"""
Router de citas médicas — agendamiento, seguimiento, WhatsApp automático.
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth.dependencies import CurrentUser, get_current_user, require_roles
from db.database_pg import get_pool
from services import whatsapp_service
from services.encryption import encrypt, decrypt
from services import audit_service
from db.rls import make_session_hash

router = APIRouter(prefix="/api/v1/appointments", tags=["Appointments"])


class CreateAppointmentRequest(BaseModel):
    specialty: str
    hospital_name: str
    scheduled_at: datetime
    copay_estimated: float | None = None
    notes: str | None = None
    patient_id: str | None = None          # STAFF puede crear para otro paciente
    conversation_id: str | None = None


class UpdateAppointmentRequest(BaseModel):
    status: str | None = None              # CONFIRMED | CANCELLED | COMPLETED | NO_SHOW
    scheduled_at: datetime | None = None
    notes: str | None = None
    copay_estimated: float | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_appointment(
    req: CreateAppointmentRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    # STAFF puede crear para cualquier paciente; PATIENT solo para sí mismo
    patient_id = req.patient_id if current_user.role in ("STAFF", "ADMIN") else current_user.user_id
    appt_id = str(uuid.uuid4())

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO appointments
               (id, patient_id, specialty, hospital_name, scheduled_at,
                copay_estimated, notes_enc, status, created_by)
               VALUES ($1, $2, $3, $4, $5, $6, $7, 'CONFIRMED', $8)""",
            appt_id,
            patient_id,
            req.specialty,
            req.hospital_name,
            req.scheduled_at,
            req.copay_estimated,
            encrypt({"notes": req.notes or ""}) if req.notes else None,
            current_user.user_id,
        )

        # Obtener teléfono para WhatsApp
        patient = await conn.fetchrow(
            "SELECT phone_whatsapp, whatsapp_opt_in FROM users WHERE id = $1", patient_id,
        )

    await audit_service.log_event(
        session_hash=make_session_hash(current_user.user_id),
        event_type=audit_service.AuditEvent.DATA_MODIFIED,
        resource="appointments",
        resource_id=appt_id,
        details={"action": "create", "specialty": req.specialty},
    )

    # Enviar confirmación WhatsApp si tiene opt-in
    if patient and patient["whatsapp_opt_in"] and patient["phone_whatsapp"]:
        await whatsapp_service.send_appointment_confirmed(
            phone=patient["phone_whatsapp"],
            specialty=req.specialty,
            date=req.scheduled_at.strftime("%d/%m/%Y"),
            time=req.scheduled_at.strftime("%H:%M"),
            hospital=req.hospital_name,
            copay=req.copay_estimated or 0.0,
            appointment_id=appt_id,
        )

    return {"appointment_id": appt_id, "status": "CONFIRMED"}


@router.get("")
async def list_appointments(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    status_filter: str | None = None,
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if current_user.role in ("ADMIN", "STAFF"):
            query = """SELECT id, patient_id, specialty, hospital_name,
                              scheduled_at, copay_estimated, status, created_at
                       FROM appointments
                       WHERE ($1::text IS NULL OR status = $1)
                       ORDER BY scheduled_at DESC LIMIT 100"""
            rows = await conn.fetch(query, status_filter)
        else:
            query = """SELECT id, specialty, hospital_name,
                              scheduled_at, copay_estimated, status, created_at
                       FROM appointments
                       WHERE patient_id = $1
                         AND ($2::text IS NULL OR status = $2)
                       ORDER BY scheduled_at DESC"""
            rows = await conn.fetch(query, current_user.user_id, status_filter)

    return [
        {
            "id": str(r["id"]),
            "specialty": r["specialty"],
            "hospital_name": r["hospital_name"],
            "scheduled_at": r["scheduled_at"].isoformat() if r["scheduled_at"] else None,
            "copay_estimated": float(r["copay_estimated"]) if r["copay_estimated"] else None,
            "status": r["status"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


@router.get("/{appointment_id}")
async def get_appointment(
    appointment_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM appointments WHERE id = $1", appointment_id,
        )
    if not row:
        raise HTTPException(404, "Cita no encontrada")
    if current_user.role not in ("ADMIN", "STAFF", "DOCTOR") and str(row["patient_id"]) != current_user.user_id:
        raise HTTPException(403, "Sin permiso para ver esta cita")

    notes = None
    if row["notes_enc"]:
        try:
            notes = decrypt(bytes(row["notes_enc"])).get("notes")
        except Exception:
            pass

    return {
        "id": str(row["id"]),
        "specialty": row["specialty"],
        "hospital_name": row["hospital_name"],
        "scheduled_at": row["scheduled_at"].isoformat() if row["scheduled_at"] else None,
        "copay_estimated": float(row["copay_estimated"]) if row["copay_estimated"] else None,
        "status": row["status"],
        "notes": notes,
        "created_at": row["created_at"].isoformat(),
    }


@router.patch("/{appointment_id}")
async def update_appointment(
    appointment_id: str,
    req: UpdateAppointmentRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    valid_statuses = {"CONFIRMED", "CANCELLED", "COMPLETED", "NO_SHOW", "PENDING"}
    if req.status and req.status not in valid_statuses:
        raise HTTPException(400, f"Estado inválido. Opciones: {', '.join(valid_statuses)}")

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT patient_id, status, specialty, hospital_name, copay_estimated FROM appointments WHERE id = $1", appointment_id)
        if not row:
            raise HTTPException(404, "Cita no encontrada")
        if current_user.role not in ("ADMIN", "STAFF") and str(row["patient_id"]) != current_user.user_id:
            raise HTTPException(403, "Sin permiso para modificar esta cita")

        updates = []
        values = []
        idx = 1
        if req.status:
            updates.append(f"status = ${idx}"); values.append(req.status); idx += 1
        if req.scheduled_at:
            updates.append(f"scheduled_at = ${idx}"); values.append(req.scheduled_at); idx += 1
        if req.copay_estimated is not None:
            updates.append(f"copay_estimated = ${idx}"); values.append(req.copay_estimated); idx += 1
        if req.notes is not None:
            updates.append(f"notes_enc = ${idx}"); values.append(encrypt({"notes": req.notes})); idx += 1

        if updates:
            values.append(appointment_id)
            await conn.execute(
                f"UPDATE appointments SET {', '.join(updates)} WHERE id = ${idx}",
                *values,
            )

        # WhatsApp si se cancela
        if req.status == "CANCELLED":
            patient = await conn.fetchrow("SELECT phone_whatsapp, whatsapp_opt_in FROM users WHERE id=$1", row["patient_id"])
            if patient and patient["whatsapp_opt_in"] and patient["phone_whatsapp"]:
                await whatsapp_service.send_whatsapp(
                    patient["phone_whatsapp"], "appointment_cancelled",
                    {"specialty": row["specialty"], "date": "la fecha programada"},
                )

    await audit_service.log_event(
        session_hash=make_session_hash(current_user.user_id),
        event_type=audit_service.AuditEvent.DATA_MODIFIED,
        resource="appointments",
        resource_id=appointment_id,
        details={"action": "update", "new_status": req.status},
    )
    return {"ok": True, "appointment_id": appointment_id}
