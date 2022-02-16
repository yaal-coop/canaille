from urllib.parse import parse_qs
from urllib.parse import urlsplit

from authlib.jose import jwt
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from canaille.oidc.models import AuthorizationCode
from canaille.oidc.models import Consent
from canaille.oidc.models import Token
from werkzeug.security import gen_salt

from . import client_credentials


def test_authorization_code_flow(
    testclient, slapd_connection, logged_user, client, keypair, other_client
):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="profile",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code, conn=slapd_connection)
    assert authcode is not None

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="profile",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    access_token = res.json["access_token"]
    token = Token.get(access_token=access_token, conn=slapd_connection)
    assert token.client == client.dn
    assert token.subject == logged_user.dn

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, keypair[1])
    assert logged_user.uid[0] == claims["sub"]
    assert logged_user.cn[0] == claims["name"]
    assert [client.client_id, other_client.client_id] == claims["aud"]

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert {
        "name": "John (johnny) Doe",
        "family_name": "Doe",
        "sub": "user",
        "groups": [],
    } == res.json

    for consent in Consent.filter(conn=slapd_connection):
        consent.delete(conn=slapd_connection)


def test_authorization_code_flow_preconsented(
    testclient, slapd_connection, logged_user, client, keypair, other_client
):
    client.preconsent = True
    client.save(conn=slapd_connection)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="profile",
            nonce="somenonce",
        ),
        status=302,
    )

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code, conn=slapd_connection)
    assert authcode is not None

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="profile",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    access_token = res.json["access_token"]
    token = Token.get(access_token=access_token, conn=slapd_connection)
    assert token.client == client.dn
    assert token.subject == logged_user.dn

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, keypair[1])
    assert logged_user.uid[0] == claims["sub"]
    assert logged_user.cn[0] == claims["name"]
    assert [client.client_id, other_client.client_id] == claims["aud"]

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert {
        "name": "John (johnny) Doe",
        "family_name": "Doe",
        "sub": "user",
        "groups": [],
    } == res.json

    for consent in Consent.filter(conn=slapd_connection):
        consent.delete(conn=slapd_connection)


def test_logout_login(testclient, slapd_connection, logged_user, client):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="profile",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="logout", status=302)
    res = res.follow(status=200)

    res.form["login"] = logged_user.name
    res.form["password"] = "wrong password"
    res = res.form.submit(status=200)
    assert "Login failed, please check your information" in res.text

    res.form["login"] = logged_user.name
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code, conn=slapd_connection)
    assert authcode is not None

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="profile",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    access_token = res.json["access_token"]
    token = Token.get(access_token=access_token, conn=slapd_connection)
    assert token.client == client.dn
    assert token.subject == logged_user.dn

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert {
        "name": "John (johnny) Doe",
        "family_name": "Doe",
        "sub": "user",
        "groups": [],
    } == res.json

    for consent in Consent.filter(conn=slapd_connection):
        consent.delete(conn=slapd_connection)


def test_refresh_token(testclient, slapd_connection, logged_user, client):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="profile",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code, conn=slapd_connection)
    assert authcode is not None

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="profile",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    access_token = res.json["access_token"]
    old_token = Token.get(access_token=access_token, conn=slapd_connection)
    assert old_token is not None
    assert not old_token.revokation_date

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="refresh_token",
            refresh_token=res.json["refresh_token"],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    access_token = res.json["access_token"]
    new_token = Token.get(access_token=access_token, conn=slapd_connection)
    assert new_token is not None
    old_token.reload(slapd_connection)
    assert old_token.revokation_date

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert {
        "name": "John (johnny) Doe",
        "family_name": "Doe",
        "sub": "user",
        "groups": [],
    } == res.json


