import uuid
from urllib.parse import parse_qs
from urllib.parse import urlsplit

import freezegun
from authlib.jose import jwt
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from canaille.app import models
from canaille.oidc.oauth import setup_oauth
from flask import g
from werkzeug.security import gen_salt

from . import client_credentials


def test_authorization_code_flow(
    testclient, logged_user, client, keypair, other_client
):
    assert not models.Consent.query()

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
    authcode = models.AuthorizationCode.get(code=code)
    assert authcode is not None
    assert set(authcode.scope) == {
        "openid",
        "profile",
        "email",
        "groups",
        "address",
        "phone",
    }

    consents = models.Consent.query(client=client, subject=logged_user)
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
    token = models.Token.get(access_token=access_token)
    assert token.client == client
    assert token.subject == logged_user
    assert set(token.scope) == {
        "openid",
        "profile",
        "email",
        "groups",
        "address",
        "phone",
    }
    claims = jwt.decode(access_token, keypair[1])
    assert claims["sub"] == logged_user.user_name
    assert claims["name"] == logged_user.formatted_name
    assert claims["aud"] == [client.client_id, other_client.client_id]

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, keypair[1])
    assert claims["sub"] == logged_user.user_name
    assert claims["name"] == logged_user.formatted_name
    assert claims["aud"] == [client.client_id, other_client.client_id]

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"

    for consent in consents:
        consent.delete()


def test_invalid_client(testclient, logged_user, keypair):
    testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id="invalid",
            scope="openid profile email groups address phone",
            nonce="somenonce",
        ),
        status=400,
    )


def test_authorization_code_flow_with_redirect_uri(
    testclient, logged_user, client, keypair, other_client
):
    assert not models.Consent.query()

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile email groups address phone",
            nonce="somenonce",
            redirect_uri=client.redirect_uris[1],
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[1])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = models.AuthorizationCode.get(code=code)
    assert authcode is not None
    consents = models.Consent.query(client=client, subject=logged_user)

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid profile email groups address phone",
            redirect_uri=client.redirect_uris[1],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    access_token = res.json["access_token"]
    token = models.Token.get(access_token=access_token)
    assert token.client == client
    assert token.subject == logged_user

    for consent in consents:
        consent.delete()


def test_authorization_code_flow_preconsented(
    testclient, logged_user, client, keypair, other_client
):
    assert not models.Consent.query()

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
    authcode = models.AuthorizationCode.get(code=code)
    assert authcode is not None

    consents = models.Consent.query(client=client, subject=logged_user)
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
    token = models.Token.get(access_token=access_token)
    assert token.client == client
    assert token.subject == logged_user

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, keypair[1])
    assert logged_user.user_name == claims["sub"]
    assert logged_user.formatted_name == claims["name"]
    assert [client.client_id, other_client.client_id] == claims["aud"]

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"


def test_logout_login(testclient, logged_user, client):
    assert not models.Consent.query()

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

    res = res.form.submit(name="answer", value="logout")
    res = res.follow()
    g.user = None
    res = res.follow()
    res = res.follow()

    res.form["login"] = logged_user.user_name
    res = res.form.submit()
    res = res.follow()

    res.form["password"] = "wrong password"
    res = res.form.submit(status=200)
    assert ("error", "Login failed, please check your information") in res.flashes

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = models.AuthorizationCode.get(code=code)
    assert authcode is not None

    consents = models.Consent.query(client=client, subject=logged_user)
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
    token = models.Token.get(access_token=access_token)
    assert token.client == client
    assert token.subject == logged_user

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"

    for consent in consents:
        consent.delete()


def test_deny(testclient, logged_user, client):
    assert not models.Consent.query()

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

    res = res.form.submit(name="answer", value="deny", status=302)
    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    error = params["error"][0]
    assert error == "access_denied"

    assert not models.Consent.query()


