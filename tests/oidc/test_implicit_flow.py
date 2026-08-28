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

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).fragment)

    access_token = params["access_token"][0]
    token = backend.get(models.Token, access_token=access_token)
    assert token is not None

    client.token_endpoint_auth_method = "client_secret_basic"
    backend.save(client)


def test_oauth_implicit_auth_method_not_none(testclient, user, client, backend):
    """Even when token_endpoint_auth_method is not none, the client should be able to not authenticate if its only grant type is implicit.

    oidc-core §9 indicates that the 'none' token endpoint authentication method is used when:

         The Client does not authenticate itself at the Token Endpoint, either because it uses only the Implicit Flow (and so does not use the Token Endpoint) or because it is a Public Client with no Client Secret or other authentication mechanism.
    """
    client.token_endpoint_auth_method = "client_secret_basic"
    client.grant_types = ["implicit"]
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

    res = res.form.submit(name="answer", value="accept", status=302)

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

    res = res.form.submit(name="answer", value="accept", status=302)

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

    res = res.form.submit(name="answer", value="accept", status=302)

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


@pytest.mark.parametrize(
    ("global_value", "client_value", "nonce", "expected_success"),
    [
        (True, None, None, False),
        (True, False, None, False),
        (False, True, None, False),
        (False, False, None, False),
        (False, False, "implicit-nonce", True),
        (True, True, "implicit-nonce", True),
    ],
)
def test_oidc_implicit_client_nonce_policy(
    testclient,
    logged_user,
    client,
    backend,
    server_jwk,
    global_value,
    client_value,
    nonce,
    expected_success,
):
    client.require_nonce = client_value
    client.grant_types = ["implicit"]
    client.response_types = ["id_token", "token"]
    client.token_endpoint_auth_method = "none"
    backend.save(client)
    testclient.app.config["CANAILLE_OIDC"]["REQUIRE_NONCE"] = global_value

    params = {
        "response_type": "id_token token",
        "client_id": client.client_id,
        "scope": "openid profile",
        "redirect_uri": client.redirect_uris[0],
    }
    if nonce is not None:
        params["nonce"] = nonce

    res = testclient.get("/oauth/authorize", params=params)
    if not expected_success:
        assert res.status_int == 302
        assert "error=invalid_request" in res.location
        return

    assert res.status_int == 200, res.json
    res = res.form.submit(name="answer", value="accept", status=302)
    assert res.location.startswith(client.redirect_uris[0])
    claims = jwt.decode(
        parse_qs(urlsplit(res.location).fragment)["id_token"][0],
        server_jwk,
        registry=registry,
    )
    if nonce is not None:
        assert claims.claims["nonce"] == nonce
