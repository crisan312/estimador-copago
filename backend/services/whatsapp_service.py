"""
WhatsApp via Twilio — templates para Ecuador (LOPDP: no PII en logs).
Si TWILIO_ACCOUNT_SID está vacío, los mensajes se loguean (modo demo).
"""
import logging
from dataclasses import dataclass
from config import settings

logger = logging.getLogger("copago.whatsapp")


@dataclass
class WhatsAppMessage:
    to: str          # E.164 format: +593991234567
    template: str
    variables: dict


TEMPLATES = {
    "appointment_reminder_24h": (
        "🗓️ *CopayAI* — Recordatorio\n\n"
        "Tu cita de *{specialty}* es mañana a las *{time}*.\n"
        "📍 {hospital}\n"
        "💲 Copago estimado: *${copay:.2f}*\n\n"
        "¿Necesitas cancelar o reagendar? Responde CANCELAR."
    ),
    "appointment_reminder_1h": (
        "⏰ *CopayAI* — Tu cita es en 1 hora\n\n"
        "📍 {hospital} — {specialty}\n"
        "💲 Recuerda llevar ${copay:.2f} para el copago.\n\n"
        "¡Buena suerte con tu consulta! 🏥"
    ),
    "appointment_confirmed": (
        "✅ *Cita confirmada — CopayAI*\n\n"
        "Especialidad: *{specialty}*\n"
        "Fecha: *{date}* a las *{time}*\n"
        "Hospital: *{hospital}*\n"
        "Copago estimado: *${copay:.2f}*\n\n"
        "ID: {appointment_id}\n"
        "Gestiona tu cita en: copayai.ec/appointments"
    ),
    "appointment_cancelled": (
        "❌ *Cita cancelada — CopayAI*\n\n"
        "Tu cita de {specialty} del {date} fue cancelada.\n"
        "Para reagendar, visita copayai.ec o responde AGENDAR."
    ),
    "copay_estimate_ready": (
        "💊 *Tu estimado de copago está listo — CopayAI*\n\n"
        "Especialidad: {specialty}\n"
        "Copago estimado: *${copay:.2f}*\n"
        "Hospital más económico: *{best_hospital}*\n\n"
        "Ver detalles completos: copayai.ec/result/{conversation_id}"
    ),
    "monthly_summary": (
        "📊 *Resumen mensual — CopayAI*\n\n"
        "Consultas este mes: *{consultations}*\n"
        "Gasto total en copagos: *${total_copay:.2f}*\n"
        "Deducible restante: *${deductible_remaining:.2f}*\n\n"
        "Ver historial completo: copayai.ec/dashboard"
    ),
    "preventive_reminder": (
        "💙 *Recordatorio preventivo — CopayAI*\n\n"
        "{message}\n\n"
        "Agenda tu consulta: copayai.ec/chat\n"
        "_Para no recibir más recordatorios, responde STOP._"
    ),
    "tramite_update": (
        "🔄 *Actualización de trámite — CopayAI*\n\n"
        "Tu solicitud #{request_id} está en estado: *{status}*\n"
        "{details}\n\n"
        "Más información: copayai.ec/appointments"
    ),
}


def _format_message(template_name: str, variables: dict) -> str:
    template = TEMPLATES.get(template_name, "")
    try:
        return template.format(**variables)
    except KeyError as e:
        logger.warning("WhatsApp template '%s' variable faltante: %s", template_name, e)
        return template


async def send_whatsapp(to: str, template_name: str, variables: dict) -> str | None:
    """
    Envía un mensaje de WhatsApp via Twilio.
    Retorna el SID del mensaje o None si falla.
    """
    body = _format_message(template_name, variables)

    if not settings.twilio_account_sid:
        logger.info("[WhatsApp DEMO] → %s\n%s", to, body)
        return f"DEMO_{template_name}"

    try:
        from twilio.rest import Client
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        msg = client.messages.create(
            from_=settings.twilio_whatsapp_from,
            to=f"whatsapp:{to}",
            body=body,
        )
        logger.info("WhatsApp enviado SID=%s → %s", msg.sid, to)
        return msg.sid
    except Exception as e:
        logger.error("Error enviando WhatsApp a %s: %s", to, e)
        return None


async def send_appointment_confirmed(phone: str, specialty: str, date: str, time: str,
                                     hospital: str, copay: float, appointment_id: str) -> str | None:
    return await send_whatsapp(phone, "appointment_confirmed", {
        "specialty": specialty, "date": date, "time": time,
        "hospital": hospital, "copay": copay, "appointment_id": appointment_id,
    })


async def send_reminder_24h(phone: str, specialty: str, time: str,
                             hospital: str, copay: float) -> str | None:
    return await send_whatsapp(phone, "appointment_reminder_24h", {
        "specialty": specialty, "time": time, "hospital": hospital, "copay": copay,
    })


async def send_reminder_1h(phone: str, specialty: str, hospital: str, copay: float) -> str | None:
    return await send_whatsapp(phone, "appointment_reminder_1h", {
        "specialty": specialty, "hospital": hospital, "copay": copay,
    })


async def send_copay_estimate(phone: str, specialty: str, copay: float,
                               best_hospital: str, conversation_id: str) -> str | None:
    return await send_whatsapp(phone, "copay_estimate_ready", {
        "specialty": specialty, "copay": copay,
        "best_hospital": best_hospital, "conversation_id": conversation_id,
    })


async def send_preventive_reminder(phone: str, message: str) -> str | None:
    return await send_whatsapp(phone, "preventive_reminder", {"message": message})


async def send_tramite_update(phone: str, request_id: str, status_text: str, details: str) -> str | None:
    return await send_whatsapp(phone, "tramite_update", {
        "request_id": request_id, "status": status_text, "details": details,
    })
