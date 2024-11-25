import pytest


@pytest.fixture
def configuration(configuration):
    configuration["CANAILLE_SCIM"] = {
        "ENABLE_SERVER": True,
    }
    configuration["CANAILLE"]["LOGGING"]["loggers"]["httpx"] = {
        "level": "INFO",
    }
    configuration["CANAILLE"]["LOGGING"]["loggers"]["httpcore"] = {
        "level": "INFO",
    }
    return configuration
