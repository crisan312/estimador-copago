import json
from agents.base_agent import BaseAgent, AgentResult
from config import settings


class CopayCalculator(BaseAgent):
    name = "a4_copay"
    temperature = 0.0
    max_tokens = 1024

    async def run(self, memory) -> AgentResult:
        poliza = memory.patient_context.get("poliza", {})
        a2 = memory.patient_context.get("a2_result", {})
        system = self._load_prompt()
        user = (
            f"Especialidad: {memory.patient_context.get('especialidad', 'Medicina General')}\n"
            f"Tipo de consulta: {a2.get('tipo_consulta', 'CONSULTA_EXTERNA')}\n"
            f"Datos de la póliza:\n{json.dumps(poliza, ensure_ascii=False, indent=2)}\n"
            f"Contexto:\n{memory.get_context_summary()}"
        )
        result = await self._call(system, user)
        if result.success and result.data:
            confianza = result.data.get("confianza", 0.8)
            if confianza < settings.validation_confidence_threshold:
                advertencias = result.data.setdefault("advertencias", [])
                advertencias.append(
                    f"Confianza del cálculo: {int(confianza*100)}% — "
                    "Este es un estimado. Te recomendamos confirmar el monto con tu aseguradora antes de la consulta."
                )
        return result
