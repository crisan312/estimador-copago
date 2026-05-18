"""
A7-InsightAnalyst: genera recomendaciones IA sobre datos agregados del sistema.
Trabaja SOLO con datos anónimos — sin PII.
"""
import json
from agents.base_agent import BaseAgent, AgentResult


class InsightAnalyst(BaseAgent):
    name = "a7_insight"
    temperature = 0.2
    max_tokens = 2000

    async def run(
        self,
        analysis_type: str,
        data: dict,
        system_context: str = "",
    ) -> AgentResult:
        system = self._load_prompt().format(
            analysis_type=analysis_type,
            data=json.dumps(data, ensure_ascii=False, indent=2),
            system_context=system_context or "Sistema CopayAI — Ecuador",
        )
        user = f"Analiza los datos de tipo '{analysis_type}' y genera los insights en JSON."
        return await self._call(system, user)
