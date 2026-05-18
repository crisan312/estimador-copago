"""
Integración HL7 FHIR R4 — interoperabilidad con Sistemas de Información Hospitalaria (HIS/HIS-EC).

Estándar internacional para intercambio de datos clínicos.
Ecuador: en proceso de adopción (MSP Resolución 00003858-2020).

Casos de uso:
- Obtener historial clínico del paciente desde el HIS del hospital
- Enviar resultados del estimado de copago al HIS
- Consultar disponibilidad de especialistas (Slot FHIR)
- Crear cita (Appointment FHIR)

Sin FHIR_BASE_URL configurado: retorna datos demo en formato FHIR.
"""
import logging
from typing import Optional

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

from config import settings
from .base import BaseIntegration, IntegrationResult

logger = logging.getLogger("copago.integrations.fhir")


class FHIRIntegration(BaseIntegration):
    name = "fhir"

    def is_available(self) -> bool:
        return bool(settings.fhir_base_url)

    async def health_check(self) -> dict:
        base = await super().health_check()
        if self.is_available() and _HAS_HTTPX:
            try:
                async with httpx.AsyncClient(timeout=5.0) as c:
                    r = await c.get(f"{settings.fhir_base_url}/metadata")
                    base["status"] = "connected" if r.status_code == 200 else "error"
                    base["fhir_version"] = r.json().get("fhirVersion", "unknown") if r.status_code == 200 else "N/A"
            except Exception as e:
                base["status"] = "error"
                base["error"] = str(e)
        return base

    async def get_patient(self, cedula: str) -> IntegrationResult:
        """Busca paciente por cédula ecuatoriana (identifier FHIR)."""
        if not self.is_available():
            return self._demo_result({
                "resourceType": "Patient",
                "id": "demo-patient-001",
                "identifier": [{"system": "urn:oid:2.16.840.1.113883.2.16.1.3.2", "value": cedula}],
                "name": [{"use": "official", "family": "Demo", "given": ["Paciente"]}],
                "gender": "unknown",
                "birthDate": "1990-01-01",
                "_demo": True,
            })
        return await self._fhir_get(f"Patient?identifier={cedula}")

    async def get_available_slots(self, specialty_code: str, hospital_id: str, date: str) -> IntegrationResult:
        """Consulta slots de cita disponibles (Slot FHIR)."""
        if not self.is_available():
            return self._demo_result({
                "resourceType": "Bundle",
                "type": "searchset",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Slot",
                            "id": f"slot-demo-{i}",
                            "status": "free",
                            "start": f"{date}T{9+i}:00:00-05:00",
                            "end": f"{date}T{9+i}:30:00-05:00",
                            "specialty": [{"coding": [{"code": specialty_code}]}],
                        }
                    }
                    for i in range(4)
                ],
                "_demo": True,
            })
        return await self._fhir_get(f"Slot?schedule.actor={hospital_id}&specialty={specialty_code}&start={date}")

    async def create_appointment(self, patient_id: str, slot_id: str, specialty: str) -> IntegrationResult:
        """Crea cita en el HIS (Appointment FHIR)."""
        if not self.is_available():
            return self._demo_result({
                "resourceType": "Appointment",
                "id": "demo-appointment-001",
                "status": "booked",
                "specialty": [{"text": specialty}],
                "participant": [{"actor": {"reference": f"Patient/{patient_id}"}, "status": "accepted"}],
                "_demo": True,
            })
        payload = {
            "resourceType": "Appointment",
            "status": "booked",
            "specialty": [{"text": specialty}],
            "participant": [
                {"actor": {"reference": f"Patient/{patient_id}"}, "required": "required", "status": "accepted"},
                {"actor": {"reference": f"Slot/{slot_id}"}, "required": "required", "status": "accepted"},
            ],
        }
        return await self._fhir_post("Appointment", payload)

    async def _fhir_get(self, path: str) -> IntegrationResult:
        if not _HAS_HTTPX:
            return self._error_result("httpx no instalado — pip install httpx")
        try:
            headers = {"Accept": "application/fhir+json"}
            if settings.fhir_token:
                headers["Authorization"] = f"Bearer {settings.fhir_token}"
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(f"{settings.fhir_base_url}/{path}", headers=headers)
                r.raise_for_status()
                return IntegrationResult(success=True, data=r.json())
        except Exception as e:
            return self._error_result(str(e))

    async def _fhir_post(self, resource: str, payload: dict) -> IntegrationResult:
        if not _HAS_HTTPX:
            return self._error_result("httpx no instalado")
        try:
            headers = {"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"}
            if settings.fhir_token:
                headers["Authorization"] = f"Bearer {settings.fhir_token}"
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.post(f"{settings.fhir_base_url}/{resource}", json=payload, headers=headers)
                r.raise_for_status()
                return IntegrationResult(success=True, data=r.json())
        except Exception as e:
            return self._error_result(str(e))


_fhir = FHIRIntegration()
