from urllib.parse import parse_qs
from urllib.parse import urlsplit

import pytest
from joserfc import jwt

from canaille.app import models
from canaille.oidc.jose import registry


def test_oauth_implicit(testclient, user, client, backend):
    client.token_endpoint_auth_method = "none"
    backend.save(client)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="token",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
    ).follow()
    assert "text/html" == res.content_type

    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302).follow()

    assert "text/html" == res.content_type, res.json

    res = res.form.submit(name="answer", value="accept", status=303)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).fragment)

    access_token = params["access_token"][0]
    token = backend.get(models.Token, access_token=access_token)
    assert token is not None

    client.token_endpoint_auth_method = "client_secret_basic"
    backend.save(client)


@pytest.mark.parametrize(
    "grant_types", [["implicit"], ["authorization_code", "implicit"]]
)
def test_oauth_implicit_auth_method_not_none(
    testclient, user, client, backend, grant_types
):
    """Clients with a token endpoint authentication method can use the implicit flow.

    Per OpenID Connect Core §9, the implicit flow does not use the token endpoint,
    so the client does not authenticate.
    """
    client.token_endpoint_auth_method = "client_secret_basic"
    client.grant_types = grant_types
    backend.save(client)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="token",
            client_id=client.client_id,
            scope="profile",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
    ).follow()
    assert "text/html" == res.content_type

    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302).follow()

    assert "text/html" == res.content_type, res.json

    res = res.form.submit(name="answer", value="accept", status=303)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).fragment)

    access_token = params["access_token"][0]
    token = backend.get(models.Token, access_token=access_token)
    assert token is not None

    client.token_endpoint_auth_method = "client_secret_basic"
    client.grant_types = [
        "password",
        "authorization_code",
        "implicit",
        "hybrid",
        "refresh_token",
        "client_credentials",
        "urn:ietf:params:oauth:grant-type:jwt-bearer",
    ]

    backend.save(client)


def test_oidc_implicit(testclient, server_jwk, user, client, trusted_client, backend):
    client.token_endpoint_auth_method = "none"

    backend.save(client)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="id_token token",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
    ).follow()
    assert "text/html" == res.content_type

    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302).follow()

    assert "text/html" == res.content_type, res.json

    res = res.form.submit(name="answer", value="accept", status=303)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).fragment)

    access_token = params["access_token"][0]
    token = backend.get(models.Token, access_token=access_token)
    assert token is not None

    id_token = params["id_token"][0]
    claims = jwt.decode(
        id_token,
        server_jwk,
        registry=registry,
    )
    assert user.user_name == claims.claims["sub"]
    assert user.formatted_name == claims.claims["name"]
    assert [client.client_id, trusted_client.client_id] == claims.claims["aud"]

    client.token_endpoint_auth_method = "client_secret_basic"
    backend.save(client)


def test_oidc_implicit_with_group(
    testclient, server_jwk, user, client, foo_group, trusted_client, backend
):
    client.token_endpoint_auth_method = "none"

    backend.save(client)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="id_token token",
            client_id=client.client_id,
            scope="openid profile groups",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
    ).follow()
    assert "text/html" == res.content_type

    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302).follow()

    assert "text/html" == res.content_type, res.json

    res = res.form.submit(name="answer", value="accept", status=303)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).fragment)

    access_token = params["access_token"][0]
    token = backend.get(models.Token, access_token=access_token)
    assert token is not None

    id_token = params["id_token"][0]
    claims = jwt.decode(
        id_token,
        server_jwk,
        registry=registry,
    )
    assert user.user_name == claims.claims["sub"]
    assert user.formatted_name == claims.claims["name"]
    assert [client.client_id, trusted_client.client_id] == claims.claims["aud"]
    assert ["foo"] == claims.claims["groups"]

    client.token_endpoint_auth_method = "client_secret_basic"
    backend.save(client)
