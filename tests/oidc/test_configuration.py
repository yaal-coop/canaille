import warnings

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
