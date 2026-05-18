"""
Auditoría inmutable de accesos a datos personales.
LOPDP Art. 37 + SSyP Res. JB-2012-2248: trazabilidad de todos los accesos
a datos sensibles. La tabla audit_log tiene reglas PostgreSQL que bloquean
UPDATE y DELETE — garantiza inmutabilidad del registro.
"""
import json
import logging
from db.database_pg import get_pool
from services.encryption import hash_identifier

logger = logging.getLogger("copago.audit")

# Tipos de eventos auditables
class AuditEvent:
    CONSENT_GIVEN       = "CONSENT_GIVEN"
    CONSENT_WITHDRAWN   = "CONSENT_WITHDRAWN"
    DATA_ACCESSED       = "DATA_ACCESSED"
    DATA_MODIFIED       = "DATA_MODIFIED"
    DATA_DELETED        = "DATA_DELETED"
    AGENT_INVOKED       = "AGENT_INVOKED"
    POLICY_RETRIEVED    = "POLICY_RETRIEVED"
    ARCO_REQUEST        = "ARCO_REQUEST"
    SESSION_EXPIRED     = "SESSION_EXPIRED"
    AUTH_FAILED         = "AUTH_FAILED"


async def log_event(
    session_hash: str,
    event_type: str,
    resource: str,
    resource_id: str | None = None,
    ip: str | None = None,
    details: dict | None = None,
):
    ip_hash = hash_identifier(ip) if ip else None
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_log (session_hash, event_type, resource, resource_id, ip_hash, details)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                """,
                session_hash,
                event_type,
                resource,
                resource_id,
                ip_hash,
                # JSON válido — str(dict) produce comillas simples y rompe el cast ::jsonb
                json.dumps(details or {}, ensure_ascii=False, default=str),
            )
    except Exception as exc:
        # El audit log falla silenciosamente para no interrumpir la experiencia
        # pero se registra en el logger de sistema
        logger.error("Audit log write failed: %s", exc)


async def get_audit_log(session_hash: str) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT event_type, resource, resource_id, created_at
            FROM audit_log
            WHERE session_hash = $1
            ORDER BY created_at DESC
            LIMIT 200
            """,
            session_hash,
        )
    return [dict(r) for r in rows]
