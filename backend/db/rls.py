"""
Utilidades de aislamiento por sesión + contexto de Row-Level Security.

Las políticas RLS (migración 005_rls.sql) filtran por los GUC
`app.session_hash` y `app.user_id`. `set_rls_context()` fija ese contexto
en la conexión actual para que las políticas se apliquen también a roles
NO superusuario (defensa en profundidad).
"""
import hashlib
import secrets


def make_session_hash(session_id: str) -> str:
    return hashlib.sha256(session_id.encode()).hexdigest()


def new_session_id() -> str:
    return secrets.token_urlsafe(32)


async def set_rls_context(conn, session_hash: str = "", user_id: str = "") -> None:
    """
    Fija el contexto RLS en la conexión asyncpg dada. Llamar al inicio de
    una transacción/petición que toque datos personales. set_config con
    is_local=true → el valor se descarta al terminar la transacción, de
    modo que no se filtra entre peticiones que reusen la conexión del pool.
    """
    await conn.execute(
        "SELECT set_config('app.session_hash', $1, true), "
        "       set_config('app.user_id', $2, true)",
        session_hash or "",
        user_id or "",
    )
