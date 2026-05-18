"""
Capa de acceso a PostgreSQL via asyncpg connection pool.
LOPDP: todas las queries usan parámetros ($1, $2...) para prevenir SQL injection.
"""
import asyncpg
import pathlib
import logging
from config import settings

logger = logging.getLogger("copago.db")
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=settings.db_pool_min,
            max_size=settings.db_pool_max,
            command_timeout=30,
            statement_cache_size=100,
        )
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def _has_executable_sql(sql: str) -> bool:
    """True si el archivo contiene SQL real (no solo comentarios/espacios).
    asyncpg.execute() sobre un string vacío o solo-comentario lanza
    'NoneType has no attribute decode' (EmptyQueryResponse sin command tag)."""
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("--"):
            return True
    return False


async def run_migrations():
    pool = await get_pool()
    migrations_dir = pathlib.Path(__file__).parent / "migrations"
    async with pool.acquire() as conn:
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            sql = sql_file.read_text(encoding="utf-8")
            if not _has_executable_sql(sql):
                logger.info("Skipping empty migration: %s", sql_file.name)
                continue
            logger.info("Running migration: %s", sql_file.name)
            await conn.execute(sql)
    logger.info("All migrations completed")
