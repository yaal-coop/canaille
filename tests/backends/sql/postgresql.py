import pytest

from canaille.app.configuration import settings_factory
from canaille.backends.sql.backend import SQLBackend

try:
    import pytest_postgresql  # noqa: F401

    PYTEST_POSTGRESQL_AVAILABLE = True
except ImportError:
    PYTEST_POSTGRESQL_AVAILABLE = False


@pytest.fixture
def postgresql_configuration(configuration, request):
    """Configure Canaille to use PostgreSQL test database."""
    if not PYTEST_POSTGRESQL_AVAILABLE:
        pytest.skip("pytest-postgresql not available")

    postgresql = request.getfixturevalue("postgresql")
    info = postgresql.info
    uri = f"postgresql://{info.user}@{info.host}:{info.port}/{info.dbname}"

    configuration["CANAILLE"]["DATABASE"] = "sql"
    configuration["CANAILLE_SQL"] = {"DATABASE_URI": uri}
    yield configuration
    del configuration["CANAILLE_SQL"]


@pytest.fixture
def postgresql_backend(postgresql_configuration):
    config_obj = settings_factory(postgresql_configuration)
    config_dict = config_obj.model_dump()
    backend = SQLBackend(config_dict)
    with backend.session():
        yield backend
