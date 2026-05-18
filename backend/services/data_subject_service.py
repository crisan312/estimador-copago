"""
Derechos ARCO del titular de datos — LOPDP Arts. 14-19:
  A — Acceso: obtener copia de todos sus datos
  R — Rectificación: corregir datos inexactos (fuera de scope clínico)
  C — Cancelación/Supresión: eliminar todos sus datos
  O — Oposición: oponerse al tratamiento (= retirar consentimiento)

Plazo legal: responder en máximo 15 días hábiles (LOPDP Art. 21).
"""
from datetime import datetime, timezone
from db.database_pg import get_pool
from services import audit_service
from services.encryption import decrypt
from config import settings


async def get_my_data(session_hash: str) -> dict:
    """ARCO — Acceso: retorna todos los datos del titular."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Conversaciones (decifradas)
        conv_rows = await conn.fetch(
            "SELECT id, state, total_tokens, patient_context_enc, turns_enc, created_at, expires_at FROM conversations WHERE session_hash = $1",
            session_hash,
        )
        conversations = []
        for row in conv_rows:
            ctx = decrypt(row["patient_context_enc"]) if row["patient_context_enc"] else {}
            turns = decrypt(row["turns_enc"]) if row["turns_enc"] else []
            conversations.append({
                "id": str(row["id"]),
                "state": row["state"],
                "total_tokens": row["total_tokens"],
                "patient_context": ctx,
                "turns_count": len(turns) if isinstance(turns, list) else 0,
                "created_at": row["created_at"].isoformat(),
                "expires_at": row["expires_at"].isoformat(),
            })

        # Consentimientos
        consent_rows = await conn.fetch(
            "SELECT consent_version, purposes, consented_at, withdrawn_at FROM consents WHERE session_hash = $1",
            session_hash,
        )

        # Historial de copagos
        copay_rows = await conn.fetch(
            "SELECT specialty, copay_estimated_usd, coverage_pct, confidence, created_at FROM copay_history WHERE session_hash = $1",
            session_hash,
        )

        # Audit log (las últimas 50 entradas)
        audit_rows = await conn.fetch(
            "SELECT event_type, resource, created_at FROM audit_log WHERE session_hash = $1 ORDER BY created_at DESC LIMIT 50",
            session_hash,
        )

    await audit_service.log_event(
        session_hash=session_hash,
        event_type=audit_service.AuditEvent.DATA_ACCESSED,
        resource="data_subject_rights",
        details={"right": "ACCESO", "conversations_count": len(conversations)},
    )

    return {
        "session_hash": session_hash[:8] + "...",  # truncado por seguridad
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "controller": {
            "nombre": settings.controller_name,
            "dpo_email": settings.dpo_email,
            "legal_basis": "Consentimiento explícito (LOPDP Art. 7)",
        },
        "conversations": conversations,
        "consents": [dict(r) for r in consent_rows],
        "copay_history": [dict(r) for r in copay_rows],
        "audit_entries": [dict(r) for r in audit_rows],
        "retention_policy": f"Los datos se eliminan automáticamente a los {settings.data_retention_days} días de creación.",
        "arco_rights": {
            "acceso": "GET /api/v1/my-data",
            "supresion": "DELETE /api/v1/my-data",
            "oposicion": "DELETE /api/v1/consent",
            "contacto_dpo": settings.dpo_email,
            "plazo_legal": "15 días hábiles (LOPDP Art. 21)",
        },
    }


async def request_deletion(session_hash: str, reason: str | None = None, ip: str | None = None) -> dict:
    """ARCO — Cancelación/Supresión: elimina todos los datos del titular."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Registrar solicitud
        await conn.execute(
            """
            INSERT INTO data_deletion_requests (session_hash, reason, status)
            VALUES ($1, $2, 'PROCESSING')
            ON CONFLICT (session_hash) DO UPDATE SET
                status = 'PROCESSING',
                reason = EXCLUDED.reason,
                requested_at = NOW()
            """,
            session_hash,
            reason,
        )

        # Eliminar datos de conversaciones, pólizas y copagos
        # El audit_log NO se elimina (inmutable + obligación legal de 7 años)
        deleted_conv = await conn.fetchval(
            "DELETE FROM conversations WHERE session_hash = $1 RETURNING COUNT(*)", session_hash
        ) or 0

        await conn.execute("DELETE FROM policy_cache WHERE session_hash = $1", session_hash)
        await conn.execute("DELETE FROM copay_history WHERE session_hash = $1", session_hash)

        # Marcar consentimiento como retirado (no eliminar — evidencia legal)
        await conn.execute(
            "UPDATE consents SET withdrawn_at = NOW() WHERE session_hash = $1 AND withdrawn_at IS NULL",
            session_hash,
        )

        # Completar solicitud
        await conn.execute(
            "UPDATE data_deletion_requests SET status = 'COMPLETED', processed_at = NOW() WHERE session_hash = $1",
            session_hash,
        )

    # Limpiar Redis
    from services import redis_store
    await redis_store.revoke_consent(session_hash)

    await audit_service.log_event(
        session_hash=session_hash,
        event_type=audit_service.AuditEvent.DATA_DELETED,
        resource="all_personal_data",
        ip=ip,
        details={"right": "SUPRESION", "conversations_deleted": deleted_conv, "reason": reason},
    )

    return {
        "status": "COMPLETED",
        "message": "Todos tus datos personales han sido eliminados.",
        "note": "El registro de auditoría se conserva de forma anónima por obligación legal (SSyP Res. JB-2012-2248).",
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }
