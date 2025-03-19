import pytest

from canaille.backends.memory.backend import MemoryBackend


@pytest.fixture
def memory_backend(configuration):
    configuration["CANAILLE"]["DATABASE"] = "memory"
    backend = MemoryBackend(configuration)
    with backend.session():
        yield backend
