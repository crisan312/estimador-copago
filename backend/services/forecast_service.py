"""
Servicio de predicción de episodios (A9) y seguimiento de resultados.

Dos responsabilidades:
1. Persistir las predicciones de A9-EpisodePredictor (tabla episode_predictions).
2. Outcome tracking: registrar el copago REAL pagado vs. el estimado
   (tabla cost_outcomes) y calcular la precisión del estimador (MAPE).

El outcome tracking es el cimiento que permite que A4 y A9 mejoren con el
tiempo: cada pago real recalibra el modelo.
"""
import json
import logging

from db.database_pg import get_pool

logger = logging.getLogger("copago.forecast")


async def save_episode_prediction(session_hash: str, conversation_id: str | None, prediction) -> None:
    """Persiste una predicción de A9. Falla en silencio para no romper el chat."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO episode_predictions
                    (session_hash, conversation_id, specialty, pathway,
                     expected_min_usd, expected_usd, expected_max_usd, confidence)
                VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8)
                """,
                session_hash,
                conversation_id,
                prediction.specialty,
                json.dumps(prediction.pathway, ensure_ascii=False),
                prediction.escenario_minimo_usd,
                prediction.escenario_probable_usd,
                prediction.escenario_completo_usd,
                prediction.confidence,
            )
    except Exception as exc:
        logger.error("save_episode_prediction failed: %s", exc)


async def record_outcome(
    appointment_id: str,
    actual_usd: float,
    source: str = "payment",
) -> dict:
    """
    Registra el copago REAL pagado y lo compara contra el estimado de la cita.
    Se invoca tras un cobro exitoso (Kushki) — outcome tracking.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            appt = await conn.fetchrow(
                """
                SELECT copay_estimated, conversation_id, session_hash, specialty
                FROM appointments WHERE id = $1
                """,
                appointment_id,
            )
            if not appt:
                return {"recorded": False, "reason": "appointment_not_found"}

            estimated = float(appt["copay_estimated"] or 0.0)
            if estimated <= 0:
                return {"recorded": False, "reason": "no_estimate_to_compare"}

            variance_pct = round(abs(actual_usd - estimated) / estimated * 100, 1)

            await conn.execute(
                """
                INSERT INTO cost_outcomes
                    (session_hash, conversation_id, appointment_id, specialty,
                     estimated_usd, actual_usd, variance_pct, source)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                appt["session_hash"],
                appt["conversation_id"],
                appointment_id,
                appt["specialty"],
                estimated,
                actual_usd,
                variance_pct,
                source,
            )
        return {
            "recorded": True,
            "estimated_usd": round(estimated, 2),
            "actual_usd": round(actual_usd, 2),
            "variance_pct": variance_pct,
        }
    except Exception as exc:
        logger.error("record_outcome failed: %s", exc)
        return {"recorded": False, "reason": "error"}


async def get_accuracy_stats() -> dict:
    """
    Precisión del estimador a partir de los pagos reales registrados.
    MAPE = error porcentual absoluto medio. Precisión = 100 - MAPE.
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            overall = await conn.fetchrow(
                """
                SELECT COUNT(*)          AS n,
                       AVG(variance_pct) AS mape,
                       AVG(estimated_usd) AS avg_estimated,
                       AVG(actual_usd)    AS avg_actual
                FROM cost_outcomes
                """
            )
            by_specialty = await conn.fetch(
                """
                SELECT specialty,
                       COUNT(*)           AS n,
                       AVG(variance_pct)  AS mape
                FROM cost_outcomes
                WHERE specialty IS NOT NULL
                GROUP BY specialty
                ORDER BY n DESC
                LIMIT 15
                """
            )

        n = overall["n"] or 0
        if n == 0:
            return {
                "muestras": 0,
                "mensaje": "Aún no hay pagos reales registrados para medir precisión.",
                "precision_pct": None,
                "mape_pct": None,
                "por_especialidad": [],
            }

        mape = round(float(overall["mape"] or 0), 1)
        return {
            "muestras": n,
            "precision_pct": round(max(0.0, 100.0 - mape), 1),
            "mape_pct": mape,
            "promedio_estimado_usd": round(float(overall["avg_estimated"] or 0), 2),
            "promedio_real_usd": round(float(overall["avg_actual"] or 0), 2),
            "por_especialidad": [
                {
                    "especialidad": r["specialty"],
                    "muestras": r["n"],
                    "mape_pct": round(float(r["mape"] or 0), 1),
                    "precision_pct": round(max(0.0, 100.0 - float(r["mape"] or 0)), 1),
                }
                for r in by_specialty
            ],
        }
    except Exception as exc:
        logger.error("get_accuracy_stats failed: %s", exc)
        return {"muestras": 0, "precision_pct": None, "mape_pct": None, "por_especialidad": [], "error": True}
