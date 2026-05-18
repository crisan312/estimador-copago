"""
Router SSE de chat — requiere consentimiento previo (ConsentMiddleware).
"""
import uuid
from typing import Annotated
from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from db.rls import make_session_hash, new_session_id
from orchestrator import pipeline
from services import audit_service

router = APIRouter(prefix="/api/v1", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


@router.post("/chat")
async def chat(
    req: ChatRequest,
    x_session_id: Annotated[str | None, Header()] = None,
):
    session_id = x_session_id or new_session_id()
    session_hash = make_session_hash(session_id)

    await audit_service.log_event(
        session_hash=session_hash,
        event_type=audit_service.AuditEvent.DATA_MODIFIED,
        resource="conversations",
        resource_id=req.conversation_id,
        details={"action": "chat_message", "has_content": bool(req.message)},
    )

    async def event_generator():
        async for event in pipeline.process_message(session_hash, req.conversation_id, req.message):
            yield event
        yield 'data: {"type": "done"}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",
            "X-Session-Id": session_id,
        },
    )


@router.get("/demo")
async def start_demo():
    session_id = new_session_id()
    session_hash = make_session_hash(session_id)
    demo_id = str(uuid.uuid4())

    async def demo_stream():
        for msg in [
            "me duele el pecho cuando subo escaleras, ya me ha pasado tres veces esta semana",
            "12345-EC",
        ]:
            async for event in pipeline.process_message(session_hash, demo_id, msg):
                yield event
        yield 'data: {"type": "done"}\n\n'

    return StreamingResponse(
        demo_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",
            "X-Session-Id": session_id,
        },
    )
