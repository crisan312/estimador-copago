import time
import uuid
from dataclasses import dataclass, field
from config import settings


@dataclass
class ConversationMemory:
    session_id: str
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: str = "GREETING"
    turns: list[dict] = field(default_factory=list)
    patient_context: dict = field(default_factory=dict)
    total_tokens: int = 0
    created_at: float = field(default_factory=time.time)

    def add_turn(self, role: str, content: str):
        self.turns.append({"role": role, "content": content})

    def get_context_summary(self) -> str:
        ctx = self.patient_context
        return (
            f"Síntoma principal: {ctx.get('sintoma_principal', 'No indicado')}\n"
            f"Especialidad sugerida: {ctx.get('especialidad', 'Pendiente')}\n"
            f"Póliza cargada: {'Sí' if 'poliza' in ctx else 'No'}\n"
            f"Turno actual: {len(self.turns)}\n"
            f"Estado: {self.state}"
        )

    async def persist(self):
        from services.redis_store import save_conversation
        await save_conversation(
            self.conversation_id,
            self.state,
            self.patient_context,
            self.turns,
            self.total_tokens,
        )


async def get_or_create(session_id: str, conversation_id: str | None = None) -> ConversationMemory:
    """Load from Redis or create a fresh ConversationMemory."""
    from services.redis_store import load_conversation
    if conversation_id:
        data = await load_conversation(conversation_id)
        if data:
            mem = ConversationMemory(
                session_id=session_id,
                conversation_id=conversation_id,
            )
            mem.state = data["state"]
            mem.patient_context = data["patient_context"]
            mem.turns = data["turns"]
            mem.total_tokens = data["total_tokens"]
            return mem
    mem = ConversationMemory(session_id=session_id)
    if conversation_id:
        mem.conversation_id = conversation_id
    return mem


async def get_conversation_meta(conversation_id: str) -> dict | None:
    """Return lightweight metadata for the /conversation/{id} endpoint."""
    from services.redis_store import load_conversation
    return await load_conversation(conversation_id)