def test_refresh_token(testclient, user, client):
    assert not models.Consent.query()

    with freezegun.freeze_time("2020-01-01 01:00:00"):
        res = testclient.get(
            "/oauth/authorize",
            params=dict(
                response_type="code",
                client_id=client.client_id,
                scope="openid profile",
                nonce="somenonce",
            ),
        )
        res = res.follow()

        res.form["login"] = "user"
        res = res.form.submit(name="answer", value="accept")
        res = res.follow()
        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(name="answer", value="accept")
        res = res.follow()
        res = res.form.submit(name="answer", value="accept")

        assert res.location.startswith(client.redirect_uris[0])
        params = parse_qs(urlsplit(res.location).query)
        code = params["code"][0]
        authcode = models.AuthorizationCode.get(code=code)
        assert authcode is not None

        consents = models.Consent.query(client=client, subject=user)
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
        old_token = models.Token.get(access_token=access_token)
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
        new_token = models.Token.get(access_token=access_token)
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
        assert res.json["name"] == "John (johnny) Doe"

    for consent in consents:
        consent.delete()


def test_code_challenge(testclient, logged_user, client):
    assert not models.Consent.query()

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
    authcode = models.AuthorizationCode.get(code=code)
    assert authcode is not None

    consents = models.Consent.query(client=client, subject=logged_user)
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

    token = models.Token.get(access_token=access_token)
    assert token.client == client
    assert token.subject == logged_user

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"

    client.token_endpoint_auth_method = "client_secret_basic"
    client.save()

    for consent in consents:
        consent.delete()


def test_authorization_code_flow_when_consent_already_given(
    testclient, logged_user, client
):
    assert not models.Consent.query()

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
    authcode = models.AuthorizationCode.get(code=code)
    assert authcode is not None

    consents = models.Consent.query(client=client, subject=logged_user)
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
    assert not models.Consent.query()

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
    authcode = models.AuthorizationCode.get(code=code)
    assert authcode is not None

    consents = models.Consent.query(client=client, subject=logged_user)
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
    authcode = models.AuthorizationCode.get(code=code)
    assert authcode is not None

    consents = models.Consent.query(client=client, subject=logged_user)
    assert "profile" in consents[0].scope
    assert "groups" in consents[0].scope

    for consent in consents:
        consent.delete()


def test_authorization_code_flow_but_user_cannot_use_oidc(
    testclient, user, client, keypair, other_client
):
    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    user.reload()

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
        ),
    )
    res = res.follow()

    res.form["login"] = "user"
    res = res.form.submit()
    res = res.follow()

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)
    res = res.follow(status=400)


def test_prompt_none(testclient, logged_user, client):
    consent = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=logged_user,
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
    consent = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=user,
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
    assert not models.Consent.query()
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
    for consent in models.Consent.query():
        consent.delete()


def test_authorization_code_request_scope_too_large(
    testclient, logged_user, keypair, other_client
):
    assert not models.Consent.query()
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
    authcode = models.AuthorizationCode.get(code=code)
    assert set(authcode.scope) == {
        "openid",
        "profile",
    }

    consents = models.Consent.query(client=other_client, subject=logged_user)
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
    token = models.Token.get(access_token=access_token)
    assert token.client == other_client
    assert token.subject == logged_user
    assert set(token.scope) == {
        "openid",
        "profile",
    }

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, keypair[1])
    assert logged_user.user_name == claims["sub"]
    assert logged_user.formatted_name == claims["name"]

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"

    for consent in consents:
        consent.delete()


