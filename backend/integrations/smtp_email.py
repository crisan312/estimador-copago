"""
Integración SMTP — notificaciones por correo electrónico.

Uso principal:
- Notificaciones ARCO (plazo 15 días LOPDP Art. 21)
- Alertas DPO de accesos a datos sensibles
- Recordatorios de cita (alternativa a WhatsApp)
- Confirmación de eliminación de datos

Sin credenciales SMTP: modo demo (log en consola).
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from config import settings
from .base import BaseIntegration, IntegrationResult

logger = logging.getLogger("copago.integrations.smtp")


class SmtpEmailIntegration(BaseIntegration):
    name = "smtp_email"

    def is_available(self) -> bool:
        return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)

    async def health_check(self) -> dict:
        base = await super().health_check()
        if self.is_available():
            try:
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as s:
                    s.ehlo()
                    if settings.smtp_tls:
                        s.starttls()
                base["status"] = "connected"
            except Exception as e:
                base["status"] = "error"
                base["error"] = str(e)
        return base

    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        body_html: str,
        body_text: str = "",
        cc: Optional[list[str]] = None,
        reply_to: Optional[str] = None,
    ) -> IntegrationResult:
        recipients = [to] if isinstance(to, str) else to

        if not self.is_available():
            logger.info(
                "[DEMO EMAIL] To=%s | Subject=%s | Body_preview=%s...",
                recipients, subject, body_html[:80],
            )
            return self._demo_result({"to": recipients, "subject": subject, "mode": "demo"})

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject
            if cc:
                msg["Cc"] = ", ".join(cc)
            if reply_to:
                msg["Reply-To"] = reply_to

            if body_text:
                msg.attach(MIMEText(body_text, "plain", "utf-8"))
            msg.attach(MIMEText(body_html, "html", "utf-8"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as s:
                s.ehlo()
                if settings.smtp_tls:
                    s.starttls()
                if settings.smtp_user:
                    s.login(settings.smtp_user, settings.smtp_password)
                all_recipients = recipients + (cc or [])
                s.sendmail(settings.smtp_from_email, all_recipients, msg.as_string())

            logger.info("Email enviado a %s: %s", recipients, subject)
            return IntegrationResult(success=True, data={"to": recipients, "subject": subject})

        except Exception as e:
            return self._error_result(str(e))

    # ── Templates ──────────────────────────────────────────────────────────

    async def send_arco_notification(self, to: str, request_type: str, deadline_days: int = 15) -> IntegrationResult:
        """Notifica al titular que su solicitud ARCO fue recibida (LOPDP Art. 21)."""
        subject = f"CopayAI — Solicitud de {request_type} recibida"
        html = f"""
        <div style="font-family:sans-serif;max-width:600px;margin:auto">
          <h2 style="color:#2563eb">CopayAI Ecuador</h2>
          <p>Hemos recibido su solicitud de <strong>{request_type}</strong> de datos personales.</p>
          <p>Según el Art. 21 de la LOPDP, tenemos <strong>{deadline_days} días hábiles</strong>
             para procesarla y notificarle el resultado.</p>
          <p>Si tiene preguntas, contáctenos en: <a href="mailto:{settings.dpo_email}">{settings.dpo_email}</a></p>
          <hr>
          <small>CopayAI — {settings.controller_name} | RUC: {settings.controller_ruc}</small>
        </div>
        """
        return await self.send_email(to, subject, html)

    async def send_arco_resolution(self, to: str, request_type: str, approved: bool, reason: str = "") -> IntegrationResult:
        """Notifica la resolución de una solicitud ARCO."""
        status = "aprobada" if approved else "rechazada"
        subject = f"CopayAI — Solicitud de {request_type} {status}"
        color = "#16a34a" if approved else "#dc2626"
        html = f"""
        <div style="font-family:sans-serif;max-width:600px;margin:auto">
          <h2 style="color:#2563eb">CopayAI Ecuador</h2>
          <p>Su solicitud de <strong>{request_type}</strong> ha sido
             <strong style="color:{color}">{status}</strong>.</p>
          {f'<p>Motivo: {reason}</p>' if reason else ''}
          <p>Contacto DPO: <a href="mailto:{settings.dpo_email}">{settings.dpo_email}</a></p>
        </div>
        """
        return await self.send_email(to, subject, html)

    async def send_appointment_reminder(self, to: str, specialty: str, hospital: str, date: str, copay: float) -> IntegrationResult:
        """Recordatorio de cita por email."""
        subject = f"CopayAI — Recordatorio de cita: {specialty}"
        html = f"""
        <div style="font-family:sans-serif;max-width:600px;margin:auto">
          <h2 style="color:#2563eb">Recordatorio de Cita Médica</h2>
          <table>
            <tr><td><strong>Especialidad:</strong></td><td>{specialty}</td></tr>
            <tr><td><strong>Hospital:</strong></td><td>{hospital}</td></tr>
            <tr><td><strong>Fecha/Hora:</strong></td><td>{date}</td></tr>
            <tr><td><strong>Copago estimado:</strong></td><td>${copay:.2f} USD</td></tr>
          </table>
          <p>Lleve su carnet de seguro y número de póliza.</p>
        </div>
        """
        return await self.send_email(to, subject, html)

    async def send_dpo_alert(self, event_type: str, details: str) -> IntegrationResult:
        """Alerta al DPO sobre eventos de datos sensibles."""
        subject = f"[ALERTA DPO] CopayAI — {event_type}"
        html = f"""
        <div style="font-family:sans-serif;max-width:600px;margin:auto">
          <h2 style="color:#dc2626">Alerta de Protección de Datos</h2>
          <p><strong>Evento:</strong> {event_type}</p>
          <p><strong>Detalle:</strong> {details}</p>
          <p>Revise el audit log en el panel DPO.</p>
        </div>
        """
        return await self.send_email(settings.dpo_email, subject, html)


_smtp = SmtpEmailIntegration()


async def send_email(to: str | list[str], subject: str, body_html: str, **kwargs) -> IntegrationResult:
    return await _smtp.send_email(to, subject, body_html, **kwargs)

async def send_arco_notification(to: str, request_type: str) -> IntegrationResult:
    return await _smtp.send_arco_notification(to, request_type)

async def send_arco_resolution(to: str, request_type: str, approved: bool, reason: str = "") -> IntegrationResult:
    return await _smtp.send_arco_resolution(to, request_type, approved, reason)

async def send_dpo_alert(event_type: str, details: str) -> IntegrationResult:
    return await _smtp.send_dpo_alert(event_type, details)
