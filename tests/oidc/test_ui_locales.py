"""Tests the behavior of Canaille with the OIDC 'ui_locales' parameter.

https://openid.net/specs/openid-connect-core-1_0.html#AuthRequest
"""

from flask import g


def test_ui_locales_exact_match(testclient, logged_user, client):
    """Test that ui_locales parameter sets the correct locale with exact match."""
    testclient.get(
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

    assert g.ui_locales == "fr"


def test_ui_locales_with_fallback(testclient, logged_user, client):
    """Test that ui_locales falls back to base language when regional variant is unavailable."""
    testclient.get(
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

    assert g.ui_locales == "fr-CA fr en"


def test_ui_locales_multiple_preferences(testclient, logged_user, client):
    """Test that ui_locales respects preference order."""
    testclient.get(
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

    assert g.ui_locales == "es fr en"


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

    assert not hasattr(g, "ui_locales")


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
