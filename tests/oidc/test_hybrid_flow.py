from urllib.parse import parse_qs
from urllib.parse import urlsplit

import pytest
from joserfc import jwt

from canaille.app import models
from canaille.oidc.jose import registry


def test_oauth_hybrid(testclient, backend, user, client):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code token",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
    ).follow()
    assert "text/html" == res.content_type, res.json

    res.form["login"] = user.user_name
    res = res.form.submit(status=302).follow()

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302).follow()

    assert "text/html" == res.content_type, res.json

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).fragment)

    code = params["code"][0]
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert authcode is not None

    access_token = params["access_token"][0]
    token = backend.get(models.Token, access_token=access_token)
    assert token is not None

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"


def test_oidc_hybrid(
    testclient, backend, logged_user, client, server_jwk, trusted_client
):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code id_token token",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
    )
    assert "text/html" == res.content_type, res.json

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).fragment)

    code = params["code"][0]
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert authcode is not None

    access_token = params["access_token"][0]
    token = backend.get(models.Token, access_token=access_token)
    assert token is not None

    id_token = params["id_token"][0]
    claims = jwt.decode(
        id_token,
        server_jwk,
        registry=registry,
    )
    assert logged_user.user_name == claims.claims["sub"]
    assert logged_user.formatted_name == claims.claims["name"]
    assert [client.client_id, trusted_client.client_id] == claims.claims["aud"]

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"


@pytest.mark.parametrize(
    ("global_value", "client_value", "nonce", "expected_success"),
    [
        (True, None, None, False),
        (True, False, None, False),
        (False, True, None, False),
        (False, False, None, False),
        (False, False, "hybrid-nonce", True),
        (True, True, "hybrid-nonce", True),
    ],
)
def test_oidc_hybrid_client_nonce_policy(
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
    client.grant_types = ["authorization_code", "hybrid"]
    client.response_types = ["code", "id_token", "token"]
    client.token_endpoint_auth_method = "none"
    backend.save(client)
    testclient.app.config["CANAILLE_OIDC"]["REQUIRE_NONCE"] = global_value

    params = {
        "response_type": "code id_token token",
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
    params = parse_qs(urlsplit(res.location).fragment)
    authcode = backend.get(models.AuthorizationCode, code=params["code"][0])
    assert authcode is not None
    assert authcode.nonce == nonce
    claims = jwt.decode(
        params["id_token"][0],
        server_jwk,
        registry=registry,
    )
    if nonce is not None:
        assert claims.claims["nonce"] == nonce
