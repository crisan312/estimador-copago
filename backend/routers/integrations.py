"""
Router de integraciones externas:
- GET  /api/v1/integrations/health  — estado de todas las integraciones
- POST /api/v1/integrations/webhooks/appointment — push desde HIS hospitalario
- POST /api/v1/integrations/webhooks/policy-update — push desde aseguradora
- POST /api/v1/integrations/copay-payment — cobrar copago vía Kushki
- GET  /api/v1/integrations/verify-identity — verificar cédula vía DINARDAP
"""
import hashlib
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from auth.dependencies import CurrentUser, get_current_user, require_roles
from services import audit_service, forecast_service
from db.rls import make_session_hash
from integrations.fhir import _fhir
from integrations.iess import _iess
from integrations.kushki import _kushki
from integrations.aseguradoras import _aseg
from integrations.dinardap import _dinardap
from integrations.smtp_email import _smtp

logger = logging.getLogger("copago.integrations.router")
router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])


# ── Health ─────────────────────────────────────────────────────────────────

@router.get("/health")
async def integrations_health(
    current_user: Annotated[CurrentUser, Depends(require_roles("ADMIN", "DPO"))]
):
    """Estado de conectividad de todas las integraciones externas."""
    results = {}
    for integration in [_smtp, _fhir, _iess, _kushki, _aseg, _dinardap]:
        results[integration.name] = await integration.health_check()
    return {"integrations": results, "total": len(results)}


# ── Webhook receiver ───────────────────────────────────────────────────────

class WebhookAppointmentPayload(BaseModel):
    external_id: str
    hospital_id: str
    patient_cedula_hash: str
    specialty: str
    scheduled_at: str
    status: str
    copay_usd: float | None = None


@router.post("/webhooks/appointment", status_code=status.HTTP_202_ACCEPTED)
async def webhook_appointment_update(
    payload: WebhookAppointmentPayload,
    request: Request,
    x_webhook_secret: Annotated[str | None, Header()] = None,
):
    """
    Endpoint para que hospitales/HIS notifiquen cambios en citas.
    Requiere header X-Webhook-Secret con el secreto configurado.
    """
    from config import settings
    expected = settings.webhook_secret
    if expected and x_webhook_secret != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Webhook secret inválido")

    logger.info(
        "Webhook appointment: hospital=%s specialty=%s status=%s",
        payload.hospital_id, payload.specialty, payload.status,
    )
    await audit_service.log_event(
        session_hash=make_session_hash(payload.patient_cedula_hash),
        event_type=audit_service.AuditEvent.DATA_MODIFIED,
        resource="appointments_webhook",
        resource_id=payload.external_id,
        details={"source": "hospital_webhook", "status": payload.status},
    )
    return {"received": True, "external_id": payload.external_id}


class PolicyUpdatePayload(BaseModel):
    policy_number_hash: str
    insurer: str
    changes: dict
    effective_date: str


@router.post("/webhooks/policy-update", status_code=status.HTTP_202_ACCEPTED)
async def webhook_policy_update(
    payload: PolicyUpdatePayload,
    x_webhook_secret: Annotated[str | None, Header()] = None,
):
    """Recibe notificaciones de cambio en pólizas desde las aseguradoras."""
    from config import settings
    if settings.webhook_secret and x_webhook_secret != settings.webhook_secret:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Webhook secret inválido")

    logger.info("Webhook policy-update: insurer=%s effective=%s", payload.insurer, payload.effective_date)
    # Invalidar caché de póliza en Redis
    from services.redis_store import get_redis
    r = await get_redis()
    cache_key = f"policy:{payload.policy_number_hash}"
    await r.delete(cache_key)
    return {"received": True, "cache_invalidated": True}


# ── Copago digital (Kushki) ───────────────────────────────────────────────

class CopayPaymentRequest(BaseModel):
    kushki_token: str = Field(..., description="Token de un solo uso generado en el frontend con Kushki.js")
    appointment_id: str
    amount_usd: float = Field(..., gt=0, lt=10000)
    description: str = "Copago médico CopayAI"


@router.post("/copay-payment")
async def charge_copay(
    req: CopayPaymentRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """
    Cobra el copago del paciente usando su token Kushki.
    El frontend debe generar el token usando kushki.js antes de llamar aquí.
    """
    result = await _kushki.charge_copay(
        token=req.kushki_token,
        amount_usd=req.amount_usd,
        appointment_id=req.appointment_id,
        patient_email=current_user.email,
        description=req.description,
    )
    if not result.success:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, result.error)

    await audit_service.log_event(
        session_hash=make_session_hash(current_user.user_id),
        event_type=audit_service.AuditEvent.DATA_MODIFIED,
        resource="payments",
        resource_id=req.appointment_id,
        details={
            "amount_usd": req.amount_usd,
            "ticket": result.data.get("ticketNumber"),
            "demo": result.demo_mode,
        },
    )

    # Outcome tracking: registra el pago real vs. el copago estimado de la cita.
    # Alimenta la métrica de precisión del estimador (GET /api/v1/kpi/accuracy).
    outcome = await forecast_service.record_outcome(req.appointment_id, req.amount_usd)
    return {**result.data, "outcome_tracking": outcome}


# ── Verificación de identidad ─────────────────────────────────────────────

class VerifyIdentityRequest(BaseModel):
    cedula_hash: str = Field(..., min_length=64, max_length=64,
                             description="SHA-256(cédula) — 64 hex chars, nunca la cédula en claro")


@router.post("/verify-identity")
async def verify_identity(
    req: VerifyIdentityRequest,
    current_user: Annotated[CurrentUser, Depends(require_roles("ADMIN", "STAFF", "DPO"))],
):
    """
    Verifica existencia de una cédula via DINARDAP.
    Solo recibe SHA-256(cédula) en el body — nunca la cédula en texto claro,
    ni el hash en la URL (evita que quede en logs de acceso). LOPDP Art. 26.
    """
    result = await _dinardap.verify_identity(req.cedula_hash)
    await audit_service.log_event(
        session_hash=make_session_hash(current_user.user_id),
        event_type=audit_service.AuditEvent.DATA_ACCESSED,
        resource="dinardap_verify",
        details={"demo": result.demo_mode},
    )
    return result.data


# ── FHIR slots disponibles ────────────────────────────────────────────────

@router.get("/fhir/slots")
async def get_fhir_slots(
    specialty_code: str,
    hospital_id: str,
    date: str,
    current_user: Annotated[CurrentUser, Depends(require_roles("ADMIN", "STAFF", "DOCTOR"))],
):
    """Consulta slots de cita disponibles en el HIS hospitalario (HL7 FHIR)."""
    result = await _fhir.get_available_slots(specialty_code, hospital_id, date)
    if not result.success:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, result.error)
    return result.data


# ── Coordinación de beneficios IESS ──────────────────────────────────────

class BenefitsRequest(BaseModel):
    cedula_hash: str
    specialty: str
    costo_consulta_usd: float
    copago_privado_usd: float


@router.post("/iess/coordinate-benefits")
async def coordinate_iess_benefits(
    req: BenefitsRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """
    Calcula copago real cuando el paciente tiene IESS + seguro privado.
    El seguro privado cubre el diferencial que IESS no cubre.
    """
    result = await _iess.coordinate_benefits(
        req.cedula_hash, req.specialty, req.costo_consulta_usd, req.copago_privado_usd
    )
    if not result.success:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, result.error)
    return result.data
