"""
CopayAI — Estimador Agéntico de Copago y Cobertura
LOPDP (Ecuador) · SSyP · OWASP
RBAC · WhatsApp (Twilio) · KPIs · IA Recomendaciones
"""
import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db.database_pg import run_migrations, close_pool
from services.redis_store import close_redis
from orchestrator.conversation_memory import get_conversation_meta
from services import data_subject_service
from services.hospital_service import get_all
from services.report_generator import build_summary
from services.notification_scheduler import start_scheduler, stop_scheduler
from db.rls import make_session_hash

from middleware.request_logger import RequestLoggerMiddleware
from middleware.security_headers import SecurityHeadersMiddleware
from middleware.rate_limiter import RateLimiterMiddleware
from middleware.consent_middleware import ConsentMiddleware
from routers import chat, consent, data_rights, hospitals, auth, appointments, kpi, recommendations, admin, integrations

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("copago.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_migrations()
    start_scheduler()
    logger.info(
        "CopayAI v%s — DB OK | Scheduler OK | env=%s",
        settings.app_version, settings.environment,
    )
    yield
    stop_scheduler()
    await close_pool()
    await close_redis()
    logger.info("CopayAI shutdown — connections closed")


app = FastAPI(
    title="CopayAI — Estimador de Copago",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)

# Orden de middlewares (último registrado = primero en ejecutar)
app.add_middleware(ConsentMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Session-Id", "Authorization"],
    expose_headers=["X-Session-Id"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(consent.router)
app.include_router(data_rights.router)
app.include_router(hospitals.router)
app.include_router(appointments.router)
app.include_router(kpi.router)
app.include_router(recommendations.router)
app.include_router(admin.router)
app.include_router(integrations.router)


# ── Conversation helpers ───────────────────────────────────────────────────

@app.get("/api/v1/conversation/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    x_session_id: Annotated[str | None, Header()] = None,
):
    data = await get_conversation_meta(conversation_id)
    if not data:
        raise HTTPException(404, "Conversación no encontrada o expirada")
    return {
        "conversation_id": conversation_id,
        "state": data.get("state"),
        "turns_count": len(data.get("turns", [])),
        "specialty": data.get("patient_context", {}).get("especialidad"),
        "total_tokens": data.get("total_tokens", 0),
    }


@app.get("/api/v1/conversation/{conversation_id}/summary")
async def get_summary(conversation_id: str):
    from orchestrator.conversation_memory import ConversationMemory
    data = await get_conversation_meta(conversation_id)
    if not data:
        raise HTTPException(404, "Conversación no encontrada")
    mem = ConversationMemory(session_id="summary-read", conversation_id=conversation_id)
    mem.state = data.get("state", "COMPLETED")
    mem.patient_context = data.get("patient_context", {})
    mem.turns = data.get("turns", [])
    mem.total_tokens = data.get("total_tokens", 0)
    return build_summary(mem)


# ── Privacy notice (LOPDP Art. 13) ───────────────────────────────────────

@app.get("/api/v1/privacy-info")
async def privacy_info():
    return {
        "controller": {
            "nombre": settings.controller_name,
            "ruc": settings.controller_ruc,
            "dpo_email": settings.dpo_email,
        },
        "datos_tratados": [
            {"categoria": "Síntomas de salud", "tipo": "Dato sensible (LOPDP Art. 26)", "base_legal": "Consentimiento explícito (Art. 7)"},
            {"categoria": "Número de póliza de seguro", "tipo": "Dato personal financiero", "base_legal": "Consentimiento explícito (Art. 7)"},
            {"categoria": "Historial de conversaciones", "tipo": "Dato personal + sensible", "base_legal": "Consentimiento explícito (Art. 7)"},
        ],
        "derechos_arco": {
            "acceso": "GET /api/v1/my-data",
            "supresion": "DELETE /api/v1/my-data",
            "oposicion": "DELETE /api/v1/consent",
            "plazo": "15 días hábiles (LOPDP Art. 21)",
        },
        "retencion": f"{settings.data_retention_days} días desde la creación",
        "transferencias_internacionales": "No se realizan transferencias internacionales de datos.",
        "organismos_control": ["DINARDAP", "Superintendencia de Seguros y Pensiones (SSyP)", "MSP"],
        "cifrado": "AES-128-CBC (Fernet) en reposo + TLS 1.3 en tránsito.",
        "version_aviso": "1.0 — vigente desde 2026-05-16",
    }


# ── Health ────────────────────────────────────────────────────────────────

@app.get("/api/v1/health")
async def health():
    from agents.base_agent import BaseAgent
    from db.database_pg import get_pool
    from services.redis_store import get_redis
    from services.notification_scheduler import get_scheduler

    cb = BaseAgent._circuit_breaker
    db_ok = redis_ok = True

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        db_ok = False

    try:
        r = await get_redis()
        await r.ping()
    except Exception:
        redis_ok = False

    sched = get_scheduler()

    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "version": settings.app_version,
        "environment": settings.environment,
        "services": {
            "postgresql": "up" if db_ok else "down",
            "redis": "up" if redis_ok else "down",
            "circuit_breaker": "OPEN" if cb.is_open else "CLOSED",
            "scheduler": "running" if sched.running else "stopped",
            "whatsapp": "twilio" if settings.twilio_account_sid else "demo_mode",
            "notion": "enabled" if settings.notion_enabled else "disabled (demo mode)",
        },
        "agents": [
            "A1-SymptomInterpreter", "A2-SpecialtySuggester", "A3-PolicyLookup",
            "A4-CopayCalculator", "A5-HospitalRanker", "A6-SummaryWriter",
            "A7-InsightAnalyst", "A8-CopayValidator (determinista, no-LLM)",
            "A9-EpisodePredictor (predictivo, no-LLM)",
        ],
        "compliance": {
            "lopdp": "compliant",
            "cifrado_en_reposo": "Fernet AES-128-CBC",
            "audit_log": "inmutable",
            "derechos_arco": "implementados",
            "rbac": "6 roles activos",
            "whatsapp_opt_in": "required",
        },
        "model": settings.claude_model,
    }
