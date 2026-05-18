"""
ConversationMemory respaldada en Redis.
- TTL automático = SESSION_TTL_SECONDS
- Datos cifrados antes de persistir (LOPDP)
- No PII en claves Redis (solo session_hash)
"""
import json
import redis.asyncio as aioredis
from config import settings
from services.encryption import encrypt, decrypt

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=False,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
    return _redis


async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


def _conv_key(conversation_id: str) -> str:
    return f"conv:{conversation_id}"


def _consent_key(session_hash: str) -> str:
    return f"consent:{session_hash}"


async def save_conversation(conv_id: str, state: str, patient_context: dict, turns: list, total_tokens: int):
    r = await get_redis()
    payload = {
        "state": state,
        "patient_context_enc": encrypt(patient_context).decode("latin-1"),
        "turns_enc": encrypt(turns).decode("latin-1"),
        "total_tokens": total_tokens,
    }
    await r.setex(
        _conv_key(conv_id),
        settings.session_ttl_seconds,
        json.dumps(payload),
    )


async def load_conversation(conv_id: str) -> dict | None:
    r = await get_redis()
    raw = await r.get(_conv_key(conv_id))
    if not raw:
        return None
    payload = json.loads(raw)
    return {
        "state": payload["state"],
        "patient_context": decrypt(payload["patient_context_enc"].encode("latin-1")),
        "turns": decrypt(payload["turns_enc"].encode("latin-1")),
        "total_tokens": payload["total_tokens"],
    }


async def delete_conversation(conv_id: str):
    r = await get_redis()
    await r.delete(_conv_key(conv_id))


async def set_consent(session_hash: str, version: str):
    r = await get_redis()
    ttl = settings.consent_ttl_days * 86400
    await r.setex(_consent_key(session_hash), ttl, version)


async def has_consent(session_hash: str) -> bool:
    r = await get_redis()
    val = await r.get(_consent_key(session_hash))
    if not val:
        return False
    version = val.decode() if isinstance(val, bytes) else val
    return version == settings.consent_version


async def revoke_consent(session_hash: str):
    r = await get_redis()
    await r.delete(_consent_key(session_hash))
