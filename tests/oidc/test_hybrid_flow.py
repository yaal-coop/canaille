from urllib.parse import parse_qs
from urllib.parse import urlsplit

from authlib.jose import jwt

from canaille.app import models


def test_oauth_hybrid(testclient, backend, user, client):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code token",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
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


def test_oidc_hybrid(testclient, backend, logged_user, client, keypair, trusted_client):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code id_token token",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
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
    claims = jwt.decode(id_token, keypair[1])
    assert logged_user.user_name == claims["sub"]
    assert logged_user.formatted_name == claims["name"]
    assert [client.client_id, trusted_client.client_id] == claims["aud"]

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"
