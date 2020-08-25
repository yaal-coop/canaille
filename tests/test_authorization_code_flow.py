from . import client_credentials
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from urllib.parse import urlsplit, parse_qs
from web.models import AuthorizationCode, Token
from werkzeug.security import gen_salt


def test_authorization_code_flow(testclient, slapd_connection, logged_user, client):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.oauthClientID,
            scope="profile",
            nonce="somenonce",
        ),
    )
    assert 200 == res.status_code

    res = res.forms["accept"].submit()
    assert 302 == res.status_code

    assert res.location.startswith(client.oauthRedirectURIs[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code, conn=slapd_connection)
    assert authcode is not None

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="profile",
            redirect_uri=client.oauthRedirectURIs[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    )
    assert 200 == res.status_code
    access_token = res.json["access_token"]

    token = Token.get(access_token, conn=slapd_connection)
    assert token is not None

    res = testclient.get("/api/me", headers={"Authorization": f"Bearer {access_token}"})
    assert 200 == res.status_code
    assert {"foo": "bar"} == res.json


def test_logout_login(testclient, slapd_connection, logged_user, client):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.oauthClientID,
            scope="profile",
            nonce="somenonce",
        ),
    )
    assert 200 == res.status_code

    res = res.forms["logout"].submit()
    assert 302 == res.status_code
    res = res.follow()
    assert 200 == res.status_code

    res.form["login"] = logged_user.name
    res.form["password"] = "wrong password"
    res = res.form.submit()
    assert 200 == res.status_code
    assert b"Login failed, please check your information" in res.body

    res.form["login"] = logged_user.name
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()
    assert 302 == res.status_code
    res = res.follow()
    assert 200 == res.status_code

    res = res.forms["accept"].submit()
    assert 302 == res.status_code

    assert res.location.startswith(client.oauthRedirectURIs[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code, conn=slapd_connection)
    assert authcode is not None

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="profile",
            redirect_uri=client.oauthRedirectURIs[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    )
    assert 200 == res.status_code
    access_token = res.json["access_token"]

    token = Token.get(access_token, conn=slapd_connection)
    assert token is not None

    res = testclient.get("/api/me", headers={"Authorization": f"Bearer {access_token}"})
    assert 200 == res.status_code
    assert {"foo": "bar"} == res.json


def test_refresh_token(testclient, slapd_connection, logged_user, client):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.oauthClientID,
            scope="profile",
            nonce="somenonce",
        ),
    )
    assert 200 == res.status_code

    res = res.forms["accept"].submit()
    assert 302 == res.status_code

    assert res.location.startswith(client.oauthRedirectURIs[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code, conn=slapd_connection)
    assert authcode is not None

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="profile",
            redirect_uri=client.oauthRedirectURIs[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    )
    assert 200 == res.status_code
    access_token = res.json["access_token"]
    old_token = Token.get(access_token, conn=slapd_connection)
    assert old_token is not None
    assert not old_token.revoked

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="refresh_token", refresh_token=res.json["refresh_token"],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    )
    assert 200 == res.status_code
    access_token = res.json["access_token"]
    new_token = Token.get(access_token, conn=slapd_connection)
    assert new_token is not None
    old_token.reload(slapd_connection)
    assert old_token.revoked

    res = testclient.get("/api/me", headers={"Authorization": f"Bearer {access_token}"})
    assert 200 == res.status_code
    assert {"foo": "bar"} == res.json


def test_code_challenge(testclient, slapd_connection, logged_user, client):
    code_verifier = gen_salt(48)
    code_challenge = create_s256_code_challenge(code_verifier)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            code_challenge=code_challenge,
            code_challenge_method="S256",
            response_type="code",
            client_id=client.oauthClientID,
            scope="profile",
            nonce="somenonce",
        ),
    )
    assert 200 == res.status_code

    res = res.forms["accept"].submit()
    assert 302 == res.status_code

    assert res.location.startswith(client.oauthRedirectURIs[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code, conn=slapd_connection)
    assert authcode is not None

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="profile",
            code_verifier=code_verifier,
            redirect_uri=client.oauthRedirectURIs[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    )
    assert 200 == res.status_code
    access_token = res.json["access_token"]

    token = Token.get(access_token, conn=slapd_connection)
    assert token is not None

    res = testclient.get("/api/me", headers={"Authorization": f"Bearer {access_token}"})
    assert 200 == res.status_code
    assert {"foo": "bar"} == res.json
