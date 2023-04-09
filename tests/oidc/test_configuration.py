import warnings

import pytest
from canaille.app.configuration import ConfigurationException
from canaille.app.configuration import validate
from canaille.oidc.oauth import get_issuer


def test_issuer(testclient):
    with warnings.catch_warnings(record=True):
        testclient.app.config["JWT"]["ISS"] = "https://anyauth.mydomain.tld"
        testclient.app.config["SERVER_NAME"] = "https://otherauth.mydomain.tld"
        with testclient.app.test_request_context("/"):
            assert get_issuer() == "https://anyauth.mydomain.tld"

        del testclient.app.config["JWT"]["ISS"]
        with testclient.app.test_request_context("/"):
            assert get_issuer() == "https://otherauth.mydomain.tld"

        testclient.app.config["SERVER_NAME"] = None
        with testclient.app.test_request_context("/"):
            assert get_issuer() == "http://localhost/"


def test_no_private_key(configuration):
    configuration["JWT"]["PRIVATE_KEY"] = "invalid-path"
    with pytest.raises(
        ConfigurationException,
        match=r"Private key does not exist",
    ):
        validate(configuration)


def test_no_public_key(configuration):
    configuration["JWT"]["PUBLIC_KEY"] = "invalid-path"
    with pytest.raises(
        ConfigurationException,
        match=r"Public key does not exist",
    ):
        validate(configuration)
