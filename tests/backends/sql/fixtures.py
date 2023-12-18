import pytest

from canaille.backends.sql.backend import Backend


@pytest.fixture
def sqlalchemy_configuration(configuration):
    configuration["CANAILLE_SQL"] = {"DATABASE_URI": "sqlite:///:memory:"}
    yield configuration
    del configuration["CANAILLE_SQL"]


@pytest.fixture
def sql_backend(sqlalchemy_configuration):
    backend = Backend(sqlalchemy_configuration)
    with backend.session(init=True):
        yield backend
