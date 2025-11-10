import pytest

from canaille.app.configuration import settings_factory
from canaille.backends.sql.backend import SQLBackend


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
def sqlite_backend(sqlite_configuration):
    config_obj = settings_factory(sqlite_configuration)
    config_dict = config_obj.model_dump()
    backend = SQLBackend(config_dict)
    with backend.session():
        yield backend
