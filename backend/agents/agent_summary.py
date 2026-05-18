import json
from agents.base_agent import BaseAgent, AgentResult
from config import settings


class SummaryWriter(BaseAgent):
    name = "a6_summary"
    temperature = settings.claude_temperature_synthesis
    max_tokens = 1024

    async def run(self, memory) -> AgentResult:
        copago = memory.patient_context.get("copago", {})
        hospitales = memory.patient_context.get("hospitales", [])
        mejor = hospitales[0] if hospitales else {}

        system = self._load_prompt()
        user = (
            f"Síntoma del paciente: {memory.patient_context.get('sintoma_principal', '')}\n"
            f"Especialidad recomendada: {memory.patient_context.get('especialidad', '')}\n"
            f"Copago estimado: ${copago.get('copago_estimado_usd', 0):.2f} USD\n"
            f"Cobertura del seguro: {copago.get('cobertura_pct', 0)}%\n"
            f"Confianza del cálculo: {copago.get('confianza', 0.8):.0%}\n"
            f"Mejor hospital: {mejor.get('nombre', 'No disponible')} — "
            f"${mejor.get('copago_estimado_usd', 0):.2f} copago\n"
            f"Teléfono: {mejor.get('telefono', 'N/D')}\n"
            f"Advertencias: {json.dumps(copago.get('advertencias', []), ensure_ascii=False)}\n"
            f"Contexto completo:\n{memory.get_context_summary()}"
        )
        return await self._call(system, user)
