"""
Gestión de consentimiento — LOPDP Art. 7, 8 y 9.
Datos de salud son 'datos sensibles' — requieren consentimiento EXPLÍCITO,
LIBRE, ESPECÍFICO e INFORMADO previo a cualquier tratamiento.
"""
from datetime import datetime, timezone
from db.database_pg import get_pool
from services import redis_store, audit_service
from services.encryption import hash_identifier
from config import settings


async def record_consent(
    session_hash: str,
    ip: str | None = None,
    user_agent: str | None = None,
) -> str:
    ip_hash = hash_identifier(ip) if ip else None
    ua_hash = hash_identifier(user_agent) if user_agent else None

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO consents (session_hash, consent_version, ip_hash, user_agent_hash, purposes)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (session_hash, consent_version)
            DO UPDATE SET withdrawn_at = NULL
            """,
            session_hash,
            settings.consent_version,
            ip_hash,
            ua_hash,
            ["health_estimation", "policy_lookup", "hospital_ranking"],
        )

    await redis_store.set_consent(session_hash, settings.consent_version)

    await audit_service.log_event(
        session_hash=session_hash,
        event_type=audit_service.AuditEvent.CONSENT_GIVEN,
        resource="consents",
        ip=ip,
        details={"version": settings.consent_version, "purposes": ["health_estimation", "policy_lookup", "hospital_ranking"]},
    )

    return settings.consent_version


async def withdraw_consent(session_hash: str, ip: str | None = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE consents
            SET withdrawn_at = NOW()
            WHERE session_hash = $1 AND consent_version = $2 AND withdrawn_at IS NULL
            """,
            session_hash,
            settings.consent_version,
        )

    await redis_store.revoke_consent(session_hash)

    await audit_service.log_event(
        session_hash=session_hash,
        event_type=audit_service.AuditEvent.CONSENT_WITHDRAWN,
        resource="consents",
        ip=ip,
    )


async def check_consent(session_hash: str) -> bool:
    """Verifica consentimiento vigente (Redis primero, luego DB)."""
    if await redis_store.has_consent(session_hash):
        return True

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id FROM consents
            WHERE session_hash = $1
              AND consent_version = $2
              AND withdrawn_at IS NULL
            """,
            session_hash,
            settings.consent_version,
        )
    if row:
        await redis_store.set_consent(session_hash, settings.consent_version)
        return True
    return False
