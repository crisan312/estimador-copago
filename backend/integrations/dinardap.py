"""
Integración DINARDAP — Dirección Nacional de Registro de Datos Públicos (Ecuador).
https://www.dinardap.gob.ec/

Permite verificar la identidad del ciudadano a partir de su cédula o pasaporte.
Requerida para: verificar nombre en póliza, prevenir fraude en solicitudes ARCO.

IMPORTANTE (LOPDP):
- Solo se envía SHA-256(cédula), nunca la cédula en texto claro.
- La respuesta se descarta después de la verificación — no almacenamos datos DINARDAP.
- Requiere convenio interinstitucional con el Registro Civil / DINARDAP.

Sin credenciales: modo demo que retorna verificación exitosa.
"""
import logging
from config import settings
from .base import BaseIntegration, IntegrationResult

logger = logging.getLogger("copago.integrations.dinardap")


class DINARDAPIntegration(BaseIntegration):
    name = "dinardap"

    def is_available(self) -> bool:
        return bool(settings.dinardap_api_key and settings.dinardap_api_url)

    async def verify_identity(self, cedula_hash: str, name_to_verify: str = "") -> IntegrationResult:
        """
        Verifica que el hash de cédula corresponde a una persona real.
        name_to_verify: nombre a comparar (opcional, para detección de fraude).
        Solo retorna: válido/inválido — sin datos personales.
        """
        if not self.is_available():
            return self._demo_result({
                "cedula_hash": cedula_hash,
                "valida": True,
                "tipo_documento": "CEDULA",
                "estado_civil": "NO_DISPONIBLE",
                "viva": True,
                "_demo": True,
                "_nota": "Configure DINARDAP_API_KEY y DINARDAP_API_URL para verificación real.",
            })

        try:
            import httpx
            payload = {
                "cedula_hash": cedula_hash,
                "verificar_nombre": bool(name_to_verify),
                "nombre_hash": _sha256(name_to_verify) if name_to_verify else None,
            }
            headers = {
                "X-API-Key": settings.dinardap_api_key,
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient(timeout=8.0) as c:
                r = await c.post(
                    f"{settings.dinardap_api_url}/verificar",
                    json=payload,
                    headers=headers,
                )
                r.raise_for_status()
                data = r.json()
                # Solo extraemos lo necesario — no cachear datos de identidad
                return IntegrationResult(success=True, data={
                    "cedula_hash": cedula_hash,
                    "valida": data.get("cedula_valida", False),
                    "viva": data.get("persona_viva", True),
                    "nombre_coincide": data.get("nombre_coincide", None),
                })
        except Exception as e:
            return self._error_result(str(e))

    async def validate_cedula_format(self, cedula: str) -> bool:
        """
        Validación local del algoritmo de la cédula ecuatoriana (módulo 10).
        No requiere API — es matemática pura.
        """
        if len(cedula) != 10 or not cedula.isdigit():
            return False
        provincia = int(cedula[:2])
        if not (1 <= provincia <= 24):
            return False
        coefficients = [2, 1, 2, 1, 2, 1, 2, 1, 2]
        total = 0
        for i, coef in enumerate(coefficients):
            val = int(cedula[i]) * coef
            if val >= 10:
                val -= 9
            total += val
        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(cedula[9])


def _sha256(value: str) -> str:
    import hashlib
    return hashlib.sha256(value.lower().strip().encode()).hexdigest()


_dinardap = DINARDAPIntegration()
