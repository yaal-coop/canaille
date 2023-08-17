import pytest
from canaille.backends.memory.backend import Backend


@pytest.fixture
def memory_backend(configuration):
    backend = Backend(configuration)
    with backend.session():
        yield backend
