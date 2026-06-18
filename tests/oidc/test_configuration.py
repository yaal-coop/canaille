import warnings

import pytest
from pydantic import ValidationError

from canaille.oidc.configuration import OIDCSettings
from canaille.oidc.provider import get_issuer


def test_issuer(testclient):
    """Test that the issuer URL is correctly determined from the configuration."""
    with warnings.catch_warnings(record=True):
        with testclient.app.test_request_context("/"):
            assert get_issuer() == "http://canaille.test"

        testclient.app.config["SERVER_NAME"] = None
        with testclient.app.test_request_context("/"):
            assert get_issuer() == "http://localhost/"


def test_device_code_polling_interval_too_short():
    """The device code polling interval must last at least one second."""
    with pytest.raises(ValidationError, match="DEVICE_CODE_POLLING_INTERVAL"):
        OIDCSettings(DEVICE_CODE_POLLING_INTERVAL="PT0.5S")


def test_device_code_lifetime_too_short():
    """The device code lifetime must be longer than the polling interval."""
    with pytest.raises(ValidationError, match="DEVICE_CODE_LIFETIME"):
        OIDCSettings(DEVICE_CODE_LIFETIME="PT5S", DEVICE_CODE_POLLING_INTERVAL="PT5S")
