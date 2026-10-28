import pytest

from . import client_credentials

INTERNAL_HOST = "canaille.foobar.test"


@pytest.mark.parametrize(
    "path",
    [
        "/.well-known/openid-configuration",
        "/.well-known/oauth-authorization-server",
        "/.well-known/webfinger?resource=acct%3Auser%40mydomain.test&rel=http%3A%2F%2Fopenid.net%2Fspecs%2Fconnect%2F1.0%2Fissuer",
        "/oauth/jwks.json",
    ],
)
def test_discovery_on_any_host(testclient, user, path):
    """Other servers can read the discovery documents on any host name."""
    res = testclient.get(path, headers={"Host": INTERNAL_HOST}, status=200)
    assert INTERNAL_HOST not in res.text


def test_introspection_on_any_host(testclient, client, token):
    """Other servers can introspect tokens on any host name."""
    res = testclient.post(
        "/oauth/introspect",
        params=dict(token=token.access_token),
        headers={
            "Authorization": f"Basic {client_credentials(client)}",
            "Host": INTERNAL_HOST,
        },
        status=200,
    )
    assert res.json["active"]
    assert res.json["iss"] == "http://canaille.test"


def test_userinfo_on_any_host(testclient, token):
    """Other servers can read the user information on any host name."""
    res = testclient.get(
        "/oauth/userinfo",
        headers={
            "Authorization": f"Bearer {token.access_token}",
            "Host": INTERNAL_HOST,
        },
        status=200,
    )
    assert INTERNAL_HOST not in res.text


def test_authorization_is_redirected_to_server_name(testclient, client):
    """The pages that browsers display are redirected to SERVER_NAME."""
    res = testclient.get(
        "/oauth/authorize",
        params=dict(client_id=client.client_id, response_type="code"),
        headers={"Host": INTERNAL_HOST},
        status=302,
    )
    assert res.location.startswith("http://canaille.test/oauth/authorize?")
