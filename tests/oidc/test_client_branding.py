"""Tests for OIDC client branding during authentication flow."""

import uuid

from canaille.app import models


def test_standard_login_displays_generic_branding(testclient, user):
    """Verify standard login page displays generic site branding without client-specific elements."""
    with testclient.session_transaction() as sess:
        sess.clear()

    res = testclient.get("/login")

    assert "Privacy policy" not in res.text
    assert "Terms of service" not in res.text
    assert "Sign in at Canaille" in res.text
    assert "Sign in to " not in res.text


def test_client_branding_elements_display(testclient, user, client, backend):
    """Verify all client branding elements (logo, name, legal links) appear in authentication interface."""
    with testclient.session_transaction() as sess:
        sess.clear()

    client.client_name = "My Cool App"
    client.logo_uri = "https://example.com/logo.png"
    client.client_uri = "https://example.com"
    client.policy_uri = "https://example.com/privacy"
    client.tos_uri = "https://example.com/terms"
    backend.save(client)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
        status=302,
    )

    res = res.follow()

    assert "My Cool App" in res.text
    assert "Sign in to My Cool App" in res.text
    assert client.logo_uri in res.text
    assert "Privacy policy" in res.text
    assert "Terms of service" in res.text


def test_reauthentication_prompt_displays_contextual_messaging(
    testclient, logged_user, client, backend
):
    """Verify prompt=login parameter triggers re-authentication with appropriate user messaging."""
    client.client_name = "Test Client"
    backend.save(client)

    consent = models.Consent(
        consent_id=str(uuid.uuid4()),
        client=client,
        subject=logged_user,
        scope=["openid", "profile"],
    )
    backend.save(consent)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            prompt="login",
            redirect_uri="https://client.test/redirect1",
        ),
        status=302,
    )

    res = res.follow()

    assert "Re-authenticate for Test Client" in res.text
    assert "You are already logged in" in res.text
    assert "is requesting identity confirmation" in res.text

    backend.delete(consent)


def test_password_step_maintains_client_branding(testclient, user, client, backend):
    """Verify client branding persists throughout password authentication step."""
    with testclient.session_transaction() as sess:
        sess.clear()

    client.client_name = "My Test App"
    client.logo_uri = "https://example.com/logo.png"
    backend.save(client)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
        status=302,
    )

    res = res.follow()
    res.form["login"] = user.user_name
    res = res.form.submit(status=302).follow()

    assert res.template == "core/auth/password.html"
    assert "My Test App" in res.text
    assert "Sign in to My Test App" in res.text
    assert client.logo_uri in res.text
