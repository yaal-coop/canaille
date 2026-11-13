from urllib.parse import parse_qs
from urllib.parse import urlsplit

from joserfc import jwt

from canaille.oidc.jose import registry

from . import client_credentials

USERINFO_ENDPOINT = "http://canaille.test/oauth/userinfo"


def get_tokens(testclient, client):
    """Get tokens for ``client`` with the authorization code flow."""
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            redirect_uri=client.redirect_uris[0],
        ),
    )
    if res.status_code == 200:
        res = res.form.submit(name="answer", value="accept", status=303)
    code = parse_qs(urlsplit(res.location).query)["code"][0]

    return testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    ).json


def get_client_credentials_token(testclient, client, scope):
    return testclient.post(
        "/oauth/token",
        params=dict(grant_type="client_credentials", scope=scope),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    ).json["access_token"]


def decode(token, server_jwk):
    return jwt.decode(token, server_jwk, registry=registry)


def test_access_token_format(testclient, logged_user, client, server_jwk):
    """Per RFC 9068 §2, access tokens are JWTs with the 'at+jwt' type."""
    access_token = get_tokens(testclient, client)["access_token"]

    token = decode(access_token, server_jwk)
    assert token.header == {"typ": "at+jwt", "alg": "RS256", "kid": server_jwk.kid}

    claims = token.claims
    assert claims["iss"] == "http://canaille.test"
    assert claims["sub"] == logged_user.user_name
    assert claims["client_id"] == client.client_id
    assert claims["scope"] == "openid profile"
    assert claims["jti"]
    assert claims["exp"] - claims["iat"] == 3600
    assert claims["name"] == logged_user.formatted_name


def test_audience(testclient, logged_user, client, trusted_client, server_jwk):
    """Per RFC 9068 §3, the audience is the userinfo endpoint and the client audience.

    The client itself is not an audience, so the access token cannot be used
    as an ID token.
    """
    access_token = get_tokens(testclient, client)["access_token"]

    claims = decode(access_token, server_jwk).claims
    assert claims["aud"] == [USERINFO_ENDPOINT, trusted_client.client_id]


def test_client_credentials(testclient, client, trusted_client, server_jwk):
    """Per RFC 9068 §2.2, the subject of a client credentials token is the client."""
    access_token = get_client_credentials_token(testclient, client, "profile")

    claims = decode(access_token, server_jwk).claims
    assert claims["sub"] == client.client_id
    assert claims["client_id"] == client.client_id
    assert claims["aud"] == [trusted_client.client_id]
    assert "name" not in claims


def test_default_audience(testclient, client, server_jwk, backend):
    """Per RFC 9068 §3, the audience is the issuer when no resource is concerned."""
    client.audience = [client]
    backend.save(client)

    access_token = get_client_credentials_token(testclient, client, "profile")

    claims = decode(access_token, server_jwk).claims
    assert claims["aud"] == ["http://canaille.test"]


def test_plain_access_tokens(testclient, logged_user, client, monkeypatch):
    """Plain access tokens are random strings, checked with introspection."""
    monkeypatch.setitem(
        testclient.app.config["CANAILLE_OIDC"], "ACCESS_TOKEN_TYPE", "plain"
    )

    access_token = get_tokens(testclient, client)["access_token"]
    assert "." not in access_token

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["sub"] == logged_user.user_name

    res = testclient.post(
        "/oauth/introspect",
        params=dict(token=access_token),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    assert res.json["active"]
    assert res.json["sub"] == logged_user.user_name


def test_subject_without_openid_scope(
    testclient, user, client, server_jwk, monkeypatch
):
    """The subject follows the userinfo mapping, even without the openid scope."""
    monkeypatch.setitem(
        testclient.app.config["CANAILLE_OIDC"]["USERINFO_MAPPING"],
        "SUB",
        "{{ user.id }}",
    )

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="password",
            username="user",
            password="correct horse battery staple",
            scope="profile",
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    claims = decode(res.json["access_token"], server_jwk).claims
    assert claims["sub"] == user.id


def test_introspection_audience(testclient, logged_user, client, server_jwk):
    """The introspection response has the audience of the access token."""
    access_token = get_tokens(testclient, client)["access_token"]

    res = testclient.post(
        "/oauth/introspect",
        params=dict(token=access_token),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    assert res.json["aud"] == decode(access_token, server_jwk).claims["aud"]
