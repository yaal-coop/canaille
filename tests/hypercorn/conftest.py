import pytest


@pytest.fixture
def configuration(configuration):
    configuration["CANAILLE_HYPERCORN"] = {}
    return configuration
