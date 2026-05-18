import hashlib
import secrets


def make_session_hash(session_id: str) -> str:
    return hashlib.sha256(session_id.encode()).hexdigest()


def new_session_id() -> str:
    return secrets.token_urlsafe(32)