def test_authorization_code_expired(testclient, user, client):
    with freezegun.freeze_time("2020-01-01 01:00:00"):
        res = testclient.get(
            "/oauth/authorize",
            params=dict(
                response_type="code",
                client_id=client.client_id,
                scope="openid profile email groups address phone",
                nonce="somenonce",
            ),
        )
        res = res.follow()

        res.form["login"] = "user"
        res = res.form.submit(name="answer", value="accept").follow()

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(name="answer", value="accept").follow()
        res = res.form.submit(name="answer", value="accept", status=302)
        params = parse_qs(urlsplit(res.location).query)
        code = params["code"][0]

    with freezegun.freeze_time("2021-01-01 01:00:00"):
        res = testclient.post(
            "/oauth/token",
            params=dict(
                grant_type="authorization_code",
                code=code,
                scope="openid profile email groups address phone",
                redirect_uri=client.redirect_uris[0],
            ),
            headers={"Authorization": f"Basic {client_credentials(client)}"},
            status=400,
        )
        assert res.json == {
            "error": "invalid_grant",
            "error_description": 'Invalid "code" in request.',
        }


def test_code_with_invalid_user(testclient, admin, client):
    user = models.User(
        formatted_name="John Doe",
        family_name="Doe",
        user_name="temp",
        emails=["temp@temp.com"],
        password="correct horse battery staple",
    )
    user.save()

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile email groups address phone",
            nonce="somenonce",
        ),
    ).follow()

    res.form["login"] = "temp"
    res = res.form.submit(name="answer", value="accept", status=302).follow()

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(name="answer", value="accept", status=302).follow()
    res = res.form.submit(name="answer", value="accept", status=302)
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = models.AuthorizationCode.get(code=code)

    user.delete()

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid profile email groups address phone",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json == {
        "error": "invalid_grant",
        "error_description": 'There is no "user" for this code.',
    }
    authcode.delete()


def test_refresh_token_with_invalid_user(testclient, client):
    user = models.User(
        formatted_name="John Doe",
        family_name="Doe",
        user_name="temp",
        emails=["temp@temp.com"],
        password="correct horse battery staple",
    )
    user.save()

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
        ),
    ).follow()

    res.form["login"] = "temp"
    res = res.form.submit(name="answer", value="accept", status=302).follow()

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(name="answer", value="accept", status=302).follow()
    res = res.form.submit(name="answer", value="accept", status=302)

    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    models.AuthorizationCode.get(code=code)

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

    refresh_token = res.json["refresh_token"]
    access_token = res.json["access_token"]
    user.delete()

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="refresh_token",
            refresh_token=refresh_token,
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json == {
        "error": "invalid_request",
        "error_description": 'There is no "user" for this token.',
    }
    models.Token.get(access_token=access_token).delete()


def test_token_default_expiration_date(testclient, logged_user, client, keypair):
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
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = models.AuthorizationCode.get(code=code)
    assert authcode.lifetime == 84400

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

    assert res.json["expires_in"] == 864000

    access_token = res.json["access_token"]
    token = models.Token.get(access_token=access_token)
    assert token.lifetime == 864000

    claims = jwt.decode(access_token, keypair[1])
    assert claims["exp"] - claims["iat"] == 864000

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, keypair[1])
    assert claims["exp"] - claims["iat"] == 3600

    consents = models.Consent.query(client=client, subject=logged_user)
    for consent in consents:
        consent.delete()


def test_token_custom_expiration_date(testclient, logged_user, client, keypair):
    testclient.app.config["OAUTH2_TOKEN_EXPIRES_IN"] = {
        "authorization_code": 1000,
        "implicit": 2000,
        "password": 3000,
        "client_credentials": 4000,
        "urn:ietf:params:oauth:grant-type:jwt-bearer": 5000,
    }
    testclient.app.config["OIDC"]["JWT"]["EXP"] = 6000
    setup_oauth(testclient.app)

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
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = models.AuthorizationCode.get(code=code)
    assert authcode.lifetime == 84400

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

    assert res.json["expires_in"] == 1000

    access_token = res.json["access_token"]
    token = models.Token.get(access_token=access_token)
    assert token.lifetime == 1000

    claims = jwt.decode(access_token, keypair[1])
    assert claims["exp"] - claims["iat"] == 1000

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, keypair[1])
    assert claims["exp"] - claims["iat"] == 6000

    consents = models.Consent.query(client=client, subject=logged_user)
    for consent in consents:
        consent.delete()
