import json
from agents.base_agent import BaseAgent, AgentResult
from config import settings


class SpecialtySuggester(BaseAgent):
    name = "a2_specialty"
    temperature = settings.claude_temperature_extraction
    max_tokens = 512

    async def run(self, a1_data: dict, memory) -> AgentResult:
        system = self._load_prompt()
        user = f"Síntomas interpretados:\n{json.dumps(a1_data, ensure_ascii=False, indent=2)}"
        return await self._call(system, user)
