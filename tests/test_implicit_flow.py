from authlib.jose import jwt
from urllib.parse import urlsplit, parse_qs
from web.models import Token


def test_oauth_implicit(testclient, slapd_connection, user, client):
    client.oauthGrantType = ["token"]
    client.oauthTokenEndpointAuthMethod = "none"

    client.save(slapd_connection)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="token",
            client_id=client.oauthClientID,
            scope="profile",
            nonce="somenonce",
        ),
    )
    assert (200, "text/html") == (res.status_code, res.content_type)

    res.form["login"] = user.name
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()
    assert 302 == res.status_code

    res = res.follow()
    assert (200, "text/html") == (res.status_code, res.content_type), res.json

    res = res.forms["accept"].submit()
    assert 302 == res.status_code

    assert res.location.startswith(client.oauthRedirectURIs[0])
    params = parse_qs(urlsplit(res.location).fragment)

    access_token = params["access_token"][0]
    token = Token.get(access_token, conn=slapd_connection)
    assert token is not None

    res = testclient.get("/api/me", headers={"Authorization": f"Bearer {access_token}"})
    assert (200, "application/json") == (res.status_code, res.content_type)
    assert {"foo": "bar"} == res.json

    client.oauthGrantType = ["code"]
    client.oauthTokenEndpointAuthMethod = "client_secret_basic"
    client.save(slapd_connection)


def test_oidc_implicit(testclient, slapd_connection, user, client):
    client.oauthGrantType = ["token id_token"]
    client.oauthTokenEndpointAuthMethod = "none"

    client.save(slapd_connection)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="id_token token",
            client_id=client.oauthClientID,
            scope="openid profile",
            nonce="somenonce",
        ),
    )
    assert (200, "text/html") == (res.status_code, res.content_type)

    res.form["login"] = user.name
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()
    assert 302 == res.status_code

    res = res.follow()
    assert (200, "text/html") == (res.status_code, res.content_type), res.json

    res = res.forms["accept"].submit()
    assert 302 == res.status_code

    assert res.location.startswith(client.oauthRedirectURIs[0])
    params = parse_qs(urlsplit(res.location).fragment)

    access_token = params["access_token"][0]
    token = Token.get(access_token, conn=slapd_connection)
    assert token is not None

    id_token = params["id_token"][0]
    claims = jwt.decode(id_token, "secret-key")
    assert user.dn == claims['sub']
    assert user.sn == claims['name']

    res = testclient.get("/api/me", headers={"Authorization": f"Bearer {access_token}"})
    assert (200, "application/json") == (res.status_code, res.content_type)
    assert {"foo": "bar"} == res.json

    client.oauthGrantType = ["code"]
    client.oauthTokenEndpointAuthMethod = "client_secret_basic"
    client.save(slapd_connection)
