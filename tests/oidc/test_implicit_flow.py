from urllib.parse import parse_qs
from urllib.parse import urlsplit

from authlib.jose import jwt

from canaille.app import models


def test_oauth_implicit(testclient, user, client, backend):
    client.grant_types = ["token"]
    client.token_endpoint_auth_method = "none"

    backend.save(client)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="token",
            client_id=client.client_id,
            scope="profile",
            nonce="somenonce",
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

    res = testclient.get(
        "/oauth/userinfo", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert "application/json" == res.content_type
    assert res.json["name"] == "John (johnny) Doe"

    client.grant_types = ["code"]
    client.token_endpoint_auth_method = "client_secret_basic"
    backend.save(client)


def test_oidc_implicit(testclient, keypair, user, client, trusted_client, backend):
    client.grant_types = ["token id_token"]
    client.token_endpoint_auth_method = "none"

    backend.save(client)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="id_token token",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
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
    claims = jwt.decode(id_token, keypair[1])
    assert user.user_name == claims["sub"]
    assert user.formatted_name == claims["name"]
    assert [client.client_id, trusted_client.client_id] == claims["aud"]

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert "application/json" == res.content_type
    assert res.json["name"] == "John (johnny) Doe"

    client.grant_types = ["code"]
    client.token_endpoint_auth_method = "client_secret_basic"
    backend.save(client)


def test_oidc_implicit_with_group(
    testclient, keypair, user, client, foo_group, trusted_client, backend
):
    client.grant_types = ["token id_token"]
    client.token_endpoint_auth_method = "none"

    backend.save(client)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="id_token token",
            client_id=client.client_id,
            scope="openid profile groups",
            nonce="somenonce",
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
    claims = jwt.decode(id_token, keypair[1])
    assert user.user_name == claims["sub"]
    assert user.formatted_name == claims["name"]
    assert [client.client_id, trusted_client.client_id] == claims["aud"]
    assert ["foo"] == claims["groups"]

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert "application/json" == res.content_type
    assert res.json["name"] == "John (johnny) Doe"

    client.grant_types = ["code"]
    client.token_endpoint_auth_method = "client_secret_basic"
    backend.save(client)
