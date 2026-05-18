"""
Capa de integraciones externas de CopayAI.

Sistemas conectados:
- SMTP Email        — notificaciones ARCO, recordatorios, alertas DPO
- HL7 FHIR          — interoperabilidad con HIS hospitalarios (futuro)
- IESS Ecuador      — verificación afiliación seguro social (futuro)
- Kushki            — pasarela de cobro de copagos (futuro)
- Aseguradoras API  — consulta de pólizas en tiempo real (futuro)
- DINARDAP          — verificación de identidad ciudadana (futuro)
- Webhook Receiver  — eventos push desde sistemas externos

Cada integración sigue la interfaz BaseIntegration:
  - is_available() → bool
  - health_check() → dict
  - Las clases stub retornan datos demo cuando no está configurada la credencial.
"""
from .base import BaseIntegration, IntegrationResult
from .smtp_email import SmtpEmailIntegration
from .fhir import FHIRIntegration
from .iess import IESSIntegration
from .kushki import KushkiIntegration
from .aseguradoras import AseguradorasIntegration
from .dinardap import DINARDAPIntegration

__all__ = [
    "BaseIntegration", "IntegrationResult",
    "SmtpEmailIntegration", "FHIRIntegration",
    "IESSIntegration", "KushkiIntegration",
    "AseguradorasIntegration", "DINARDAPIntegration",
]
