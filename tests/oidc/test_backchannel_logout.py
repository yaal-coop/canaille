import datetime
import logging
from types import SimpleNamespace
from urllib.parse import parse_qs
from urllib.parse import urlsplit

import httpx2
import pytest
from flask import Flask
from flask import g
from flask import request
from joserfc import jwt

from canaille.app import models
from canaille.app.http import http
from canaille.app.session import login_user
from canaille.oidc.backchannel import LogoutSender
from canaille.oidc.jose import registry

from . import client_credentials

BACKCHANNEL_LOGOUT_EVENT = "http://schemas.openid.net/event/backchannel-logout"


@pytest.fixture
def client_app():
    """Serve the client application, that records the logout tokens it receives."""
    state = SimpleNamespace(logout_tokens=[], status=200)
    client_app = Flask("client")

    @client_app.route("/backchannel-logout", methods=["POST"])
    def backchannel_logout():
        state.logout_tokens.append(request.form["logout_token"])
        return "", state.status

    http().mount("https://client.test", httpx2.WSGITransport(app=client_app))
    yield state
    http().unmount("https://client.test")


@pytest.fixture
def logout_tokens(client_app, client, backend):
    client.backchannel_logout_uri = "https://client.test/backchannel-logout"
    backend.save(client)
    return client_app.logout_tokens


def decode(token, server_jwk):
    return jwt.decode(token, server_jwk, registry=registry).claims


def authorize(testclient, client, response_type="code"):
    """Return the parameters of the authorization response."""
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type=response_type,
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
    )
    if res.status_code == 200:
        res = res.form.submit(name="answer", value="accept", status=303)

    url = urlsplit(res.location)
    return parse_qs(url.fragment or url.query)


def get_tokens(testclient, client):
    """Run the authorization code flow and return the token response."""
    code = authorize(testclient, client)["code"][0]
    return testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    ).json


def test_logout(testclient, logged_user, client, server_jwk, logout_tokens):
    """Per Back-Channel Logout §2.4, logging out sends a logout token to the client."""
    id_token = decode(get_tokens(testclient, client)["id_token"], server_jwk)
    assert id_token["sid"]

    testclient.get("/logout")

    assert len(logout_tokens) == 1
    claims = decode(logout_tokens[0], server_jwk)
    assert claims["iss"] == "http://canaille.test"
    assert claims["aud"] in (client.client_id, [client.client_id])
    assert claims["sub"] == logged_user.user_name
    assert claims["sid"] == id_token["sid"]
    assert BACKCHANNEL_LOGOUT_EVENT in claims["events"]
    assert "nonce" not in claims


def test_logout_without_backchannel_logout_uri(
    testclient, logged_user, client, client_app
):
    """Clients without back-channel logout URI are not notified."""
    get_tokens(testclient, client)

    testclient.get("/logout")

    assert not client_app.logout_tokens


@pytest.mark.parametrize("response_type", ["id_token", "code id_token"])
def test_implicit_and_hybrid_sid(
    testclient, logged_user, client, server_jwk, response_type
):
    """The ID tokens of the authorization endpoint have the sid of the session."""
    id_token = decode(get_tokens(testclient, client)["id_token"], server_jwk)

    params = authorize(testclient, client, response_type)
    claims = decode(params["id_token"][0], server_jwk)

    assert claims["sid"] == id_token["sid"]


def test_refresh_token_keeps_the_sid(testclient, logged_user, client, backend):
    """A token issued with a refresh token belongs to the same session."""
    tokens = get_tokens(testclient, client)
    sid = backend.get(models.Token, access_token=tokens["access_token"]).sid

    res = testclient.post(
        "/oauth/token",
        params=dict(grant_type="refresh_token", refresh_token=tokens["refresh_token"]),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    )

    assert backend.get(models.Token, access_token=res.json["access_token"]).sid == sid


def test_user_lock(testclient, logged_user, client, server_jwk, logout_tokens, backend):
    """Locking a user sends a logout token for each session."""
    id_token = decode(get_tokens(testclient, client)["id_token"], server_jwk)

    logged_user.lock_date = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
        seconds=1
    )
    backend.save(logged_user)

    assert len(logout_tokens) == 1
    claims = decode(logout_tokens[0], server_jwk)
    assert claims["sub"] == logged_user.user_name
    assert claims["sid"] == id_token["sid"]

    backend.save(logged_user)
    assert len(logout_tokens) == 1


def test_user_deletion(testclient, client, server_jwk, logout_tokens, backend):
    """Deleting a user sends a logout token for each session."""
    user = models.User(
        user_name="temp-user",
        formatted_name="Temp User",
        family_name="User",
        emails=["temp@user.test"],
    )
    backend.save(user)
    token = models.Token(
        token_id="token-id",
        access_token="access-token",
        client=client,
        subject=user,
        type="access_token",
        issue_date=datetime.datetime.now(datetime.UTC),
        lifetime=3600,
        sid="session-id",
    )
    backend.save(token)

    backend.delete(user)

    assert len(logout_tokens) == 1
    claims = decode(logout_tokens[0], server_jwk)
    assert claims["sub"] == "temp-user"
    assert claims["sid"] == "session-id"


