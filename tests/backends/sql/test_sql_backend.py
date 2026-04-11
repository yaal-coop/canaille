from canaille.app.configuration import settings_factory
from canaille.backends.sql.backend import SQLBackend


def test_in_memory_sqlite_pool():
    """SQLBackend should handle in-memory SQLite which does not support pool_size/max_overflow."""
    config = settings_factory(
        {
            "SECRET_KEY": "test",
            "CANAILLE": {"DATABASE": "sql"},
            "CANAILLE_SQL": {
                "DATABASE_URI": "sqlite://",
                "PASSWORD_SCHEMES": "plaintext",
            },
        }
    )
    backend = SQLBackend(config.model_dump())
    try:
        assert backend.engine is not None
    finally:
        SQLBackend.engine.dispose()
