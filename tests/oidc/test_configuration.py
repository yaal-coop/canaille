import warnings

from canaille.oidc.oauth import get_issuer


def test_issuer(testclient):
    with warnings.catch_warnings(record=True):
        testclient.app.config["CANAILLE_OIDC"]["JWT"]["ISS"] = (
            "https://anyauth.mydomain.test"
        )
        testclient.app.config["SERVER_NAME"] = "https://otherauth.mydomain.test"
        with testclient.app.test_request_context("/"):
            assert get_issuer() == "https://anyauth.mydomain.test"

        testclient.app.config["CANAILLE_OIDC"]["JWT"]["ISS"] = None
        with testclient.app.test_request_context("/"):
            assert get_issuer() == "https://otherauth.mydomain.test"

        testclient.app.config["SERVER_NAME"] = None
        with testclient.app.test_request_context("/"):
            assert get_issuer() == "http://localhost/"
