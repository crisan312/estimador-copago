import json
import pathlib
from agents.base_agent import BaseAgent, AgentResult
from config import settings


_DEMO_PATH = pathlib.Path(__file__).parent.parent / "data" / "demo" / "poliza_demo.json"


class PolicyLookup(BaseAgent):
    name = "a3_policy"
    temperature = 0.0
    max_tokens = 1024

    async def run(self, memory) -> AgentResult:
        numero = memory.patient_context.get("numero_poliza", "")

        # Try Notion first if configured
        if settings.notion_enabled and numero:
            result = await self._try_notion(numero, memory)
            if result.success and result.data:
                result.data["fuente"] = "notion"
                return result

        # Fallback to demo JSON
        try:
            demo = json.loads(_DEMO_PATH.read_text(encoding="utf-8"))
            if not numero or numero == demo.get("numero_poliza", ""):
                from agents.base_agent import AgentResult
                return AgentResult(success=True, data={**demo, "fuente": "demo"})
        except Exception:
            pass

        # Last resort: LLM inference from market data
        system = self._load_prompt()
        user = (
            f"Número de póliza ingresado: {numero or 'No proporcionado'}\n"
            f"Contexto del paciente:\n{memory.get_context_summary()}\n"
            "Usa valores de referencia del mercado ecuatoriano."
        )
        result = await self._call(system, user)
        if result.success and result.data:
            result.data["fuente"] = "inferido"
        return result

    async def _try_notion(self, numero: str, memory) -> AgentResult:
        from services.notion_client import fetch_policy
        try:
            policy_data = await fetch_policy(numero)
            if policy_data:
                return AgentResult(success=True, data=policy_data)
        except Exception:
            pass
        return AgentResult(success=False)
