from urllib.parse import parse_qs
from urllib.parse import urlsplit

import time_machine

from canaille.app import models
from canaille.oidc.provider import AuthorizationSession

AUTHORIZATION_REQUEST_TIMES = AuthorizationSession.session_key


def test_silent_request_does_not_write_the_session(
    testclient, logged_user, client, consent
):
    """A request with prompt=none does not send the session cookie again."""
    # Logged users got a CSRF token with the login form.
    with testclient.session_transaction() as sess:
        sess["csrf_token"] = "token"

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            redirect_uri=client.redirect_uris[0],
            prompt="none",
        ),
        status=303,
    )
    assert "code" in parse_qs(urlsplit(res.location).query)
    assert "Set-Cookie" not in res.headers


def test_login_during_the_request_is_fresh(testclient, user, client, backend):
    """A login made during a request with prompt=login is not asked again."""
    params = dict(
        response_type="code",
        client_id=client.client_id,
        scope="openid",
        nonce="somenonce",
        redirect_uri=client.redirect_uris[0],
        prompt="login",
    )
    with time_machine.travel("2025-01-01 03:00:00+00:00", tick=False):
        res = testclient.get("/oauth/authorize", params=params, status=302).follow()
        res.form["login"] = "user"
        res = res.form.submit(name="answer", value="accept", status=302).follow()

    with time_machine.travel("2025-01-01 03:00:10+00:00", tick=False):
        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(name="answer", value="accept", status=302)

    with time_machine.travel("2025-01-01 03:00:20+00:00", tick=False):
        res = res.follow(status=200)
        assert res.template == "oidc/authorize.html"

    for consent in backend.query(models.Consent, client=client, subject=user):
        backend.delete(consent)


def test_failed_request_ends(testclient, client):
    """A request that ends with an error does not keep its start time."""
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid",
            nonce="somenonce",
            redirect_uri=client.redirect_uris[0],
            prompt="none",
        ),
        status=303,
    )
    assert parse_qs(urlsplit(res.location).query)["error"] == ["login_required"]
    with testclient.session_transaction() as sess:
        assert not sess.get(AUTHORIZATION_REQUEST_TIMES)


def test_session_without_login_time(testclient, user, client, backend):
    """Sessions without a login time can still be used, and must select an account again."""
    with testclient.session_transaction() as sess:
        sess["sessions"] = [{"user": user.id}]

    params = dict(
        response_type="code",
        client_id=client.client_id,
        scope="openid",
        nonce="somenonce",
        redirect_uri=client.redirect_uris[0],
    )
    res = testclient.get("/oauth/authorize", params=params, status=200)
    res = res.form.submit(name="answer", value="accept", status=303)
    code = parse_qs(urlsplit(res.location).query)["code"][0]
    authorization_code = backend.get(models.AuthorizationCode, code=code)
    assert authorization_code.auth_time is None

    res = testclient.get(
        "/oauth/authorize",
        params=dict(params, nonce="othernonce", prompt="select_account"),
        status=302,
    ).follow()
    assert res.template == "core/login.html"

    res = testclient.get(f"/login/{user.user_name}", status=302).follow(status=303)
    assert "code" in parse_qs(urlsplit(res.location).query)

    for consent in backend.query(models.Consent, client=client, subject=user):
        backend.delete(consent)


def test_aborted_request_ends(testclient, logged_user, client):
    """A request that ends with an HTTP error does not keep its start time."""
    params = dict(
        response_type="code",
        client_id=client.client_id,
        scope="openid",
        nonce="somenonce",
        redirect_uri=client.redirect_uris[0],
    )
    res = testclient.get("/oauth/authorize", params=params, status=200)
    with testclient.session_transaction() as sess:
        assert sess.get(AUTHORIZATION_REQUEST_TIMES)

    testclient.post(
        res.request.url,
        params=dict(answer="unknown", csrf_token=res.form["csrf_token"].value),
        status=400,
    )
    with testclient.session_transaction() as sess:
        assert not sess.get(AUTHORIZATION_REQUEST_TIMES)


def test_untracked_interaction_has_no_time(testclient, logged_user, client):
    """Canaille gives no time for the interactions it does not track."""
    with testclient.app.test_request_context():
        authorization_session = AuthorizationSession(logged_user, {})
        assert authorization_session.get_interaction_time(None, "create") is None
