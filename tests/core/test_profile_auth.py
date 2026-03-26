import datetime

import pytest

from canaille.app import models
from canaille.core.auth import AuthenticationSession


def test_profile_auth_page(testclient, backend, logged_user):
    """Test accessing the authentication factors list page."""
    factors = ["password", "otp"]
    has_fido = backend.__class__.__name__ != "LDAPBackend"
    if has_fido:
        factors.append("fido2")
        testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = factors

    res = testclient.get("/profile/user/auth", status=200)
    res.mustcontain("Authentication")
    res.mustcontain("Password")
    res.mustcontain("Authenticator application")
    if has_fido:
        res.mustcontain("Passkeys")


def test_profile_auth_single_factor_redirects(testclient, logged_user):
    """Test that when only one factor is available, it redirects directly."""
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password"]

    res = testclient.get("/profile/user/auth", status=302)
    assert res.location == "/profile/user/auth/password"


def test_profile_auth_factor_invalid(testclient, logged_user):
    """Test accessing an invalid authentication factor."""
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password"]

    testclient.get("/profile/user/auth/invalid", status=404)


def test_profile_auth_factor_not_configured(testclient, logged_user):
    """Test accessing a factor that is not in AUTHENTICATION_FACTORS."""
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password"]

    testclient.get("/profile/user/auth/otp", status=404)


def test_profile_auth_unauthorized_user(testclient, logged_user, admin):
    """Test that a user cannot access another user's auth page."""
    testclient.get(f"/profile/{admin.user_name}/auth", status=404)


def test_profile_auth_factor_unauthorized_user(testclient, logged_user, admin):
    """Test that a user cannot access another user's auth factor page."""
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password"]

    testclient.get(f"/profile/{admin.user_name}/auth/password", status=404)


def test_profile_auth_admin_can_access_other_user(
    testclient, backend, logged_admin, user
):
    """Test that an admin can access another user's auth page."""
    factors = ["password", "otp"]
    if backend.__class__.__name__ != "LDAPBackend":
        factors.append("fido2")
        testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = factors

    res = testclient.get(f"/profile/{user.user_name}/auth", status=200)
    res.mustcontain("Authentication")


def test_fido2_auto_redirect_when_not_configured(testclient, backend, logged_user):
    """Test that accessing FIDO2 page without credentials redirects to setup."""
    if backend.__class__.__name__ == "LDAPBackend":
        pytest.skip("FIDO2 is not supported with LDAP backend")

    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password", "fido2"]
    assert len(logged_user.webauthn_credentials) == 0

    res = testclient.get("/profile/user/auth/fido2", status=302)
    assert res.location == "/auth/fido2-setup"

    with testclient.session_transaction() as session:
        assert "auth" in session
        auth = AuthenticationSession.deserialize(session["auth"])
        assert auth.remaining == ["fido2"]


def test_fido2_page_with_credentials(testclient, backend, logged_user):
    """Test accessing FIDO2 page when credentials are configured."""
    if backend.__class__.__name__ == "LDAPBackend":
        pytest.skip("FIDO2 is not supported with LDAP backend")

    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password", "fido2"]

    credential = models.WebAuthnCredential(
        credential_id=b"test_credential",
        public_key=b"test_public_key",
        sign_count=0,
        aaguid=b"\x00" * 16,
        transports='["usb"]',
        name="Test Key",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        user=logged_user,
    )
    backend.save(credential)
    backend.reload(logged_user)

    res = testclient.get("/profile/user/auth/fido2", status=200)
    res.mustcontain("Passkeys")
    res.mustcontain("Test Key")


def test_fido2_page_feature_disabled(testclient, backend, logged_user):
    """Test accessing FIDO2 page when feature is disabled."""
    if backend.__class__.__name__ == "LDAPBackend":
        pytest.skip("FIDO2 is not supported with LDAP backend")

    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = False
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password", "fido2"]

    testclient.get("/profile/user/auth/fido2", status=404)


def test_fido2_page_factor_not_configured(testclient, backend, logged_user):
    """Test accessing FIDO2 page when fido2 is not in AUTHENTICATION_FACTORS."""
    if backend.__class__.__name__ == "LDAPBackend":
        pytest.skip("FIDO2 is not supported with LDAP backend")

    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password"]

    testclient.get("/profile/user/auth/fido2", status=404)


def test_fido2_page_unauthorized_user(testclient, backend, logged_user, admin):
    """Test that a user cannot access another user's FIDO2 page."""
    if backend.__class__.__name__ == "LDAPBackend":
        pytest.skip("FIDO2 is not supported with LDAP backend")

    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password", "fido2"]

    testclient.get(f"/profile/{admin.user_name}/auth/fido2", status=404)


def test_otp_page_feature_disabled(testclient, logged_user):
    """Test accessing OTP page when feature is disabled."""
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = None
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password", "otp"]

    testclient.get("/profile/user/auth/otp", status=404)


def test_otp_page_unauthorized_user(testclient, logged_user, admin):
    """Test that a user cannot access another user's OTP page."""
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password", "otp"]

    testclient.get(f"/profile/{admin.user_name}/auth/otp", status=404)


def test_fido2_page_unrecognized_post_action(testclient, backend, logged_user):
    """Test POST with unrecognized action shows the page normally."""
    if backend.__class__.__name__ == "LDAPBackend":
        pytest.skip("FIDO2 is not supported with LDAP backend")

    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password", "fido2"]
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    credential = models.WebAuthnCredential(
        credential_id=b"test_credential",
        public_key=b"test_public_key",
        sign_count=0,
        aaguid=b"\x00" * 16,
        transports='["usb"]',
        name="Test Key",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        user=logged_user,
    )
    backend.save(credential)
    backend.reload(logged_user)

    res = testclient.post(
        "/profile/user/auth/fido2",
        {"action": "unknown-action"},
        status=200,
    )
    res.mustcontain("Passkeys")
