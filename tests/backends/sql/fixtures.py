import pytest
from canaille.backends.sql.backend import Backend


@pytest.fixture
def sqlalchemy_configuration(configuration):
    configuration["BACKENDS"] = {
        "SQL": {"SQL_DATABASE_URI": "sqlite:///:memory:"},
    }
    yield configuration
    del configuration["BACKENDS"]


@pytest.fixture
def sql_backend(sqlalchemy_configuration):
    backend = Backend(sqlalchemy_configuration)
    with backend.session(init=True):
        yield backend
