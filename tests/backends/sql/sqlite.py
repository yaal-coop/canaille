import shutil
import tempfile
from pathlib import Path

import pytest

from canaille.app.configuration import settings_factory
from canaille.backends.sql.backend import SQLBackend


@pytest.fixture(scope="session")
def sqlite_template_db(tmp_path_factory):
    """Create a pre-migrated SQLite database template once per test session.

    This template is created with all Alembic migrations applied, and will be
    copied for each test that needs a SQLite backend, avoiding the overhead of
    running migrations repeatedly.
    """
    template_dir = tmp_path_factory.mktemp("sqlite_templates")
    template_path = template_dir / "template.db"

    template_config = {
        "SECRET_KEY": "template-secret-key",
        "CANAILLE": {
            "DATABASE": "sql",
        },
        "CANAILLE_SQL": {
            "DATABASE_URI": f"sqlite:///{template_path}",
            "PASSWORD_SCHEMES": "plaintext",
            "AUTO_MIGRATE": True,
        },
    }

    config_obj = settings_factory(template_config)
    config_dict = config_obj.model_dump()
    backend = SQLBackend(config_dict)

    from canaille import create_app

    app = create_app(config_dict)
    with app.app_context():
        backend.alembic.upgrade()

    yield template_path

    SQLBackend.engine.dispose()


@pytest.fixture
def sqlite_configuration(configuration):
    configuration["CANAILLE"]["DATABASE"] = "sql"
    configuration["CANAILLE_SQL"] = {
        "DATABASE_URI": "sqlite:///:memory:",
        "PASSWORD_SCHEMES": "plaintext",
    }
    yield configuration
    del configuration["CANAILLE_SQL"]


@pytest.fixture
def sqlite_backend(sqlite_configuration, sqlite_template_db):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        test_db_path = f.name

    shutil.copy2(sqlite_template_db, test_db_path)

    sqlite_configuration["CANAILLE_SQL"]["DATABASE_URI"] = f"sqlite:///{test_db_path}"
    sqlite_configuration["CANAILLE_SQL"]["AUTO_MIGRATE"] = False

    config_obj = settings_factory(sqlite_configuration)
    config_dict = config_obj.model_dump()
    backend = SQLBackend(config_dict)

    try:
        with backend.session():
            yield backend
    finally:
        SQLBackend.engine.dispose()
        Path(test_db_path).unlink(missing_ok=True)
