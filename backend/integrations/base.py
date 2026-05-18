"""
Contrato base para todas las integraciones externas de CopayAI.
"""
import logging
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IntegrationResult:
    success: bool
    data: dict = field(default_factory=dict)
    error: str = ""
    demo_mode: bool = False


class BaseIntegration:
    """Clase base para integraciones externas."""
    name: str = "base"
    _logger: logging.Logger

    def __init__(self):
        self._logger = logging.getLogger(f"copago.integrations.{self.name}")

    def is_available(self) -> bool:
        """Retorna True si las credenciales están configuradas."""
        raise NotImplementedError

    async def health_check(self) -> dict:
        """Verifica conectividad con el sistema externo."""
        return {
            "integration": self.name,
            "available": self.is_available(),
            "mode": "live" if self.is_available() else "demo",
        }

    def _demo_result(self, data: dict) -> IntegrationResult:
        self._logger.info("[DEMO] %s — credenciales no configuradas, retornando datos demo", self.name)
        return IntegrationResult(success=True, data=data, demo_mode=True)

    def _error_result(self, error: str) -> IntegrationResult:
        self._logger.error("[ERROR] %s: %s", self.name, error)
        return IntegrationResult(success=False, error=error)
