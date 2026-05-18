import json
import pathlib
from agents.base_agent import BaseAgent, AgentResult

_HOSPITALS_PATH = pathlib.Path(__file__).parent.parent / "data" / "hospitales_red.json"


class HospitalRanker(BaseAgent):
    name = "a5_hospital"
    temperature = 0.1
    max_tokens = 1024

    async def run(self, memory) -> AgentResult:
        try:
            hospitals_data = json.loads(_HOSPITALS_PATH.read_text(encoding="utf-8"))
        except Exception:
            hospitals_data = []

        poliza = memory.patient_context.get("poliza", {})
        copago_data = memory.patient_context.get("copago", {})
        especialidad = memory.patient_context.get("especialidad", "Medicina General")

        system = self._load_prompt()
        user = (
            f"Especialidad requerida: {especialidad}\n"
            f"Ciudad del paciente: {memory.patient_context.get('ciudad', 'Guayaquil')}\n"
            f"Datos de póliza:\n{json.dumps(poliza, ensure_ascii=False)}\n"
            f"Copago calculado: {copago_data.get('copago_estimado_usd', 'No calculado')} USD\n"
            f"Red de hospitales disponible:\n{json.dumps(hospitals_data[:30], ensure_ascii=False)}\n"
            "Selecciona los 5 más relevantes, ordena por copago_estimado_usd ASC."
        )
        return await self._call(system, user)
