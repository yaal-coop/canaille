import warnings

import pytest

from canaille.app.configuration import ConfigurationException
from canaille.app.configuration import validate
from canaille.oidc.oauth import get_issuer


def test_issuer(testclient):
    with warnings.catch_warnings(record=True):
        testclient.app.config["CANAILLE_OIDC"]["JWT"]["ISS"] = (
            "https://anyauth.mydomain.tld"
        )
        testclient.app.config["SERVER_NAME"] = "https://otherauth.mydomain.tld"
        with testclient.app.test_request_context("/"):
            assert get_issuer() == "https://anyauth.mydomain.tld"

        del testclient.app.config["CANAILLE_OIDC"]["JWT"]["ISS"]
        with testclient.app.test_request_context("/"):
            assert get_issuer() == "https://otherauth.mydomain.tld"

        testclient.app.config["SERVER_NAME"] = None
        with testclient.app.test_request_context("/"):
            assert get_issuer() == "http://localhost/"


def test_no_private_key(testclient, configuration):
    del configuration["CANAILLE_OIDC"]["JWT"]["PRIVATE_KEY"]
    with pytest.raises(
        ConfigurationException,
        match=r"No private key has been set",
    ):
        validate(configuration)


def test_no_public_key(testclient, configuration):
    del configuration["CANAILLE_OIDC"]["JWT"]["PUBLIC_KEY"]
    with pytest.raises(
        ConfigurationException,
        match=r"No public key has been set",
    ):
        validate(configuration)
