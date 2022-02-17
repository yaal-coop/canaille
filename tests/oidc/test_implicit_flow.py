from urllib.parse import parse_qs
from urllib.parse import urlsplit

from authlib.jose import jwt
from canaille.oidc.models import Token


def test_oauth_implicit(testclient, slapd_connection, user, client):
    client.grant_type = ["token"]
    client.token_endpoint_auth_method = "none"

    client.save(slapd_connection)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="token",
            client_id=client.client_id,
            scope="profile",
            nonce="somenonce",
        ),
    )
    assert "text/html" == res.content_type

    res.form["login"] = "user"
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)

    res = res.follow()
    assert "text/html" == res.content_type, res.json

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).fragment)

    access_token = params["access_token"][0]
    token = Token.get(access_token=access_token, conn=slapd_connection)
    assert token is not None

    res = testclient.get(
        "/oauth/userinfo", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert "application/json" == res.content_type
    assert {
        "name": "John (johnny) Doe",
        "sub": "user",
        "family_name": "Doe",
        "groups": [],
    } == res.json

    client.grant_type = ["code"]
    client.token_endpoint_auth_method = "client_secret_basic"
    client.save(slapd_connection)


def test_oidc_implicit(
    testclient, keypair, slapd_connection, user, client, other_client
):
    client.grant_type = ["token id_token"]
    client.token_endpoint_auth_method = "none"

    client.save(slapd_connection)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="id_token token",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
        ),
    )
    assert "text/html" == res.content_type

    res.form["login"] = "user"
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)

    res = res.follow(status=200)
    assert "text/html" == res.content_type, res.json

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).fragment)

    access_token = params["access_token"][0]
    token = Token.get(access_token=access_token, conn=slapd_connection)
    assert token is not None

    id_token = params["id_token"][0]
    claims = jwt.decode(id_token, keypair[1])
    assert user.uid[0] == claims["sub"]
    assert user.cn[0] == claims["name"]
    assert [client.client_id, other_client.client_id] == claims["aud"]

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert "application/json" == res.content_type
    assert {
        "name": "John (johnny) Doe",
        "sub": "user",
        "family_name": "Doe",
        "groups": [],
    } == res.json

    client.grant_type = ["code"]
    client.token_endpoint_auth_method = "client_secret_basic"
    client.save(slapd_connection)


def test_oidc_implicit_with_group(
    testclient, keypair, slapd_connection, user, client, foo_group, other_client
):
    client.grant_type = ["token id_token"]
    client.token_endpoint_auth_method = "none"

    client.save(slapd_connection)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="id_token token",
            client_id=client.client_id,
            scope="openid profile groups",
            nonce="somenonce",
        ),
    )
    assert "text/html" == res.content_type

    res.form["login"] = "user"
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)

    res = res.follow(status=200)
    assert "text/html" == res.content_type, res.json

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).fragment)

    access_token = params["access_token"][0]
    token = Token.get(access_token=access_token, conn=slapd_connection)
    assert token is not None

    id_token = params["id_token"][0]
    claims = jwt.decode(id_token, keypair[1])
    assert user.uid[0] == claims["sub"]
    assert user.cn[0] == claims["name"]
    assert [client.client_id, other_client.client_id] == claims["aud"]
    assert ["foo"] == claims["groups"]

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert "application/json" == res.content_type
    assert {
        "name": "John (johnny) Doe",
        "sub": "user",
        "family_name": "Doe",
        "groups": ["foo"],
    } == res.json

    client.grant_type = ["code"]
    client.token_endpoint_auth_method = "client_secret_basic"
    client.save(slapd_connection)
