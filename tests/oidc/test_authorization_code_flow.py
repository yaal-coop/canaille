from urllib.parse import parse_qs
from urllib.parse import urlsplit

import freezegun
from authlib.jose import jwt
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from canaille.oidc.models import AuthorizationCode
from canaille.oidc.models import Consent
from canaille.oidc.models import Token
from werkzeug.security import gen_salt

from . import client_credentials


def test_authorization_code_flow(
    testclient, logged_user, client, keypair, other_client
):
    assert not Consent.all()

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile email groups address phone",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code)
    assert authcode is not None
    assert set(authcode.scope[0].split(" ")) == {
        "openid",
        "profile",
        "email",
        "groups",
        "address",
        "phone",
    }

    consents = Consent.filter(client=client.dn, subject=logged_user.dn)
    assert set(consents[0].scope) == {
        "openid",
        "profile",
        "email",
        "groups",
        "address",
        "phone",
    }

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid profile email groups address phone",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    access_token = res.json["access_token"]
    token = Token.get(access_token=access_token)
    assert token.client == client.dn
    assert token.subject == logged_user.dn
    assert set(token.scope[0].split(" ")) == {
        "openid",
        "profile",
        "email",
        "groups",
        "address",
        "phone",
    }

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
        "preferred_username": "Johnny",
        "email": "john@doe.com",
        "sub": "user",
        "groups": [],
        "locale": "en",
    } == res.json

    for consent in consents:
        consent.delete()


def test_authorization_code_flow_preconsented(
    testclient, logged_user, client, keypair, other_client
):
    assert not Consent.all()

    client.preconsent = True
    client.save()

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
        ),
        status=302,
    )

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code)
    assert authcode is not None

    consents = Consent.filter(client=client.dn, subject=logged_user.dn)
    assert not consents

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid profile",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    access_token = res.json["access_token"]
    token = Token.get(access_token=access_token)
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
        "preferred_username": "Johnny",
        "sub": "user",
        "locale": "en",
    } == res.json


def test_logout_login(testclient, logged_user, client):
    assert not Consent.all()

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
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
    authcode = AuthorizationCode.get(code=code)
    assert authcode is not None

    consents = Consent.filter(client=client.dn, subject=logged_user.dn)
    assert "profile" in consents[0].scope

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid profile",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    access_token = res.json["access_token"]
    token = Token.get(access_token=access_token)
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
        "preferred_username": "Johnny",
        "sub": "user",
        "locale": "en",
    } == res.json

    for consent in consents:
        consent.delete()


def test_refresh_token(testclient, user, client):
    assert not Consent.all()

    with freezegun.freeze_time("2020-01-01 01:00:00"):
        res = testclient.get(
            "/oauth/authorize",
            params=dict(
                response_type="code",
                client_id=client.client_id,
                scope="openid profile",
                nonce="somenonce",
            ),
            status=200,
        )

        res.form["login"] = "John (johnny) Doe"
        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(name="answer", value="accept", status=302)
        res = res.follow()
        res = res.form.submit(name="answer", value="accept", status=302)

        assert res.location.startswith(client.redirect_uris[0])
        params = parse_qs(urlsplit(res.location).query)
        code = params["code"][0]
        authcode = AuthorizationCode.get(code=code)
        assert authcode is not None

        consents = Consent.filter(client=client.dn, subject=user.dn)
        assert "profile" in consents[0].scope

    with freezegun.freeze_time("2020-01-01 00:01:00"):
        res = testclient.post(
            "/oauth/token",
            params=dict(
                grant_type="authorization_code",
                code=code,
                scope="openid profile",
                redirect_uri=client.redirect_uris[0],
            ),
            headers={"Authorization": f"Basic {client_credentials(client)}"},
            status=200,
        )
        access_token = res.json["access_token"]
        old_token = Token.get(access_token=access_token)
        assert old_token is not None
        assert not old_token.revokation_date

    with freezegun.freeze_time("2020-01-01 00:02:00"):
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
        new_token = Token.get(access_token=access_token)
        assert new_token is not None
        assert old_token.access_token != new_token.access_token

        old_token.reload()
        assert old_token.revokation_date

    with freezegun.freeze_time("2020-01-01 00:03:00"):
        res = testclient.get(
            "/oauth/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            status=200,
        )
        assert {
            "name": "John (johnny) Doe",
            "family_name": "Doe",
            "preferred_username": "Johnny",
            "sub": "user",
            "locale": "en",
        } == res.json

    for consent in consents:
        consent.delete()


