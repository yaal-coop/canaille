"""OpenID Connect Back-Channel Logout 1.0.

When a session ends, the clients that got tokens in this session receive a
logout token at their ``backchannel_logout_uri``, and the tokens of the
session are revoked.
"""

import datetime

import httpx2
from authlib.oidc.backchannel import BackchannelLogoutSender
from blinker import signal
from flask import current_app
from flask import has_request_context

from canaille.app import models
from canaille.app.flask import dramatiq
from canaille.app.http import http
from canaille.backends import Backend
from canaille.oidc.provider import _get_signing_key
from canaille.oidc.provider import get_issuer
from canaille.oidc.userinfo import generate_user_claims

LOGOUT_TOKEN_DELIVERY_TIMEOUT = 5


class LogoutSender(BackchannelLogoutSender):
    """Send the logout tokens to the clients.

    ``sub`` is the identifier of the user in Canaille.
    The clients of a session are found with the ``sid`` of their tokens.
    """

    def get_issuer(self):
        return get_issuer()

    def resolve_client_private_key(self, client):
        key, _ = _get_signing_key(client)
        return key

    def get_client_algorithm(self, client):
        _, alg = _get_signing_key(client)
        return alg

    def get_client_sub(self, client, sub):
        user = Backend.instance.get(models.User, sub)
        return generate_user_claims(user).get("sub") if user else None

    def get_logout_sessions(self, sub, sid):
        """Return the clients of a session, or the sessions of a user that did not end.

        The tokens of the sessions that ended are revoked.
        """
        if sid:
            tokens = Backend.instance.query(models.Token, sid=sid)
        else:
            user = Backend.instance.get(models.User, sub)
            tokens = [
                token
                for token in Backend.instance.query(models.Token, subject=user)
                if not token.revoked
            ]

        return list(dict.fromkeys((token.client, token.sid) for token in tokens))

    def deliver_logout_tokens(self, deliveries):
        for client, uri, logout_token in deliveries:
            send_logout_token.send(client.client_id, uri, logout_token)


logout_sender = LogoutSender()


@dramatiq.actor
def send_logout_token(client_id, uri, logout_token):
    """Send a logout token to the back-channel logout URI of a client."""
    try:
        response = http().untrusted_client.post(
            uri,
            data={"logout_token": logout_token},
            timeout=LOGOUT_TOKEN_DELIVERY_TIMEOUT,
        )
        response.raise_for_status()
    except httpx2.HTTPError as exc:
        current_app.logger.warning(
            "Back-channel logout failed for client %s at %s: %s", client_id, uri, exc
        )


def send_logout(user, sid=None):
    """Notify the clients of a session, or of all the sessions of a user."""
    if not current_app.features.has_oidc:
        return

    # The issuer cannot be built outside of a request without SERVER_NAME.
    if not has_request_context() and not current_app.config.get("SERVER_NAME"):
        current_app.logger.warning(
            "Back-channel logout skipped for user %s, as SERVER_NAME is not set",
            user.user_name,
        )
        return

    try:
        logout_sender.send_logout(sub=user.id, sid=sid)
    except Exception:
        current_app.logger.exception(
            "Back-channel logout failed for user %s", user.user_name
        )


def was_locked(user):
    """Whether the user was locked before the changes that are being saved."""
    lock_date = Backend.instance.get_persisted_value(user, "lock_date")
    return bool(lock_date) and lock_date < datetime.datetime.now(datetime.UTC)


def end_session(sid):
    """Revoke the tokens and delete the codes of a session that ended.

    Per Back-Channel Logout §2.7, the refresh tokens of the session
    should not be usable anymore.
    """
    now = datetime.datetime.now(datetime.UTC)
    for token in Backend.instance.query(models.Token, sid=sid):
        if not token.revoked:
            token.revokation_date = now
            Backend.instance.save(token)

    for code in Backend.instance.query(models.AuthorizationCode, sid=sid):
        Backend.instance.delete(code)


def on_user_logged_out(sender, user, user_session):
    if not current_app.features.has_oidc:
        return

    end_session(user_session.sid)
    send_logout(user, user_session.sid)


def before_user_save(user, data):
    data["locking"] = user.locked and not was_locked(user)


def after_user_save(user, data):
    if data.get("locking"):
        send_logout(user)


def before_user_delete(user, data):
    send_logout(user)


def setup_backchannel_signals():
    teardown_backchannel_signals()
    signal("user_logged_out").connect(on_user_logged_out)
    signal("before_user_save").connect(before_user_save)
    signal("after_user_save").connect(after_user_save)
    signal("before_user_delete").connect(before_user_delete)


def teardown_backchannel_signals():
    signal("user_logged_out").disconnect(on_user_logged_out)
    signal("before_user_save").disconnect(before_user_save)
    signal("after_user_save").disconnect(after_user_save)
    signal("before_user_delete").disconnect(before_user_delete)