def test_code_challenge(testclient, slapd_connection, logged_user, client):
    client.token_endpoint_auth_method = "none"
    client.save(slapd_connection)

    code_verifier = gen_salt(48)
    code_challenge = create_s256_code_challenge(code_verifier)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            code_challenge=code_challenge,
            code_challenge_method="S256",
            response_type="code",
            client_id=client.client_id,
            scope="profile",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code, conn=slapd_connection)
    assert authcode is not None

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="profile",
            code_verifier=code_verifier,
            redirect_uri=client.redirect_uris[0],
            client_id=client.client_id,
        ),
        status=200,
    )
    access_token = res.json["access_token"]

    token = Token.get(access_token=access_token, conn=slapd_connection)
    assert token.client == client.dn
    assert token.subject == logged_user.dn

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert {
        "name": "John (johnny) Doe",
        "family_name": "Doe",
        "sub": "user",
        "groups": [],
    } == res.json

    client.token_endpoint_auth_method = "client_secret_basic"
    client.save(slapd_connection)

    for consent in Consent.filter(conn=slapd_connection):
        consent.delete(conn=slapd_connection)


def test_authorization_code_flow_when_consent_already_given(
    testclient, slapd_connection, logged_user, client
):
    assert not Consent.filter(conn=slapd_connection)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="profile",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code, conn=slapd_connection)
    assert authcode is not None

    consents = Consent.filter(
        client=client.dn, subject=logged_user.dn, conn=slapd_connection
    )
    assert "profile" in consents[0].scope

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="profile",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    assert "access_token" in res.json

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="profile",
            nonce="somenonce",
        ),
        status=302,
    )
    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    assert "code" in params

    for consent in Consent.filter(conn=slapd_connection):
        consent.delete(conn=slapd_connection)


def test_authorization_code_flow_when_consent_already_given_but_for_a_smaller_scope(
    testclient, slapd_connection, logged_user, client
):
    assert not Consent.filter(conn=slapd_connection)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="profile",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code, conn=slapd_connection)
    assert authcode is not None

    consents = Consent.filter(
        client=client.dn, subject=logged_user.dn, conn=slapd_connection
    )
    assert "profile" in consents[0].scope
    assert "groups" not in consents[0].scope

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="profile",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    assert "access_token" in res.json

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="profile groups",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code, conn=slapd_connection)
    assert authcode is not None

    consents = Consent.filter(
        client=client.dn, subject=logged_user.dn, conn=slapd_connection
    )
    assert "profile" in consents[0].scope
    assert "groups" in consents[0].scope

    for consent in Consent.filter(conn=slapd_connection):
        consent.delete(conn=slapd_connection)


def test_authorization_code_flow_but_user_cannot_use_oidc(
    testclient, slapd_connection, user, client, keypair, other_client
):
    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = []

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="profile",
            nonce="somenonce",
        ),
        status=200,
    )

    res.form["login"] = "John (johnny) Doe"
    res = res.form.submit(status=200)

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)
    res = res.follow(status=400)

    for consent in Consent.filter(conn=slapd_connection):
        consent.delete(conn=slapd_connection)


def test_prompt_none(testclient, slapd_connection, logged_user, client):
    consent = Consent(
        client=client.dn,
        subject=logged_user.dn,
        scope=["openid", "profile"],
    )
    consent.save(conn=slapd_connection)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="profile",
            nonce="somenonce",
            prompt="none",
        ),
        status=302,
    )
    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    assert "code" in params
    consent.delete(conn=slapd_connection)


def test_prompt_not_logged(testclient, slapd_connection, user, client):
    consent = Consent(
        client=client.dn,
        subject=user.dn,
        scope=["openid", "profile"],
    )
    consent.save(conn=slapd_connection)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="profile",
            nonce="somenonce",
            prompt="none",
        ),
        status=200,
    )
    assert "login_required" == res.json.get("error")
    consent.delete(conn=slapd_connection)


def test_prompt_no_consent(testclient, slapd_connection, logged_user, client):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="profile",
            nonce="somenonce",
            prompt="none",
        ),
        status=200,
    )
    assert "consent_required" == res.json.get("error")
