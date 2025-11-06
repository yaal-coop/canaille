"""Tests the behavior of Canaille with the OIDC 'ui_locales' parameter.

https://openid.net/specs/openid-connect-core-1_0.html#AuthRequest
"""


def test_ui_locales_exact_match(testclient, logged_user, client):
    """Test that ui_locales parameter sets the correct locale with exact match."""
    res = testclient.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client.client_id,
            "scope": "openid",
            "nonce": "somenonce",
            "redirect_uri": "https://client.test/redirect1",
            "ui_locales": "fr",
        },
        status=200,
    )

    res.mustcontain('<html lang="fr">')


def test_ui_locales_with_fallback(testclient, logged_user, client):
    """Test that ui_locales falls back to base language when regional variant is unavailable."""
    res = testclient.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client.client_id,
            "scope": "openid",
            "nonce": "somenonce",
            "redirect_uri": "https://client.test/redirect1",
            "ui_locales": "fr-CA fr en",
        },
        status=200,
    )

    res.mustcontain('<html lang="fr">')


def test_ui_locales_multiple_preferences(testclient, logged_user, client):
    """Test that ui_locales respects preference order."""
    res = testclient.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client.client_id,
            "scope": "openid",
            "nonce": "somenonce",
            "redirect_uri": "https://client.test/redirect1",
            "ui_locales": "es fr en",
        },
        status=200,
    )

    res.mustcontain('<html lang="es">')


def test_ui_locales_absent(testclient, logged_user, client):
    """Test that request works without ui_locales parameter."""
    testclient.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client.client_id,
            "scope": "openid",
            "nonce": "somenonce",
            "redirect_uri": "https://client.test/redirect1",
        },
        status=200,
    )


def test_ui_locales_default_language(testclient, logged_user, client):
    """Test that ui_locales works even when requesting the default language."""
    res = testclient.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client.client_id,
            "scope": "openid profile",
            "nonce": "somenonce",
            "redirect_uri": "https://client.test/redirect1",
            "ui_locales": "en",
        },
        status=200,
    )

    res.mustcontain('<html lang="en">')


def test_ui_locales_consent_page(testclient, logged_user, client):
    """Test that ui_locales is applied on consent page."""
    res = testclient.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client.client_id,
            "scope": "openid profile",
            "nonce": "somenonce",
            "redirect_uri": "https://client.test/redirect1",
            "ui_locales": "fr",
        },
        status=200,
    )

    res.mustcontain('<html lang="fr">')


def test_ui_locales_login_page(testclient, user, client):
    """Test that ui_locales is preserved when redirecting to login page."""
    res = testclient.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client.client_id,
            "scope": "openid",
            "nonce": "somenonce",
            "redirect_uri": "https://client.test/redirect1",
            "ui_locales": "fr",
        },
        status=302,
    )

    res = res.follow()

    res.mustcontain('<html lang="fr">')


def test_ui_locales_switch_user(testclient, logged_user, client):
    """Test that ui_locales is preserved when switching user."""
    res = testclient.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client.client_id,
            "scope": "openid profile",
            "nonce": "somenonce",
            "redirect_uri": "https://client.test/redirect1",
            "ui_locales": "fr",
        },
        status=200,
    )

    res.mustcontain('<html lang="fr">')

    res = res.form.submit(name="answer", value="logout")
    res = res.follow()
    res = res.follow()
    res = res.follow()

    res.mustcontain('<html lang="fr">')
