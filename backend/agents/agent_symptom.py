from agents.base_agent import BaseAgent, AgentResult
from config import settings


class SymptomInterpreter(BaseAgent):
    name = "a1_symptom"
    temperature = settings.claude_temperature_conversation
    max_tokens = 512

    async def run(self, user_message: str, memory) -> AgentResult:
        system = self._load_prompt()
        user = f"El paciente dice: \"{user_message}\"\n\nContexto previo:\n{memory.get_context_summary()}"
        return await self._call(system, user)
