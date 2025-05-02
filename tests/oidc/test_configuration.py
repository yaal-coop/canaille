import warnings

from canaille.oidc.oauth import get_issuer


def test_issuer(testclient):
    with warnings.catch_warnings(record=True):
        with testclient.app.test_request_context("/"):
            assert get_issuer() == "http://canaille.test"

        testclient.app.config["SERVER_NAME"] = None
        with testclient.app.test_request_context("/"):
            assert get_issuer() == "http://localhost/"
