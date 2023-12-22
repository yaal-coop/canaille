"""
Tests the behavior of Canaille depending on the OIDC 'prompt' parameter.
https://openid.net/specs/openid-connect-core-1_0.html#AuthorizationEndpoint
"""
import uuid
from urllib.parse import parse_qs
from urllib.parse import urlsplit

from canaille.app import models


def test_prompt_none(testclient, logged_user, client):
    """
    Nominal case with prompt=none
    """
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
    """
    prompt=none should return a login_required error when no
    user is logged in.

    login_required
        The Authorization Server requires End-User authentication.
        This error MAY be returned when the prompt parameter value in the
        Authentication Request is none, but the Authentication Request
        cannot be completed without displaying a user interface for End-User
        authentication.
    """
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
    """
    prompt=none should return a consent_required error when user
    are logged in but have not granted their consent.

    consent_required
    The Authorization Server requires End-User consent. This error MAY be
    returned when the prompt parameter value in the Authentication Request
    is none, but the Authentication Request cannot be completed without
    displaying a user interface for End-User consent.
    """
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
