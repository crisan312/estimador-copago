"""
APScheduler: recordatorios de citas (24h y 1h antes) y recomendaciones preventivas.
Se inicia en el lifespan de FastAPI y corre en background.
"""
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from db.database_pg import get_pool
from services import whatsapp_service
from services.encryption import decrypt

logger = logging.getLogger("copago.scheduler")

_scheduler: AsyncIOScheduler | None = None


async def _send_pending_reminders():
    """Procesa la cola de notificaciones pendientes."""
    now = datetime.now(timezone.utc)
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT nq.id, nq.user_id, nq.appointment_id, nq.template_name,
                      nq.payload_enc, u.phone_whatsapp
               FROM notifications_queue nq
               JOIN users u ON u.id = nq.user_id
               WHERE nq.status = 'PENDING'
                 AND nq.scheduled_at <= $1
                 AND nq.retry_count < 3
                 AND u.whatsapp_opt_in = TRUE
                 AND u.phone_whatsapp IS NOT NULL
               ORDER BY nq.scheduled_at
               LIMIT 50""",
            now,
        )
        for row in rows:
            try:
                payload = decrypt(bytes(row["payload_enc"]))
                sid = await whatsapp_service.send_whatsapp(
                    row["phone_whatsapp"],
                    row["template_name"],
                    payload,
                )
                if sid:
                    await conn.execute(
                        "UPDATE notifications_queue SET status='SENT', sent_at=NOW(), twilio_sid=$2 WHERE id=$1",
                        row["id"], sid,
                    )
                else:
                    await conn.execute(
                        "UPDATE notifications_queue SET retry_count=retry_count+1 WHERE id=$1",
                        row["id"],
                    )
            except Exception as e:
                logger.error("Error procesando notificación %s: %s", row["id"], e)
                await conn.execute(
                    "UPDATE notifications_queue SET status='FAILED', error_message=$2 WHERE id=$1",
                    row["id"], str(e),
                )


async def _schedule_appointment_reminders():
    """
    Encola recordatorios 24h y 1h antes de cada cita confirmada.
    Corre cada 15 minutos.
    """
    from services.encryption import encrypt
    now = datetime.now(timezone.utc)
    window_24h_start = now + timedelta(hours=23, minutes=30)
    window_24h_end = now + timedelta(hours=24, minutes=30)
    window_1h_start = now + timedelta(minutes=50)
    window_1h_end = now + timedelta(hours=1, minutes=10)

    pool = await get_pool()
    async with pool.acquire() as conn:
        appointments = await conn.fetch(
            """SELECT a.id, a.patient_id, a.specialty, a.hospital_name,
                      a.scheduled_at, a.copay_estimated,
                      a.whatsapp_reminded_24h, a.whatsapp_reminded_1h
               FROM appointments a
               WHERE a.status IN ('PENDING', 'CONFIRMED')
                 AND (
                   (a.scheduled_at BETWEEN $1 AND $2 AND a.whatsapp_reminded_24h = FALSE)
                   OR
                   (a.scheduled_at BETWEEN $3 AND $4 AND a.whatsapp_reminded_1h = FALSE)
                 )""",
            window_24h_start, window_24h_end,
            window_1h_start, window_1h_end,
        )

        for appt in appointments:
            scheduled: datetime = appt["scheduled_at"]
            is_24h = window_24h_start <= scheduled <= window_24h_end and not appt["whatsapp_reminded_24h"]
            is_1h = window_1h_start <= scheduled <= window_1h_end and not appt["whatsapp_reminded_1h"]
            template = "appointment_reminder_24h" if is_24h else "appointment_reminder_1h"
            payload = {
                "specialty": appt["specialty"],
                "hospital": appt["hospital_name"],
                "copay": float(appt["copay_estimated"] or 0),
                "time": scheduled.strftime("%H:%M"),
                "date": scheduled.strftime("%d/%m/%Y"),
            }

            existing = await conn.fetchval(
                "SELECT id FROM notifications_queue WHERE appointment_id=$1 AND template_name=$2 AND status='PENDING'",
                appt["id"], template,
            )
            if not existing:
                await conn.execute(
                    """INSERT INTO notifications_queue
                       (user_id, appointment_id, template_name, payload_enc, scheduled_at)
                       VALUES ($1, $2, $3, $4, NOW())""",
                    appt["patient_id"], appt["id"], template, encrypt(payload),
                )

            # mark as enqueued to avoid duplicates
            if is_24h:
                await conn.execute(
                    "UPDATE appointments SET whatsapp_reminded_24h=TRUE WHERE id=$1", appt["id"],
                )
            elif is_1h:
                await conn.execute(
                    "UPDATE appointments SET whatsapp_reminded_1h=TRUE WHERE id=$1", appt["id"],
                )

    logger.debug("Recordatorios verificados: %d citas procesadas", len(appointments) if appointments else 0)


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="America/Guayaquil")
        _scheduler.add_job(_send_pending_reminders, "interval", minutes=2, id="send_notifications")
        _scheduler.add_job(_schedule_appointment_reminders, "interval", minutes=15, id="schedule_reminders")
    return _scheduler


def start_scheduler():
    sched = get_scheduler()
    if not sched.running:
        sched.start()
        logger.info("Scheduler iniciado — recordatorios WhatsApp activos")


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido")
