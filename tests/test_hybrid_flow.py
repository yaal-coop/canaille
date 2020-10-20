from authlib.jose import jwt
from urllib.parse import urlsplit, parse_qs
from oidc_ldap_bridge.models import AuthorizationCode, Token


def test_oauth_hybrid(testclient, slapd_connection, user, client):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code token",
            client_id=client.oauthClientID,
            scope="openid profile",
            nonce="somenonce",
        ),
    )
    assert (200, "text/html") == (res.status_code, res.content_type), res.json

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

    code = params["code"][0]
    authcode = AuthorizationCode.get(code, conn=slapd_connection)
    assert authcode is not None

    access_token = params["access_token"][0]
    token = Token.get(access_token, conn=slapd_connection)
    assert token is not None

    res = testclient.get(
        "/oauth/userinfo", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert 200 == res.status_code
    assert {"name": "John Doe", "family_name": "Doe", "sub": "user"} == res.json


def test_oidc_hybrid(testclient, slapd_connection, logged_user, client, keypair):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code id_token token",
            client_id=client.oauthClientID,
            scope="openid profile",
            nonce="somenonce",
        ),
    )
    assert (200, "text/html") == (res.status_code, res.content_type), res.json

    res = res.forms["accept"].submit()
    assert 302 == res.status_code

    assert res.location.startswith(client.oauthRedirectURIs[0])
    params = parse_qs(urlsplit(res.location).fragment)

    code = params["code"][0]
    authcode = AuthorizationCode.get(code, conn=slapd_connection)
    assert authcode is not None

    access_token = params["access_token"][0]
    token = Token.get(access_token, conn=slapd_connection)
    assert token is not None

    id_token = params["id_token"][0]
    claims = jwt.decode(id_token, keypair[1])
    assert logged_user.uid[0] == claims["sub"]
    assert logged_user.cn[0] == claims["name"]
    assert [client.oauthClientID] == claims["aud"]

    res = testclient.get(
        "/oauth/userinfo", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert 200 == res.status_code
    assert {"name": "John Doe", "family_name": "Doe", "sub": "user"} == res.json