def test_code_challenge(testclient, logged_user, client):
    assert not Consent.all()

    client.token_endpoint_auth_method = "none"
    client.save()

    code_verifier = gen_salt(48)
    code_challenge = create_s256_code_challenge(code_verifier)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            code_challenge=code_challenge,
            code_challenge_method="S256",
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code)
    assert authcode is not None

    consents = Consent.filter(client=client.dn, subject=logged_user.dn)
    assert "profile" in consents[0].scope

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid profile",
            code_verifier=code_verifier,
            redirect_uri=client.redirect_uris[0],
            client_id=client.client_id,
        ),
        status=200,
    )
    access_token = res.json["access_token"]

    token = Token.get(access_token=access_token)
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
        "preferred_username": "Johnny",
        "sub": "user",
        "locale": "en",
    } == res.json

    client.token_endpoint_auth_method = "client_secret_basic"
    client.save()

    for consent in consents:
        consent.delete()


def test_authorization_code_flow_when_consent_already_given(
    testclient, logged_user, client
):
    assert not Consent.all()

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code)
    assert authcode is not None

    consents = Consent.filter(client=client.dn, subject=logged_user.dn)
    assert "profile" in consents[0].scope

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid profile",
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
            scope="openid profile",
            nonce="somenonce",
        ),
        status=302,
    )
    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    assert "code" in params

    for consent in consents:
        consent.delete()


def test_authorization_code_flow_when_consent_already_given_but_for_a_smaller_scope(
    testclient, logged_user, client
):
    assert not Consent.all()

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code)
    assert authcode is not None

    consents = Consent.filter(client=client.dn, subject=logged_user.dn)
    assert "profile" in consents[0].scope
    assert "groups" not in consents[0].scope

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid profile",
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
            scope="openid profile groups",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code)
    assert authcode is not None

    consents = Consent.filter(client=client.dn, subject=logged_user.dn)
    assert "profile" in consents[0].scope
    assert "groups" in consents[0].scope

    for consent in consents:
        consent.delete()


def test_authorization_code_flow_but_user_cannot_use_oidc(
    testclient, user, client, keypair, other_client
):
    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = []

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
        ),
        status=200,
    )

    res.form["login"] = "John (johnny) Doe"
    res = res.form.submit(status=200)

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)
    res = res.follow(status=400)


def test_prompt_none(testclient, logged_user, client):
    consent = Consent(
        client=client.dn,
        subject=logged_user.dn,
        scope=["openid", "profile"],
    )
    consent.save()

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="none",
        ),
        status=302,
    )
    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    assert "code" in params

    consent.delete()


def test_prompt_not_logged(testclient, user, client):
    consent = Consent(
        client=client.dn,
        subject=user.dn,
        scope=["openid", "profile"],
    )
    consent.save()

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="none",
        ),
        status=200,
    )
    assert "login_required" == res.json.get("error")

    consent.delete()


def test_prompt_no_consent(testclient, logged_user, client):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="none",
        ),
        status=200,
    )
    assert "consent_required" == res.json.get("error")


def test_nonce_required_in_oidc_requests(testclient, logged_user, client):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
        ),
        status=200,
    )

    assert res.json.get("error") == "invalid_request"


def test_nonce_not_required_in_oauth_requests(testclient, logged_user, client):
    assert not Consent.all()
    testclient.app.config["REQUIRE_NONCE"] = False

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="profile",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    for consent in Consent.all():
        consent.delete()


def test_authorization_code_request_scope_too_large(
    testclient, logged_user, keypair, other_client
):
    assert not Consent.all()
    assert "email" not in other_client.scope

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=other_client.client_id,
            scope="openid profile email",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = AuthorizationCode.get(code=code)
    assert set(authcode.scope[0].split(" ")) == {
        "openid",
        "profile",
    }

    consents = Consent.filter(client=other_client.dn, subject=logged_user.dn)
    assert set(consents[0].scope) == {
        "openid",
        "profile",
    }

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid profile email groups address phone",
            redirect_uri=other_client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(other_client)}"},
        status=200,
    )

    access_token = res.json["access_token"]
    token = Token.get(access_token=access_token)
    assert token.client == other_client.dn
    assert token.subject == logged_user.dn
    assert set(token.scope[0].split(" ")) == {
        "openid",
        "profile",
    }

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, keypair[1])
    assert logged_user.uid[0] == claims["sub"]
    assert logged_user.cn[0] == claims["name"]

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert {
        "name": "John (johnny) Doe",
        "family_name": "Doe",
        "preferred_username": "Johnny",
        "sub": "user",
        "locale": "en",
    } == res.json

    for consent in consents:
        consent.delete()
