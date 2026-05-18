"""
Integración IESS Ecuador — Instituto Ecuatoriano de Seguridad Social.

Permite verificar si el paciente tiene cobertura IESS activa y cruzar datos
con el seguro privado para evitar doble cobro (coordinación de beneficios).

API oficial: https://servicios.iess.gob.ec (requiere convenio institucional)
Sandbox: IESS no tiene sandbox público — usamos stub con datos demo.

Casos de uso:
- Verificar afiliación activa por cédula
- Obtener tipo de afiliación (dependiente, voluntario, campesino)
- Consultar si tiene cobertura para la especialidad solicitada
- Coordinación de beneficios: IESS cubre X%, privado cubre el diferencial

Sin IESS_API_KEY configurado: retorna datos demo.
"""
import logging
from config import settings
from .base import BaseIntegration, IntegrationResult

logger = logging.getLogger("copago.integrations.iess")


class IESSIntegration(BaseIntegration):
    name = "iess"

    def is_available(self) -> bool:
        return bool(settings.iess_api_key and settings.iess_api_url)

    async def verify_affiliation(self, cedula_hash: str) -> IntegrationResult:
        """
        Verifica si el ciudadano está afiliado al IESS.
        Recibe SHA-256(cédula) — LOPDP: nunca enviamos cédulas en claro.
        """
        if not self.is_available():
            return self._demo_result({
                "afiliado": True,
                "tipo_afiliacion": "DEPENDIENTE",
                "estado": "ACTIVO",
                "especialidades_cubiertas": ["Medicina General", "Medicina Interna", "Pediatría"],
                "requiere_referencia_iess": True,
                "cedula_hash": cedula_hash,
                "_demo": True,
                "_nota": "Configure IESS_API_KEY e IESS_API_URL para consultas reales.",
            })

        try:
            import httpx
            headers = {
                "X-API-Key": settings.iess_api_key,
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient(timeout=8.0) as c:
                r = await c.post(
                    f"{settings.iess_api_url}/afiliacion/verificar",
                    json={"cedula_hash": cedula_hash},
                    headers=headers,
                )
                r.raise_for_status()
                return IntegrationResult(success=True, data=r.json())
        except Exception as e:
            return self._error_result(str(e))

    async def get_coverage_for_specialty(self, cedula_hash: str, specialty: str) -> IntegrationResult:
        """
        Consulta si el IESS cubre la especialidad para este afiliado.
        Importante para coordinación de beneficios con el seguro privado.
        """
        if not self.is_available():
            specialty_covered = specialty.lower() in [
                "medicina general", "medicina interna", "pediatría",
                "ginecología", "cardiología", "emergencia",
            ]
            return self._demo_result({
                "especialidad": specialty,
                "cubierta_iess": specialty_covered,
                "porcentaje_cobertura_iess": 80 if specialty_covered else 0,
                "copago_iess_usd": 1.50 if specialty_covered else 0,
                "requiere_referencia": True,
                "tiempo_espera_promedio_dias": 15,
                "_demo": True,
            })

        try:
            import httpx
            async with httpx.AsyncClient(timeout=8.0) as c:
                r = await c.get(
                    f"{settings.iess_api_url}/cobertura",
                    params={"cedula_hash": cedula_hash, "especialidad": specialty},
                    headers={"X-API-Key": settings.iess_api_key},
                )
                r.raise_for_status()
                return IntegrationResult(success=True, data=r.json())
        except Exception as e:
            return self._error_result(str(e))

    async def coordinate_benefits(
        self, cedula_hash: str, specialty: str, costo_consulta: float, copago_privado: float
    ) -> IntegrationResult:
        """
        Calcula el copago real cuando el paciente tiene IESS + seguro privado.
        El seguro privado cubre el diferencial que IESS no cubre.
        """
        iess_cov = await self.get_coverage_for_specialty(cedula_hash, specialty)
        if not iess_cov.success:
            return iess_cov

        porcentaje_iess = iess_cov.data.get("porcentaje_cobertura_iess", 0) / 100
        costo_iess = costo_consulta * porcentaje_iess
        diferencial = costo_consulta - costo_iess
        copago_final = min(copago_privado, diferencial * 0.2)  # Seguro privado cubre 80% del diferencial

        return IntegrationResult(success=True, data={
            "costo_total_usd": costo_consulta,
            "cubierto_iess_usd": round(costo_iess, 2),
            "diferencial_usd": round(diferencial, 2),
            "copago_final_usd": round(copago_final, 2),
            "ahorro_vs_solo_privado_usd": round(copago_privado - copago_final, 2),
            "_demo": iess_cov.demo_mode,
        })


_iess = IESSIntegration()
