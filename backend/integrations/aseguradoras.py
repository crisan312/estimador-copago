"""
Integración con APIs de aseguradoras ecuatorianas.

Aseguradoras objetivo:
- BMI Ecuador (Seguros Médicos) — https://www.bmigrupo.com/ec/
- Ecuasanitas — https://www.ecuasanitas.com/
- MAPFRE Ecuador — https://www.mapfre.com.ec/
- Seguros Sucre — https://www.segurossucre.fin.ec/
- AXA Colpatria Ecuador

Sin API configurada: retorna datos del JSON demo (poliza_demo.json).
Cada aseguradora requiere convenio de interoperabilidad y certificado SSL mutuo.

Patrón: adapter por aseguradora → interfaz unificada de CopayAI.
"""
import json
import logging
import pathlib
from typing import Optional
from config import settings
from .base import BaseIntegration, IntegrationResult

logger = logging.getLogger("copago.integrations.aseguradoras")

_DEMO_POLIZA = pathlib.Path(__file__).parent.parent / "data" / "demo" / "poliza_demo.json"


class AseguradorasIntegration(BaseIntegration):
    """
    Adapter unificado para múltiples aseguradoras.
    Detecta la aseguradora por prefijo del número de póliza y usa el adapter correcto.
    """
    name = "aseguradoras"

    # Mapeo prefijo de póliza → aseguradora
    POLICY_PREFIXES = {
        "BMI": "bmi",
        "ECU": "ecuasanitas",
        "MAP": "mapfre",
        "SUC": "sucre",
        "AXA": "axa",
    }

    def is_available(self) -> bool:
        return any([
            settings.aseg_bmi_api_key,
            settings.aseg_ecuasanitas_api_key,
            settings.aseg_mapfre_api_key,
        ])

    def _detect_insurer(self, policy_number: str) -> Optional[str]:
        upper = policy_number.upper()
        for prefix, insurer in self.POLICY_PREFIXES.items():
            if upper.startswith(prefix):
                return insurer
        return None

    async def fetch_policy(self, policy_number: str) -> IntegrationResult:
        """
        Consulta póliza en tiempo real desde la aseguradora correspondiente.
        Fallback a demo JSON si no hay API configurada.
        """
        insurer = self._detect_insurer(policy_number)

        if insurer == "bmi" and settings.aseg_bmi_api_key:
            return await self._fetch_bmi(policy_number)
        elif insurer == "ecuasanitas" and settings.aseg_ecuasanitas_api_key:
            return await self._fetch_ecuasanitas(policy_number)
        elif insurer == "mapfre" and settings.aseg_mapfre_api_key:
            return await self._fetch_mapfre(policy_number)

        # Demo fallback
        try:
            demo = json.loads(_DEMO_POLIZA.read_text(encoding="utf-8"))
            demo["fuente"] = "demo"
            demo["numero_poliza"] = policy_number or demo["numero_poliza"]
            return self._demo_result(demo)
        except Exception as e:
            return self._error_result(f"Demo fallback error: {e}")

    async def _fetch_bmi(self, policy_number: str) -> IntegrationResult:
        """Adapter BMI Ecuador."""
        try:
            import httpx
            headers = {
                "X-Api-Key": settings.aseg_bmi_api_key,
                "Accept": "application/json",
            }
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(
                    f"{settings.aseg_bmi_api_url}/polizas/{policy_number}",
                    headers=headers,
                )
                r.raise_for_status()
                raw = r.json()
                # Normalize BMI response → CopayAI schema
                return IntegrationResult(success=True, data={
                    "numero_poliza": policy_number,
                    "plan_nombre": raw.get("planNombre", ""),
                    "aseguradora": "BMI Ecuador",
                    "copago_pct": raw.get("porcentajeCopago", 20),
                    "deducible_anual": raw.get("deducibleAnual", 500),
                    "deducible_consumido": raw.get("deducibleConsumido", 0),
                    "cobertura_consulta_externa": raw.get("coberturaConsulta", True),
                    "cobertura_especialistas": raw.get("coberturaEspecialistas", True),
                    "cobertura_emergencias": raw.get("coberturaEmergencias", True),
                    "coaseguro_pct": raw.get("coaseguro", 0),
                    "tope_anual_usd": raw.get("topeAnual", 50000),
                    "tope_consumido_usd": raw.get("topeConsumido", 0),
                    "red_hospitales_autorizados": raw.get("redHospitales", []),
                    "fuente": "bmi_api",
                })
        except Exception as e:
            logger.warning("BMI API error para %s: %s — usando demo", policy_number, e)
            return await self.fetch_policy("")  # recurse to demo

    async def _fetch_ecuasanitas(self, policy_number: str) -> IntegrationResult:
        """Adapter Ecuasanitas."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(
                    f"{settings.aseg_ecuasanitas_api_url}/afiliados/poliza/{policy_number}",
                    headers={"Authorization": f"Bearer {settings.aseg_ecuasanitas_api_key}"},
                )
                r.raise_for_status()
                raw = r.json()
                return IntegrationResult(success=True, data={
                    "numero_poliza": policy_number,
                    "plan_nombre": raw.get("plan", ""),
                    "aseguradora": "Ecuasanitas",
                    "copago_pct": raw.get("copago", 20),
                    "deducible_anual": raw.get("deducible", 300),
                    "deducible_consumido": raw.get("deducibleUsado", 0),
                    "cobertura_consulta_externa": True,
                    "cobertura_especialistas": True,
                    "cobertura_emergencias": True,
                    "coaseguro_pct": 0,
                    "tope_anual_usd": raw.get("tope", 40000),
                    "tope_consumido_usd": raw.get("topeUsado", 0),
                    "red_hospitales_autorizados": raw.get("hospitalesRed", []),
                    "fuente": "ecuasanitas_api",
                })
        except Exception as e:
            logger.warning("Ecuasanitas API error: %s — usando demo", e)
            return await self.fetch_policy("")

    async def _fetch_mapfre(self, policy_number: str) -> IntegrationResult:
        """Adapter MAPFRE Ecuador."""
        # MAPFRE usa SOAP — wrapper HTTP simplificado
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.post(
                    f"{settings.aseg_mapfre_api_url}/ws/poliza",
                    json={"numeroPoliza": policy_number, "apiKey": settings.aseg_mapfre_api_key},
                )
                r.raise_for_status()
                raw = r.json()
                return IntegrationResult(success=True, data={
                    "numero_poliza": policy_number,
                    "plan_nombre": raw.get("descripcion", ""),
                    "aseguradora": "MAPFRE Ecuador",
                    "copago_pct": raw.get("porcentajeCopago", 20),
                    "deducible_anual": raw.get("deducible", 400),
                    "deducible_consumido": raw.get("consumoDeducible", 0),
                    "cobertura_consulta_externa": raw.get("ambuConsulta", True),
                    "cobertura_especialistas": raw.get("ambuEspecialista", True),
                    "cobertura_emergencias": raw.get("emergencia", True),
                    "coaseguro_pct": raw.get("coaseguro", 0),
                    "tope_anual_usd": raw.get("limiteAnual", 60000),
                    "tope_consumido_usd": raw.get("consumoAnual", 0),
                    "red_hospitales_autorizados": raw.get("red", []),
                    "fuente": "mapfre_api",
                })
        except Exception as e:
            logger.warning("MAPFRE API error: %s — usando demo", e)
            return await self.fetch_policy("")


_aseg = AseguradorasIntegration()


async def fetch_policy(policy_number: str) -> IntegrationResult:
    return await _aseg.fetch_policy(policy_number)
