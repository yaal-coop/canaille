import datetime
import uuid
from urllib.parse import parse_qs
from urllib.parse import urlsplit

import pytest
import time_machine
from joserfc import jwt

from canaille.app import models
from canaille.oidc.jose import registry

from . import client_credentials


def test_nominal_case(testclient, user, client, trusted_client, backend):
    """Test that authentication succeeds when the max_age requirement is met."""
    max_age = int(datetime.timedelta(hours=3).total_seconds())

    with time_machine.travel("2025-01-01 02:30:00+00:00", tick=False):
        res = testclient.get("/login")

        res.form["login"] = "user"
        res = res.form.submit(name="answer", value="accept", status=302).follow()

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(name="answer", value="accept", status=302).follow()

    with time_machine.travel("2025-01-01 03:00:00+00:00", tick=False):
        res = testclient.get(
            "/oauth/authorize",
            params=dict(
                response_type="code",
                client_id=client.client_id,
                scope="openid",
                nonce="somenonce",
                redirect_uri="https://client.test/redirect1",
                max_age=max_age,
            ),
        )
        res = res.form.submit(name="answer", value="accept", status=303)

    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]

    with time_machine.travel("2025-01-01 03:01:00+00:00", tick=False):
        res = testclient.post(
            "/oauth/token",
            params=dict(
                grant_type="authorization_code",
                code=code,
                scope="openid",
                redirect_uri=client.redirect_uris[0],
            ),
            headers={"Authorization": f"Basic {client_credentials(client)}"},
        )

    for consent in backend.query(models.Consent, client=client, subject=user):
        backend.delete(consent)


def test_max_age_expired(testclient, user, client, trusted_client, backend):
    """Test that re-authentication is required when the max_age requirement has expired."""
    max_age = int(datetime.timedelta(minutes=15).total_seconds())

    with time_machine.travel("2025-01-01 02:30:00+00:00", tick=False):
        res = testclient.get("/login")

        res.form["login"] = "user"
        res = res.form.submit(name="answer", value="accept", status=302).follow()

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(name="answer", value="accept", status=302).follow()

    with time_machine.travel("2025-01-01 03:00:00+00:00", tick=False):
        res = testclient.get(
            "/oauth/authorize",
            params=dict(
                response_type="code",
                client_id=client.client_id,
                scope="openid",
                nonce="somenonce",
                redirect_uri="https://client.test/redirect1",
                max_age=max_age,
            ),
        ).follow()

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(name="answer", value="accept", status=302).follow()

        res = res.form.submit(name="answer", value="accept", status=303)

    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]

    with time_machine.travel("2025-01-01 03:01:00+00:00", tick=False):
        res = testclient.post(
            "/oauth/token",
            params=dict(
                grant_type="authorization_code",
                code=code,
                scope="openid",
                redirect_uri=client.redirect_uris[0],
            ),
            headers={"Authorization": f"Basic {client_credentials(client)}"},
        )

    for consent in backend.query(models.Consent, client=client, subject=user):
        backend.delete(consent)


def test_invalid_max_age(testclient, logged_user, client):
    """A max_age that is not a positive integer is refused."""
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
            max_age="-1",
        ),
        status=303,
    )
    assert res.location.startswith(client.redirect_uris[0])
    assert parse_qs(urlsplit(res.location).query)["error"] == ["invalid_request"]

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
            max_age="invalid",
        ),
        status=303,
    )
    assert res.location.startswith(client.redirect_uris[0])
    assert parse_qs(urlsplit(res.location).query)["error"] == ["invalid_request"]


def test_max_age_zero(testclient, user, client, backend):
    """A max_age of zero asks to log in once, and not again after the login."""
    with time_machine.travel("2025-01-01 02:30:00+00:00", tick=False):
        res = testclient.get("/login")
        res.form["login"] = "user"
        res = res.form.submit(name="answer", value="accept", status=302).follow()
        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(name="answer", value="accept", status=302).follow()

    with time_machine.travel("2025-01-01 03:00:00+00:00", tick=False):
        res = testclient.get(
            "/oauth/authorize",
            params=dict(
                response_type="code",
                client_id=client.client_id,
                scope="openid",
                nonce="somenonce",
                redirect_uri="https://client.test/redirect1",
                max_age=0,
            ),
        ).follow()

    with time_machine.travel("2025-01-01 03:00:05+00:00", tick=False):
        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(name="answer", value="accept", status=302)

    with time_machine.travel("2025-01-01 03:00:10+00:00", tick=False):
        res = res.follow(status=200)
        res.mustcontain('id="accept"')


def test_prompt_login_after_a_finished_request(
    testclient, logged_user, client, backend
):
    """A finished authorization request sent again asks for a new login."""
    consent = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=logged_user,
        scope=["openid"],
    )
    backend.save(consent)
    params = dict(
        response_type="code",
        client_id=client.client_id,
        scope="openid",
        nonce="somenonce",
        redirect_uri="https://client.test/redirect1",
        prompt="login",
    )

    res = testclient.get("/oauth/authorize", params=params, status=302).follow()
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302).follow(status=303)
    code = parse_qs(urlsplit(res.location).query)["code"][0]

    # The client exchanges the code, so the nonce can be sent again.
    backend.delete(backend.get(models.AuthorizationCode, code=code))

    later = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=1)
    with time_machine.travel(later, tick=False):
        res = testclient.get("/oauth/authorize", params=params, status=302).follow()
        assert res.template == "core/auth/password.html"

    backend.delete(consent)


@pytest.mark.parametrize("response_type", ["id_token token", "code id_token"])
def test_auth_time_in_front_channel_id_token(
    testclient, user, client, server_jwk, backend, response_type
):
    """ID tokens sent by the authorization endpoint hold the time of the login."""
    client.token_endpoint_auth_method = "none"
    backend.save(client)

    with time_machine.travel("2025-01-01 02:30:00+00:00", tick=False):
        res = testclient.get("/login")

        res.form["login"] = "user"
        res = res.form.submit(name="answer", value="accept", status=302).follow()

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(name="answer", value="accept", status=302).follow()

    with time_machine.travel("2025-01-01 03:00:00+00:00", tick=False):
        res = testclient.get(
            "/oauth/authorize",
            params=dict(
                response_type=response_type,
                client_id=client.client_id,
                scope="openid",
                nonce="somenonce",
                redirect_uri="https://client.test/redirect1",
            ),
        )
        res = res.form.submit(name="answer", value="accept", status=303)

    params = parse_qs(urlsplit(res.location).fragment)
    claims = jwt.decode(params["id_token"][0], server_jwk, registry=registry).claims
    login_time = datetime.datetime(2025, 1, 1, 2, 30, tzinfo=datetime.UTC)
    assert claims["auth_time"] == login_time.timestamp()

    for consent in backend.query(models.Consent, client=client, subject=user):
        backend.delete(consent)

    client.token_endpoint_auth_method = "client_secret_basic"
    backend.save(client)


def test_max_age_without_openid_scope(testclient, logged_user, client):
    """Per RFC 9470 §4, max_age also applies to OAuth requests without openid."""
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="profile",
            redirect_uri="https://client.test/redirect1",
            max_age=0,
        ),
        status=302,
    ).follow()
    assert res.template == "core/auth/password.html"
