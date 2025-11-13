import pytest

from canaille.app.configuration import settings_factory
from canaille.backends.sql.backend import SQLBackend


@pytest.fixture
def postgresql_configuration(configuration, request):
    """Configure Canaille to use PostgreSQL test database."""
    pytest.importorskip("pytest_postgresql")

    postgresql = request.getfixturevalue("postgresql")
    info = postgresql.info
    uri = f"postgresql://{info.user}@{info.host}:{info.port}/{info.dbname}"

    configuration["CANAILLE"]["DATABASE"] = "sql"
    configuration["CANAILLE_SQL"] = {
        "DATABASE_URI": uri,
        "PASSWORD_SCHEMES": "plaintext",
    }
    yield configuration
    del configuration["CANAILLE_SQL"]


@pytest.fixture
def postgresql_backend(postgresql_configuration):
    config_obj = settings_factory(postgresql_configuration)
    config_dict = config_obj.model_dump()
    backend = SQLBackend(config_dict)
    with backend.session():
        yield backend
