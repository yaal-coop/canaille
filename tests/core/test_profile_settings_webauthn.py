import datetime

import pytest

from canaille.app import models
from canaille.core.auth import AuthenticationSession


@pytest.fixture(autouse=True)
def skip_ldap(backend):
    """Skip test if backend is LDAP."""
    if backend.__class__.__name__ == "LDAPBackend":
        pytest.skip("FIDO2 is not supported with LDAP backend")


@pytest.fixture
def fido_credential(testclient, logged_user, backend):
    """Create test FIDO2 credentials for the user."""
    credentials = []
    for i in range(3):
        credential = models.WebAuthnCredential(
            credential_id=f"credential_{i}".encode(),
            public_key=b"test_public_key",
            sign_count=0,
            aaguid=b"\x00" * 16,
            transports='["usb", "nfc"]',
            name=f"Security Key {i}",
            created_at=datetime.datetime.now(datetime.timezone.utc),
            user=logged_user,
        )
        backend.save(credential)
        credentials.append(credential)
    backend.reload(logged_user)
    return credentials


def test_confirm_delete_single_credential(testclient, logged_user, fido_credential):
    """Test confirmation modal for deleting a single credential."""
    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    credential_id = fido_credential[0].id

    res = testclient.post(
        f"/profile/{logged_user.user_name}/settings",
        {"confirm_credential": str(credential_id)},
        status=200,
    )

    res.mustcontain("delete-credential")
    res.mustcontain(fido_credential[0].name)


def test_confirm_delete_credential_not_found(testclient, logged_user, fido_credential):
    """Test confirmation modal with non-existent credential ID."""
    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    res = testclient.post(
        f"/profile/{logged_user.user_name}/settings",
        {"confirm_credential": "nonexistent-id"},
        status=200,
    )

    assert ("error", "Credential not found") in res.flashes


def test_delete_single_credential(testclient, logged_user, fido_credential, backend):
    """Test deleting a single credential."""
    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    credential_id = fido_credential[1].id
    assert len(logged_user.webauthn_credentials) == 3

    res = testclient.post(
        f"/profile/{logged_user.user_name}/settings",
        {
            "action": "delete-credential",
            "credential_id": str(credential_id),
        },
        status=200,
    )

    assert ("success", "WebAuthn credential has been removed") in res.flashes

    backend.reload(logged_user)
    assert len(logged_user.webauthn_credentials) == 2
    assert all(c.id != credential_id for c in logged_user.webauthn_credentials)


def test_delete_credential_without_id(testclient, logged_user, fido_credential):
    """Test deleting credential without providing credential_id."""
    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    res = testclient.post(
        f"/profile/{logged_user.user_name}/settings",
        {
            "action": "delete-credential",
        },
        status=200,
    )

    assert ("error", "Credential not found") in res.flashes


def test_delete_credential_not_found(testclient, logged_user, fido_credential):
    """Test deleting a non-existent credential."""
    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    res = testclient.post(
        f"/profile/{logged_user.user_name}/settings",
        {
            "action": "delete-credential",
            "credential_id": "nonexistent-id",
        },
        status=200,
    )

    assert ("error", "Credential not found") in res.flashes


def test_rename_credential(testclient, logged_user, fido_credential, backend):
    """Test renaming a credential."""
    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    credential_id = fido_credential[0].id
    new_name = "My YubiKey 5C"

    res = testclient.post(
        f"/profile/{logged_user.user_name}/settings",
        {
            "rename_credential": str(credential_id),
            f"credential_name_{credential_id}": new_name,
        },
        status=200,
    )

    assert ("success", "Security key renamed successfully") in res.flashes

    backend.reload(logged_user)
    credential = next(
        c for c in logged_user.webauthn_credentials if c.id == credential_id
    )
    assert credential.name == new_name


def test_rename_credential_empty_name(testclient, logged_user, fido_credential):
    """Test renaming credential with empty name."""
    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    credential_id = fido_credential[0].id

    res = testclient.post(
        f"/profile/{logged_user.user_name}/settings",
        {
            "rename_credential": str(credential_id),
            f"credential_name_{credential_id}": "   ",
        },
        status=200,
    )

    assert ("error", "Name cannot be empty") in res.flashes


def test_rename_credential_not_found(testclient, logged_user, fido_credential):
    """Test renaming a non-existent credential."""
    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    res = testclient.post(
        f"/profile/{logged_user.user_name}/settings",
        {
            "rename_credential": "nonexistent-id",
            "credential_name_nonexistent-id": "New Name",
        },
        status=200,
    )

    assert ("error", "Credential not found") in res.flashes


def test_reset_fido(testclient, logged_user, fido_credential, backend):
    """Test resetting all FIDO2 credentials from user profile."""
    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    assert len(logged_user.webauthn_credentials) > 0

    # Confirm reset
    res = testclient.post(
        f"/profile/{logged_user.user_name}/settings",
        {"action": "confirm-reset-fido2"},
        status=200,
    )
    assert b"reset" in res.body.lower()

    # Perform reset
    res = testclient.post(
        f"/profile/{logged_user.user_name}/settings",
        {"action": "reset-fido2"},
        status=200,
    )

    assert ("success", "All WebAuthn credentials have been removed") in res.flashes

    backend.reload(logged_user)
    assert len(logged_user.webauthn_credentials) == 0


def test_setup_fido_redirects_to_auth(testclient, logged_user):
    """Test setting up FIDO2 from user profile redirects to setup flow."""
    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    res = testclient.post(
        f"/profile/{logged_user.user_name}/settings",
        {"action": "setup-fido2"},
        status=302,
    )

    assert res.location == "/auth/fido2-setup"

    with testclient.session_transaction() as session:
        assert "auth" in session
        auth = AuthenticationSession.deserialize(session["auth"])
        assert auth.remaining == ["fido2"]
