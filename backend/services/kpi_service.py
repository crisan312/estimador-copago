"""
KPI Service — métricas agregadas y anónimas por rol.
Todos los datos son agrupados; nunca se expone PII en KPIs.
"""
import logging
from datetime import datetime, timedelta, timezone

from db.database_pg import get_pool

logger = logging.getLogger("copago.kpi")


async def get_patient_kpis(user_id: str) -> dict:
    """KPIs para el paciente: sus propias citas y gastos."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        appts = await conn.fetchrow(
            """SELECT
                COUNT(*) FILTER (WHERE status='COMPLETED') AS completed,
                COUNT(*) FILTER (WHERE status='PENDING' OR status='CONFIRMED') AS upcoming,
                COUNT(*) FILTER (WHERE status='NO_SHOW') AS no_show,
                COALESCE(SUM(copay_estimated) FILTER (WHERE status='COMPLETED'), 0) AS total_copay,
                COALESCE(AVG(copay_estimated) FILTER (WHERE status='COMPLETED'), 0) AS avg_copay
               FROM appointments
               WHERE patient_id = $1
                 AND created_at >= NOW() - INTERVAL '12 months'""",
            user_id,
        )
        monthly = await conn.fetch(
            """SELECT
                DATE_TRUNC('month', scheduled_at) AS month,
                COUNT(*) AS count,
                COALESCE(SUM(copay_estimated), 0) AS total
               FROM appointments
               WHERE patient_id = $1
                 AND status = 'COMPLETED'
                 AND scheduled_at >= NOW() - INTERVAL '6 months'
               GROUP BY 1 ORDER BY 1""",
            user_id,
        )
        next_appt = await conn.fetchrow(
            """SELECT specialty, hospital_name, scheduled_at, copay_estimated
               FROM appointments
               WHERE patient_id = $1 AND status IN ('PENDING','CONFIRMED')
                 AND scheduled_at > NOW()
               ORDER BY scheduled_at LIMIT 1""",
            user_id,
        )
    return {
        "role": "PATIENT",
        "summary": {
            "completed_consultations": int(appts["completed"] or 0),
            "upcoming_appointments": int(appts["upcoming"] or 0),
            "no_show_count": int(appts["no_show"] or 0),
            "total_copay_usd": round(float(appts["total_copay"] or 0), 2),
            "avg_copay_usd": round(float(appts["avg_copay"] or 0), 2),
        },
        "monthly_trend": [
            {"month": str(r["month"])[:7], "count": r["count"], "total_usd": round(float(r["total"]), 2)}
            for r in monthly
        ],
        "next_appointment": {
            "specialty": next_appt["specialty"],
            "hospital": next_appt["hospital_name"],
            "scheduled_at": str(next_appt["scheduled_at"]),
            "copay_estimated": float(next_appt["copay_estimated"] or 0),
        } if next_appt else None,
    }


async def get_doctor_kpis(user_id: str, specialty_area: str | None) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        stats = await conn.fetchrow(
            """SELECT
                COUNT(*) FILTER (WHERE status='COMPLETED') AS attended,
                COUNT(*) FILTER (WHERE status='NO_SHOW') AS no_shows,
                COUNT(*) FILTER (WHERE status IN ('PENDING','CONFIRMED')) AS upcoming,
                COALESCE(AVG(copay_estimated), 0) AS avg_copay
               FROM appointments
               WHERE created_by = $1 OR specialty = $2""",
            user_id, specialty_area or "",
        )
        weekly = await conn.fetch(
            """SELECT DATE_TRUNC('week', scheduled_at) AS week, COUNT(*) AS count
               FROM appointments
               WHERE (created_by=$1 OR specialty=$2)
                 AND scheduled_at >= NOW() - INTERVAL '8 weeks'
               GROUP BY 1 ORDER BY 1""",
            user_id, specialty_area or "",
        )
    return {
        "role": "DOCTOR",
        "summary": {
            "attended": int(stats["attended"] or 0),
            "no_shows": int(stats["no_shows"] or 0),
            "upcoming": int(stats["upcoming"] or 0),
            "avg_copay_usd": round(float(stats["avg_copay"] or 0), 2),
        },
        "weekly_trend": [
            {"week": str(r["week"])[:10], "count": r["count"]} for r in weekly
        ],
    }


async def get_staff_kpis() -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        today_stats = await conn.fetchrow(
            """SELECT
                COUNT(*) FILTER (WHERE status='CONFIRMED') AS confirmed_today,
                COUNT(*) FILTER (WHERE status='COMPLETED') AS completed_today,
                COUNT(*) FILTER (WHERE status='NO_SHOW') AS no_show_today,
                COUNT(*) FILTER (WHERE status='PENDING') AS pending_today
               FROM appointments
               WHERE DATE(scheduled_at AT TIME ZONE 'America/Guayaquil') = CURRENT_DATE""",
        )
        pending_requests = await conn.fetchval(
            "SELECT COUNT(*) FROM data_deletion_requests WHERE status = 'PENDING'",
        )
    return {
        "role": "STAFF",
        "today": {
            "confirmed": int(today_stats["confirmed_today"] or 0),
            "completed": int(today_stats["completed_today"] or 0),
            "no_show": int(today_stats["no_show_today"] or 0),
            "pending": int(today_stats["pending_today"] or 0),
        },
        "pending_arco_requests": int(pending_requests or 0),
    }


async def get_analyst_kpis() -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        volume = await conn.fetch(
            """SELECT DATE_TRUNC('day', created_at) AS day, COUNT(*) AS count
               FROM conversations
               WHERE created_at >= NOW() - INTERVAL '30 days'
               GROUP BY 1 ORDER BY 1""",
        )
        specialty_dist = await conn.fetch(
            """SELECT specialty, COUNT(*) AS count,
                      ROUND(AVG(copay_estimated)::numeric, 2) AS avg_copay
               FROM appointments
               WHERE created_at >= NOW() - INTERVAL '30 days'
               GROUP BY specialty ORDER BY count DESC LIMIT 10""",
        )
        hospital_rank = await conn.fetch(
            """SELECT hospital_name,
                      COUNT(*) AS visits,
                      ROUND(AVG(copay_estimated)::numeric, 2) AS avg_copay,
                      COUNT(*) FILTER (WHERE status='COMPLETED') AS completed
               FROM appointments
               WHERE created_at >= NOW() - INTERVAL '30 days'
               GROUP BY hospital_name ORDER BY visits DESC LIMIT 10""",
        )
        completion_rate = await conn.fetchrow(
            """SELECT
                COUNT(*) FILTER (WHERE state='SUMMARY' OR state='COMPLETED') AS completed,
                COUNT(*) AS total
               FROM conversations
               WHERE created_at >= NOW() - INTERVAL '7 days'""",
        )
        token_usage = await conn.fetchrow(
            """SELECT
                COALESCE(SUM(total_tokens), 0) AS total_tokens,
                COALESCE(AVG(total_tokens), 0) AS avg_tokens
               FROM conversations
               WHERE created_at >= NOW() - INTERVAL '7 days'""",
        )
    rate = 0.0
    if completion_rate["total"] and completion_rate["total"] > 0:
        rate = round(completion_rate["completed"] / completion_rate["total"] * 100, 1)
    return {
        "role": "ANALYST",
        "conversation_volume_30d": [
            {"day": str(r["day"])[:10], "count": r["count"]} for r in volume
        ],
        "specialty_distribution": [
            {"specialty": r["specialty"], "count": r["count"], "avg_copay": float(r["avg_copay"] or 0)}
            for r in specialty_dist
        ],
        "hospital_ranking": [
            {"hospital": r["hospital_name"], "visits": r["visits"],
             "avg_copay": float(r["avg_copay"] or 0), "completed": r["completed"]}
            for r in hospital_rank
        ],
        "chatbot_completion_rate_7d": rate,
        "token_usage_7d": {
            "total": int(token_usage["total_tokens"] or 0),
            "avg_per_conversation": round(float(token_usage["avg_tokens"] or 0), 0),
            "estimated_cost_usd": round(int(token_usage["total_tokens"] or 0) / 1_000_000 * 3.0, 4),
        },
    }


async def get_admin_kpis() -> dict:
    """ADMIN ve todo: analista + sistema + usuarios."""
    analyst = await get_analyst_kpis()
    pool = await get_pool()
    async with pool.acquire() as conn:
        users_by_role = await conn.fetch(
            "SELECT role, COUNT(*) AS count FROM users WHERE is_active=TRUE GROUP BY role",
        )
        active_consents = await conn.fetchval(
            "SELECT COUNT(*) FROM consents WHERE withdrawn_at IS NULL",
        )
        pending_deletions = await conn.fetchval(
            "SELECT COUNT(*) FROM data_deletion_requests WHERE status='PENDING'",
        )
        system_total_conversations = await conn.fetchval("SELECT COUNT(*) FROM conversations")
        system_total_appointments = await conn.fetchval("SELECT COUNT(*) FROM appointments")
    analyst["role"] = "ADMIN"
    analyst["system"] = {
        "users_by_role": {r["role"]: r["count"] for r in users_by_role},
        "active_consents": int(active_consents or 0),
        "pending_arco_deletions": int(pending_deletions or 0),
        "total_conversations": int(system_total_conversations or 0),
        "total_appointments": int(system_total_appointments or 0),
    }
    return analyst


async def get_dpo_kpis() -> dict:
    """DPO: compliance, ARCO, audit trail."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        consents = await conn.fetchrow(
            """SELECT
                COUNT(*) FILTER (WHERE withdrawn_at IS NULL) AS active,
                COUNT(*) FILTER (WHERE withdrawn_at IS NOT NULL) AS withdrawn,
                COUNT(*) FILTER (WHERE consented_at >= NOW() - INTERVAL '7 days') AS new_7d
               FROM consents""",
        )
        arco = await conn.fetchrow(
            """SELECT
                COUNT(*) FILTER (WHERE status='PENDING') AS pending,
                COUNT(*) FILTER (WHERE status='COMPLETED') AS completed,
                COUNT(*) FILTER (WHERE status='REJECTED') AS rejected
               FROM data_deletion_requests""",
        )
        audit_events_24h = await conn.fetch(
            """SELECT event_type, COUNT(*) AS count
               FROM audit_log
               WHERE created_at >= NOW() - INTERVAL '24 hours'
               GROUP BY event_type ORDER BY count DESC""",
        )
        sensitive_accesses = await conn.fetchval(
            """SELECT COUNT(*) FROM audit_log
               WHERE event_type = 'DATA_ACCESSED'
                 AND created_at >= NOW() - INTERVAL '24 hours'""",
        )
    return {
        "role": "DPO",
        "consent_status": {
            "active": int(consents["active"] or 0),
            "withdrawn": int(consents["withdrawn"] or 0),
            "new_last_7_days": int(consents["new_7d"] or 0),
        },
        "arco_requests": {
            "pending": int(arco["pending"] or 0),
            "completed": int(arco["completed"] or 0),
            "rejected": int(arco["rejected"] or 0),
        },
        "audit_events_24h": [
            {"event": r["event_type"], "count": r["count"]} for r in audit_events_24h
        ],
        "sensitive_data_accesses_24h": int(sensitive_accesses or 0),
    }
