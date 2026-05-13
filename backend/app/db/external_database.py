import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

_engine: Engine | None = None


def get_external_engine() -> Engine:
    """
    Retorna (singleton) o engine SQLAlchemy do banco externo `meli`.
    A conexão deve ser feita com um role Postgres com GRANT SELECT
    apenas (read-only) no schema `meli`.
    """
    global _engine
    if _engine is None:
        url = os.getenv("EXTERNAL_DB_URL")
        if not url:
            raise RuntimeError(
                "EXTERNAL_DB_URL não configurada. "
                "Defina no .env (ex.: postgresql://meli_readonly:senha@host:5432/meli)."
            )
        _engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=2,
            future=True,
        )
        logger.info("External engine (meli) inicializado.")
    return _engine


def test_external_connection() -> bool:
    """Executa SELECT 1 no banco externo. Lança exceção em caso de falha."""
    with get_external_engine().connect() as conn:
        conn.execute(text("SELECT 1"))
    return True