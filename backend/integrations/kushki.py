"""
Integración Kushki — pasarela de pagos líder en Ecuador y Latinoamérica.
https://kushki.com/ec/

Permite cobrar el copago directamente en la plataforma (copago digital).
Soporta: tarjetas de crédito/débito, transferencias bancarias, efectivo (Efectivo),
         cash (PagoEfectivo), SafetiPay.

Sin KUSHKI_PUBLIC_KEY configurado: modo demo (simula transacciones).

Documentación: https://docs.kushkipagos.com
"""
import logging
import uuid
from config import settings
from .base import BaseIntegration, IntegrationResult

logger = logging.getLogger("copago.integrations.kushki")


class KushkiIntegration(BaseIntegration):
    name = "kushki"

    def is_available(self) -> bool:
        return bool(settings.kushki_private_key)

    @property
    def _base_url(self) -> str:
        if settings.kushki_sandbox:
            return "https://api-uat.kushkipagos.com"
        return "https://api.kushkipagos.com"

    async def health_check(self) -> dict:
        base = await super().health_check()
        base["sandbox"] = settings.kushki_sandbox
        base["currency"] = "USD"
        base["country"] = "EC"
        return base

    async def charge_copay(
        self,
        token: str,
        amount_usd: float,
        appointment_id: str,
        patient_email: str,
        description: str,
    ) -> IntegrationResult:
        """
        Cobra el copago usando un token de Kushki obtenido en el frontend.
        El token es de un solo uso y expira en 15 minutos.
        """
        if not self.is_available():
            tx_id = f"DEMO-{uuid.uuid4().hex[:12].upper()}"
            logger.info("[DEMO KUSHKI] Cargo simulado: $%.2f para %s | appointment=%s | tx=%s",
                       amount_usd, patient_email, appointment_id, tx_id)
            return self._demo_result({
                "ticketNumber": tx_id,
                "amount": {"subtotalIva": 0, "subtotalIva0": round(amount_usd, 2), "ice": 0, "iva": 0, "currency": "USD"},
                "status": "APPROVED",
                "approvalCode": "DEMO123",
                "appointmentId": appointment_id,
                "_demo": True,
            })

        try:
            import httpx
            payload = {
                "token": token,
                "amount": {
                    "subtotalIva": 0,
                    "subtotalIva0": round(amount_usd, 2),
                    "ice": 0,
                    "iva": 0,
                    "currency": "USD",
                },
                "fullResponse": True,
                "metadata": {
                    "appointmentId": appointment_id,
                    "email": patient_email,
                    "description": description,
                },
            }
            headers = {
                "Private-Merchant-Id": settings.kushki_private_key,
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient(timeout=15.0) as c:
                r = await c.post(f"{self._base_url}/card/v1/charges", json=payload, headers=headers)
                data = r.json()
                if r.status_code == 201 and "ticketNumber" in data:
                    logger.info("Kushki cargo OK: ticket=%s amount=$%.2f", data["ticketNumber"], amount_usd)
                    return IntegrationResult(success=True, data=data)
                return self._error_result(data.get("message", "Error en el cargo"))
        except Exception as e:
            return self._error_result(str(e))

    async def void_charge(self, ticket_number: str) -> IntegrationResult:
        """Reversa un cargo (dentro del mismo día)."""
        if not self.is_available():
            return self._demo_result({"reversed": True, "ticketNumber": ticket_number, "_demo": True})
        try:
            import httpx
            headers = {"Private-Merchant-Id": settings.kushki_private_key}
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.delete(f"{self._base_url}/card/v1/void/{ticket_number}", headers=headers)
                r.raise_for_status()
                return IntegrationResult(success=True, data=r.json())
        except Exception as e:
            return self._error_result(str(e))

    async def refund_charge(self, ticket_number: str, amount_usd: float) -> IntegrationResult:
        """Reembolso parcial o total (para cancelaciones de cita)."""
        if not self.is_available():
            return self._demo_result({"refunded": True, "amount": amount_usd, "_demo": True})
        try:
            import httpx
            headers = {"Private-Merchant-Id": settings.kushki_private_key, "Content-Type": "application/json"}
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.post(
                    f"{self._base_url}/card/v1/refund/{ticket_number}",
                    json={"amount": round(amount_usd, 2)},
                    headers=headers,
                )
                r.raise_for_status()
                return IntegrationResult(success=True, data=r.json())
        except Exception as e:
            return self._error_result(str(e))


_kushki = KushkiIntegration()
