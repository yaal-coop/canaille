import datetime
import logging
from urllib.parse import parse_qs
from urllib.parse import urlsplit

import time_machine
from authlib.jose import jwt
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from flask import g
from werkzeug.security import gen_salt

from canaille.app import models
from canaille.core.models import PASSWORD_MIN_DELAY

from . import client_credentials


def test_nominal_case(
    testclient, logged_user, client, keypair, trusted_client, backend, caplog
):
    assert not backend.query(models.Consent)

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
    assert (
        "canaille",
        logging.SECURITY,
        "New consent for user in client Some client from unknown IP",
    ) in caplog.record_tuples

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert authcode is not None
    assert set(authcode.scope) == {
        "openid",
        "profile",
        "email",
        "groups",
        "address",
        "phone",
    }

    consents = backend.query(models.Consent, client=client, subject=logged_user)
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
    token = backend.get(models.Token, access_token=access_token)
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
    assert claims["aud"] == [client.client_id, trusted_client.client_id]

    id_token = res.json["id_token"]
    claims = jwt.decode(id_token, keypair[1])
    assert claims["sub"] == logged_user.user_name
    assert claims["name"] == logged_user.formatted_name
    assert claims["aud"] == [client.client_id, trusted_client.client_id]
    assert (
        "canaille",
        logging.SECURITY,
        "Issued authorization_code token for user in client Some client from unknown IP",
    ) in caplog.record_tuples
    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"

    for consent in consents:
        backend.delete(consent)


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


def test_redirect_uri(
    testclient, logged_user, client, keypair, trusted_client, backend
):
    assert not backend.query(models.Consent)

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
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert authcode is not None
    consents = backend.query(models.Consent, client=client, subject=logged_user)

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
    token = backend.get(models.Token, access_token=access_token)
    assert token.client == client
    assert token.subject == logged_user

    for consent in consents:
        backend.delete(consent)


def test_preconsented_client(
    testclient, logged_user, client, keypair, trusted_client, backend
):
    assert not backend.query(models.Consent)

    client.preconsent = True
    backend.save(client)

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
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert authcode is not None

    consents = backend.query(models.Consent, client=client, subject=logged_user)
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
    token = backend.get(models.Token, access_token=access_token)
    assert token.client == client
    assert token.subject == logged_user

    id_token = res.json["id_token"]
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


def test_logout_login(testclient, logged_user, client, backend):
    assert not backend.query(models.Consent)

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
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert authcode is not None

    consents = backend.query(models.Consent, client=client, subject=logged_user)
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
    token = backend.get(models.Token, access_token=access_token)
    assert token.client == client
    assert token.subject == logged_user

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"

    for consent in consents:
        backend.delete(consent)


def test_deny(testclient, logged_user, client, backend):
    assert not backend.query(models.Consent)

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

    assert not backend.query(models.Consent)


def test_code_challenge(testclient, logged_user, client, backend):
    assert not backend.query(models.Consent)

    client.token_endpoint_auth_method = "none"
    backend.save(client)

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
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert authcode is not None

    consents = backend.query(models.Consent, client=client, subject=logged_user)
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

    token = backend.get(models.Token, access_token=access_token)
    assert token.client == client
    assert token.subject == logged_user

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"

    client.token_endpoint_auth_method = "client_secret_basic"
    backend.save(client)

    for consent in consents:
        backend.delete(consent)


def test_consent_already_given(testclient, logged_user, client, backend):
    assert not backend.query(models.Consent)

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
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert authcode is not None

    consents = backend.query(models.Consent, client=client, subject=logged_user)
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
        backend.delete(consent)


def test_when_consent_already_given_but_for_a_smaller_scope(
    testclient, logged_user, client, backend
):
    assert not backend.query(models.Consent)

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
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert authcode is not None

    consents = backend.query(models.Consent, client=client, subject=logged_user)
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
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert authcode is not None

    consents = backend.query(models.Consent, client=client, subject=logged_user)
    assert "profile" in consents[0].scope
    assert "groups" in consents[0].scope

    for consent in consents:
        backend.delete(consent)


def test_user_cannot_use_oidc(
    testclient, user, client, keypair, trusted_client, backend
):
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    backend.reload(user)

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
    res = res.follow(status=403)


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


def test_nonce_not_required_in_oauth_requests(testclient, logged_user, client, backend):
    assert not backend.query(models.Consent)
    testclient.app.config["CANAILLE_OIDC"]["REQUIRE_NONCE"] = False

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
    for consent in backend.query(models.Consent):
        backend.delete(consent)


def test_request_scope_too_large(testclient, logged_user, keypair, client, backend):
    assert not backend.query(models.Consent)
    client.scope = ["openid", "profile", "groups"]
    backend.save(client)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile email",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert set(authcode.scope) == {
        "openid",
        "profile",
    }

    consents = backend.query(models.Consent, client=client, subject=logged_user)
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
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    access_token = res.json["access_token"]
    token = backend.get(models.Token, access_token=access_token)
    assert token.client == client
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
        backend.delete(consent)


def test_code_expired(testclient, user, client):
    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False):
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

    with time_machine.travel("2021-01-01 01:00:00+00:00", tick=False):
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


def test_code_with_invalid_user(testclient, admin, client, backend):
    user = models.User(
        formatted_name="John Doe",
        family_name="Doe",
        user_name="temp",
        emails=["temp@temp.test"],
        password="correct horse battery staple",
    )
    backend.save(user)

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
    authcode = backend.get(models.AuthorizationCode, code=code)

    backend.delete(user)

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
    backend.delete(authcode)


def test_locked_account(
    testclient, logged_user, client, keypair, trusted_client, backend
):
    """Users with a locked account should not be able to exchange code against
    tokens."""
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

    logged_user.lock_date = datetime.datetime.now(datetime.timezone.utc)
    backend.save(logged_user)

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert authcode is not None

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

    assert "access_token" not in res.json


def test_missing_client_id(
    testclient, logged_user, client, keypair, trusted_client, backend
):
    """Missing client_id should raise a 400 error."""

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            scope="openid profile email groups address phone",
            nonce="somenonce",
        ),
        status=400,
    )
    res.mustcontain("client_id parameter is missing.")


def test_logout_login_with_intruder_lockout(testclient, logged_user, client, backend):
    testclient.app.config["CANAILLE"]["ENABLE_INTRUDER_LOCKOUT"] = True

    # add 500 milliseconds to account for LDAP time
    with time_machine.travel(
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(milliseconds=500),
        tick=False,
    ) as traveller:
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
        res = res.form.submit(status=200)

        assert (
            "error",
            f"Too much attempts. Please wait for {PASSWORD_MIN_DELAY} seconds before trying to login again.",
        ) in res.flashes

        traveller.shift(datetime.timedelta(seconds=PASSWORD_MIN_DELAY))

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(status=302)
        res = res.follow(status=200)

        res = res.form.submit(name="answer", value="accept", status=302)

        assert res.location.startswith(client.redirect_uris[0])