@pytest.mark.parametrize("session_required", [True, False])
def test_session_required(
    testclient, client, user, server_jwk, logout_tokens, backend, session_required
):
    """Tokens without session are only notified to clients that do not require one."""
    client.backchannel_logout_session_required = session_required
    backend.save(client)
    token = models.Token(
        token_id="token-id",
        access_token="access-token",
        client=client,
        subject=user,
        type="access_token",
        issue_date=datetime.datetime.now(datetime.UTC),
        lifetime=3600,
    )
    backend.save(token)

    user.lock_date = datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=1)
    backend.save(user)

    if session_required:
        assert not logout_tokens
        return

    assert len(logout_tokens) == 1
    claims = decode(logout_tokens[0], server_jwk)
    assert claims["sub"] == user.user_name
    assert "sid" not in claims


def test_delivery_failure(
    testclient, logged_user, client, client_app, logout_tokens, caplog
):
    """A failed delivery is logged."""
    get_tokens(testclient, client)
    client_app.status = 500

    testclient.get("/logout")

    assert len(logout_tokens) == 1
    assert any(
        record.name == "canaille"
        and record.levelno == logging.WARNING
        and record.getMessage().startswith(
            f"Back-channel logout failed for client {client.client_id}"
        )
        for record in caplog.records
    )


def test_login_again_keeps_the_sid(app, user):
    """A new login of the same user keeps the session."""
    with app.test_request_context():
        login_user(user)
        sid = g.session.sid
        login_user(user)
        assert g.session.sid == sid


def test_session_without_sid(testclient, user):
    """Sessions opened before the sid existed get one."""
    with testclient.session_transaction() as session:
        session["sessions"] = [{"user": user.id}]

    testclient.get(f"/profile/{user.user_name}", status=200)

    with testclient.session_transaction() as session:
        assert session["sessions"][0]["sid"]


def test_dynamic_client_registration(testclient, backend, monkeypatch):
    """Clients can register their back-channel logout URI."""
    monkeypatch.setitem(
        testclient.app.config["CANAILLE_OIDC"], "DYNAMIC_CLIENT_REGISTRATION_OPEN", True
    )
    payload = {
        "redirect_uris": ["https://client.test/callback"],
        "client_name": "Back-channel client",
        "backchannel_logout_uri": "https://client.test/backchannel-logout",
        "backchannel_logout_session_required": True,
    }

    res = testclient.post_json("/oauth/register", payload, status=201)

    assert res.json["backchannel_logout_uri"] == payload["backchannel_logout_uri"]
    client = backend.get(models.Client, client_id=res.json["client_id"])
    assert client.backchannel_logout_uri == payload["backchannel_logout_uri"]
    assert client.backchannel_logout_session_required is True
    backend.delete(client)


def test_dynamic_client_registration_with_fragment(testclient, backend, monkeypatch):
    """Per Back-Channel Logout §2.2, the back-channel logout URI has no fragment."""
    monkeypatch.setitem(
        testclient.app.config["CANAILLE_OIDC"], "DYNAMIC_CLIENT_REGISTRATION_OPEN", True
    )
    payload = {
        "redirect_uris": ["https://client.test/callback"],
        "client_name": "Back-channel client",
        "backchannel_logout_uri": "https://client.test/backchannel-logout#fragment",
    }

    res = testclient.post_json("/oauth/register", payload, status=400)

    assert res.json["error"] == "invalid_client_metadata"


def test_lock_ignores_revoked_tokens(
    testclient, client, user, server_jwk, logout_tokens, backend
):
    """Locking a user notifies the sessions that did not end, even with expired tokens."""
    now = datetime.datetime.now(datetime.UTC)
    for token_id, issue_date, revokation_date in [
        ("revoked", now, now),
        ("expired", now - datetime.timedelta(days=1), None),
    ]:
        backend.save(
            models.Token(
                token_id=token_id,
                access_token=token_id,
                client=client,
                subject=user,
                type="access_token",
                issue_date=issue_date,
                lifetime=3600,
                revokation_date=revokation_date,
                sid=token_id,
            )
        )

    user.lock_date = now - datetime.timedelta(seconds=1)
    backend.save(user)

    assert [decode(token, server_jwk)["sid"] for token in logout_tokens] == ["expired"]


def test_sending_failure(testclient, logged_user, client, backend, monkeypatch, caplog):
    """A failure to send the logout tokens does not prevent the logout."""
    tokens = get_tokens(testclient, client)

    def fail(*args, **kwargs):
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr(LogoutSender, "send_logout", fail)

    testclient.get("/logout", status=302)

    assert backend.get(models.Token, access_token=tokens["access_token"]).revoked
    assert any(
        record.getMessage()
        == f"Back-channel logout failed for user {logged_user.user_name}"
        for record in caplog.records
    )


def test_client_admin_backchannel_logout_uri_with_fragment(
    testclient, logged_admin, client
):
    """Per Back-Channel Logout §2.2, the back-channel logout URI has no fragment."""
    res = testclient.get("/admin/client/edit/" + client.client_id)
    res.forms["clienteditform"]["backchannel_logout_uri"] = (
        "https://client.test/logout#fragment"
    )
    res = res.forms["clienteditform"].submit(name="action", value="edit")

    res.mustcontain("This URL must not have a fragment")


def test_logout_revokes_the_session_tokens(testclient, logged_user, client, backend):
    """Per Back-Channel Logout §2.7, the tokens of the session are revoked at logout."""
    tokens = get_tokens(testclient, client)
    code = authorize(testclient, client)["code"][0]

    testclient.get("/logout")

    token = backend.get(models.Token, access_token=tokens["access_token"])
    assert token.revoked
    assert not backend.get(models.AuthorizationCode, code=code)

    res = testclient.post(
        "/oauth/token",
        params=dict(grant_type="refresh_token", refresh_token=tokens["refresh_token"]),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json["error"] == "invalid_grant"
