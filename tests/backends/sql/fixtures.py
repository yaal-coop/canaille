import pytest

from canaille.app.configuration import settings_factory
from canaille.backends.sql.backend import SQLBackend


@pytest.fixture
def sqlalchemy_configuration(configuration):
    configuration["CANAILLE"]["DATABASE"] = "sql"
    configuration["CANAILLE_SQL"] = {
        "DATABASE_URI": "sqlite:///:memory:",
        "PASSWORD_HASH_PARAMS": {"pbkdf2_sha512__rounds": 1},
    }
    yield configuration
    del configuration["CANAILLE_SQL"]


@pytest.fixture
def sql_backend(sqlalchemy_configuration):
    config_obj = settings_factory(sqlalchemy_configuration)
    config_dict = config_obj.model_dump()
    backend = SQLBackend(config_dict)
    with backend.session():
        yield backend
