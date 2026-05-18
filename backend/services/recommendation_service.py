"""
RecommendationService: genera insights IA en background y los cachea en Redis.
Usa A7-InsightAnalyst con datos agregados (sin PII).
"""
import json
import logging
from datetime import timedelta

from agents.agent_insight import InsightAnalyst
from services.encryption import encrypt, decrypt
from services.redis_store import get_redis
from db.database_pg import get_pool

logger = logging.getLogger("copago.recommendations")

_agent = InsightAnalyst()

ANALYSIS_TYPES = [
    "HOSPITAL_RANKING",
    "COST_OPTIMIZATION",
    "SPECIALTY_TREND",
    "SERVICE_QUALITY",
    "SYSTEM_HEALTH",
]

_CACHE_TTL = 3600  # 1 hora


def _cache_key(analysis_type: str) -> str:
    return f"insight:{analysis_type.lower()}"


async def get_cached_insight(analysis_type: str) -> dict | None:
    r = await get_redis()
    raw = await r.get(_cache_key(analysis_type))
    if not raw:
        return None
    try:
        decrypted = decrypt(raw)
        return decrypted if isinstance(decrypted, dict) else json.loads(decrypted)
    except Exception:
        return None


async def _gather_data_for(analysis_type: str) -> dict:
    """Recopila datos anónimos agregados para el tipo de análisis."""
    from services.kpi_service import get_analyst_kpis
    pool = await get_pool()
    async with pool.acquire() as conn:
        if analysis_type == "HOSPITAL_RANKING":
            rows = await conn.fetch(
                """SELECT hospital_name,
                          COUNT(*) AS visits,
                          ROUND(AVG(copay_estimated)::numeric, 2) AS avg_copay,
                          COUNT(*) FILTER (WHERE status='COMPLETED') AS completed,
                          COUNT(*) FILTER (WHERE status='NO_SHOW') AS no_shows
                   FROM appointments
                   WHERE created_at >= NOW() - INTERVAL '90 days'
                   GROUP BY hospital_name ORDER BY visits DESC""",
            )
            return {"hospitals": [dict(r) for r in rows]}

        elif analysis_type == "COST_OPTIMIZATION":
            rows = await conn.fetch(
                """SELECT specialty, hospital_name,
                          ROUND(AVG(copay_estimated)::numeric, 2) AS avg_copay,
                          COUNT(*) AS visits
                   FROM appointments
                   WHERE created_at >= NOW() - INTERVAL '60 days'
                   GROUP BY specialty, hospital_name
                   ORDER BY specialty, avg_copay""",
            )
            return {"specialty_hospital_matrix": [dict(r) for r in rows]}

        elif analysis_type == "SPECIALTY_TREND":
            rows = await conn.fetch(
                """SELECT specialty,
                          DATE_TRUNC('week', created_at) AS week,
                          COUNT(*) AS count
                   FROM appointments
                   WHERE created_at >= NOW() - INTERVAL '12 weeks'
                   GROUP BY specialty, week ORDER BY specialty, week""",
            )
            return {"weekly_by_specialty": [dict(r) for r in rows]}

        elif analysis_type == "SERVICE_QUALITY":
            states = await conn.fetch(
                """SELECT state, COUNT(*) AS count
                   FROM conversations
                   WHERE created_at >= NOW() - INTERVAL '7 days'
                   GROUP BY state""",
            )
            tokens = await conn.fetchrow(
                """SELECT COALESCE(AVG(total_tokens),0) AS avg_tokens,
                          COALESCE(SUM(total_tokens),0) AS sum_tokens
                   FROM conversations WHERE created_at >= NOW() - INTERVAL '7 days'""",
            )
            return {
                "conversation_states_7d": [dict(r) for r in states],
                "token_stats_7d": {
                    "avg": float(tokens["avg_tokens"]),
                    "total": int(tokens["sum_tokens"]),
                },
            }

        elif analysis_type == "SYSTEM_HEALTH":
            agent_traces = await conn.fetch(
                """SELECT agent_name,
                          COUNT(*) AS calls,
                          COUNT(*) FILTER (WHERE success=FALSE) AS errors,
                          ROUND(AVG(latency_ms)::numeric, 0) AS avg_latency_ms,
                          COALESCE(SUM(input_tokens + output_tokens), 0) AS total_tokens
                   FROM agent_traces
                   WHERE created_at >= NOW() - INTERVAL '24 hours'
                   GROUP BY agent_name ORDER BY calls DESC""",
            )
            return {"agent_performance_24h": [dict(r) for r in agent_traces]}

    return {}


async def generate_insight(analysis_type: str, force: bool = False) -> dict | None:
    if not force:
        cached = await get_cached_insight(analysis_type)
        if cached:
            return cached

    try:
        data = await _gather_data_for(analysis_type)
        result = await _agent.run(analysis_type=analysis_type, data=data)
        if not result.success or not result.data:
            return None

        # cache encrypted
        r = await get_redis()
        await r.setex(_cache_key(analysis_type), _CACHE_TTL, encrypt(result.data))

        # persist to DB
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO recommendations
                   (insight_type, content_enc, score, is_public)
                   VALUES ($1, $2, $3, TRUE)""",
                analysis_type,
                encrypt(result.data),
                result.data.get("score", 0.5),
            )

        logger.info("Insight generado: %s (score=%.2f)", analysis_type, result.data.get("score", 0))
        return result.data

    except Exception as e:
        logger.error("Error generando insight %s: %s", analysis_type, e)
        return None


async def generate_all_insights(force: bool = False) -> dict[str, dict]:
    """Genera todos los tipos de insights. Llamar desde el scheduler o manualmente."""
    results = {}
    for analysis_type in ANALYSIS_TYPES:
        insight = await generate_insight(analysis_type, force=force)
        if insight:
            results[analysis_type] = insight
    return results


async def get_patient_recommendations(session_hash: str, patient_context: dict) -> dict | None:
    """Genera recomendaciones personalizadas para un paciente (datos anónimos)."""
    data = {
        "specialty": patient_context.get("especialidad", ""),
        "copay_estimated": patient_context.get("copago", {}).get("total_estimado", 0),
        "recommended_hospitals": patient_context.get("hospitales", [])[:5],
    }
    result = await _agent.run(analysis_type="PATIENT_INSIGHT", data=data)
    if not result.success:
        return None

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO recommendations (session_hash, insight_type, content_enc, score)
               VALUES ($1, 'PATIENT_INSIGHT', $2, $3)""",
            session_hash, encrypt(result.data), result.data.get("score", 0.5),
        )
    return result.data
