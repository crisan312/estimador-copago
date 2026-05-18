"""
Endpoints de consentimiento LOPDP.
POST /api/v1/consent        — otorgar consentimiento (previo a cualquier dato de salud)
DELETE /api/v1/consent      — retirar consentimiento (derecho de oposición Art. 18)
GET  /api/v1/consent/status — verificar estado actual
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel
from db.rls import make_session_hash, new_session_id
from services import consent_service, audit_service

router = APIRouter(prefix="/api/v1/consent", tags=["LOPDP — Consentimiento"])


class ConsentRequest(BaseModel):
    accepted: bool
    purposes: list[str] = ["health_estimation", "policy_lookup", "hospital_ranking"]


@router.post("")
async def give_consent(body: ConsentRequest, request: Request):
    if not body.accepted:
        return {"detail": "El consentimiento debe ser afirmativo para usar el servicio."}

    session_id = request.headers.get("X-Session-Id") or new_session_id()
    session_hash = make_session_hash(session_id)
    ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else None)
    ua = request.headers.get("User-Agent")

    version = await consent_service.record_consent(session_hash, ip, ua)

    return {
        "consented": True,
        "version": version,
        "session_id": session_id,
        "purposes": body.purposes,
        "withdrawal_url": "/api/v1/consent",
        "data_rights_url": "/api/v1/my-data",
        "privacy_notice_url": "/privacidad",
        "message": (
            "Has aceptado el tratamiento de tus datos de salud para estimar tu copago médico. "
            "Puedes retirar tu consentimiento en cualquier momento."
        ),
    }


@router.delete("")
async def withdraw_consent(request: Request):
    session_id = request.headers.get("X-Session-Id", "")
    if not session_id:
        return {"detail": "Sesión no encontrada."}
    session_hash = make_session_hash(session_id)
    ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else None)
    await consent_service.withdraw_consent(session_hash, ip)
    return {
        "withdrawn": True,
        "message": "Tu consentimiento ha sido retirado. No procesaremos más tus datos de salud.",
        "note": "Para eliminar todos tus datos, usa DELETE /api/v1/my-data.",
    }


@router.get("/status")
async def consent_status(request: Request):
    session_id = request.headers.get("X-Session-Id", "")
    if not session_id:
        return {"consented": False}
    session_hash = make_session_hash(session_id)
    consented = await consent_service.check_consent(session_hash)
    return {"consented": consented}
