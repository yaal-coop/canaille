import datetime
import json
import logging
import uuid
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from webauthn.helpers.bytes_to_base64url import bytes_to_base64url
from webauthn.helpers.exceptions import InvalidAuthenticationResponse
from webauthn.helpers.exceptions import InvalidRegistrationResponse

from canaille.app import models
from canaille.app.fido import get_fake_credential
from canaille.core.auth import AuthenticationSession


@pytest.fixture
def configuration(configuration):
    configuration["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["fido2"]
    configuration["CANAILLE"]["JAVASCRIPT"] = True
    configuration["WTF_CSRF_ENABLED"] = False
    return configuration


@pytest.fixture(autouse=True)
def skip_ldap(backend):
    """Skip test if backend is LDAP."""
    if backend.__class__.__name__ == "LDAPBackend":
        pytest.skip("FIDO2 is not supported with LDAP backend")


@pytest.fixture
def fido_credential(user, backend):
    """Create a test FIDO2 credential for the user."""
    credential = models.WebAuthnCredential(
        credential_id=b"test_credential_id_123456",
        public_key=b"test_public_key_data",
        sign_count=0,
        aaguid=b"\x00" * 16,
        transports='["usb", "nfc"]',
        name="Test YubiKey",
        created_at=datetime.datetime.now(datetime.UTC),
        user=user,
    )
    backend.save(credential)
    backend.reload(user)
    return credential


@pytest.mark.parametrize("path", ["/auth/fido2", "/auth/fido2-setup"])
def test_fido_posts_require_csrf_token(testclient, path):
    """WebAuthn POST endpoints reject requests without a CSRF token."""
    testclient.app.config["WTF_CSRF_ENABLED"] = True

    response = testclient.post_json(path, {}, status=400)

    assert response.json == {
        "success": False,
        "error": "This page has expired. Please reload it.",
    }


@patch("webauthn.verify_authentication_response")
def test_fido_authentication_accepts_valid_csrf_token(
    mock_verify, testclient, fido_credential
):
    """WebAuthn authentication accepts the CSRF token rendered by its form."""
    testclient.app.config["WTF_CSRF_ENABLED"] = True
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user", remaining=["fido2"]
        ).serialize()
    page = testclient.get("/auth/fido2", status=200)
    csrf_token = page.pyquery("#csrf-token").val()

    assert csrf_token

    mock_verify.return_value = MagicMock(new_sign_count=1)
    response = testclient.post_json(
        "/auth/fido2",
        {
            "id": "test_id",
            "rawId": "dGVzdF9jcmVkZW50aWFsX2lkXzEyMzQ1Ng",
            "type": "public-key",
            "response": {
                "authenticatorData": "eHh4eHh4eHh4",
                "clientDataJSON": "eHh4eHh4eHh4eHh4eHh4",
                "signature": "eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4",
                "userHandle": None,
            },
        },
        headers={"X-CSRFToken": csrf_token},
        status=200,
    )

    assert response.json["success"] is True


@pytest.mark.parametrize("logged_in", [False, True])
@patch("webauthn.verify_registration_response")
def test_fido_registration_accepts_valid_csrf_token(
    mock_verify, testclient, user, backend, request, logged_in
):
    """WebAuthn registration accepts the CSRF token rendered by its form."""
    testclient.app.config["WTF_CSRF_ENABLED"] = True
    if logged_in:
        request.getfixturevalue("logged_user")
    else:
        with testclient.session_transaction() as session:
            session["auth"] = AuthenticationSession(
                user_name="user", remaining=["fido2"], achieved=["password"]
            ).serialize()
    page = testclient.get("/auth/fido2-setup", status=200)
    csrf_token = page.pyquery("#csrf-token").val()

    assert csrf_token

    mock_verify.return_value = MagicMock(
        credential_id=b"new_credential_id",
        credential_public_key=b"new_public_key",
        sign_count=0,
        aaguid=b"\x00" * 16,
    )
    response = testclient.post_json(
        "/auth/fido2-setup",
        {
            "credential": {
                "id": "new_id",
                "rawId": "bmV3X2lk",
                "type": "public-key",
                "response": {
                    "attestationObject": "dGVzdA",
                    "clientDataJSON": "dGVzdA",
                },
            },
        },
        headers={"X-CSRFToken": csrf_token},
        status=200,
    )

    assert response.json["success"] is True


def test_no_auth_session_not_logged_in(testclient, user):
    """Non-logged users should not be able to access the fido2 auth form without an authentication session."""
    res = testclient.get("/auth/fido2", status=302)
    assert res.location == "/login"
    assert res.flashes == [
        ("warning", "Cannot remember the login you attempted to sign in with.")
    ]


def test_no_auth_session_logged_in(testclient, logged_user):
    """Logged users should not be able to access the fido2 auth form without an authentication session."""
    res = testclient.get("/auth/fido2", status=302)
    assert res.location == "/"


def test_not_fido_step(testclient, user):
    """Users reaching the fido2 form while this is not the right auth step should be redirected."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["email", "fido2"],
        ).serialize()

    res = testclient.get("/auth/fido2", status=302)
    assert res.location == "/auth/email"


def test_redirect_to_setup_without_credential(testclient, user):
    """Users without a FIDO2 credential should be redirected to setup."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
        ).serialize()

    res = testclient.get("/auth/fido2", status=302)
    assert res.location == "/auth/fido2-setup"


@patch("webauthn.generate_authentication_options")
def test_generate_auth_options(mock_gen_options, testclient, user, fido_credential):
    """Test generation of authentication options."""
    mock_options = MagicMock()
    mock_options.challenge = b"test_challenge_bytes"
    mock_gen_options.return_value = mock_options

    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
        ).serialize()

    with patch("webauthn.options_to_json") as mock_to_json:
        mock_to_json.return_value = '{"challenge": "test_challenge"}'

        res = testclient.get("/auth/fido2", status=200)

        with testclient.session_transaction() as session:
            assert (
                session["auth"]["data"]["fido_challenge"]
                == "dGVzdF9jaGFsbGVuZ2VfYnl0ZXM"
            )

        assert b"test_challenge" in res.body


@patch("webauthn.verify_authentication_response")
def test_successful_authentication(
    mock_verify, testclient, user, fido_credential, backend, caplog
):
    """Test successful FIDO2 authentication."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
            data={"fido_challenge": "dGVzdF9jaGFsbGVuZ2U"},
        ).serialize()

    mock_verification = MagicMock()
    mock_verification.new_sign_count = 1
    mock_verify.return_value = mock_verification

    credential_response = {
        "id": "test_id",
        "rawId": "dGVzdF9jcmVkZW50aWFsX2lkXzEyMzQ1Ng",  # base64url of test_credential_id_123456
        "type": "public-key",
        "response": {
            "authenticatorData": "eHh4eHh4eHh4",
            "clientDataJSON": "eHh4eHh4eHh4eHh4eHh4",
            "signature": "eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4",
            "userHandle": None,
        },
    }

    res = testclient.post_json("/auth/fido2", credential_response, status=200)
    data = json.loads(res.body)

    assert data["success"] is True
    assert "redirect" in data

    user_reloaded = backend.get(models.User, id=user.id)
    assert user_reloaded.webauthn_credentials[0].sign_count == 1
    assert user_reloaded.webauthn_credentials[0].last_used_at is not None


@patch("webauthn.verify_authentication_response")
def test_full_login_flow_with_existing_credential(
    mock_verify,
    testclient,
    user,
    fido_credential,
    backend,
):
    """Test complete login flow from /login with existing FIDO2 credential."""
    res = testclient.get("/login", status=200)
    assert b"Login" in res.body

    res = testclient.post(
        "/login",
        {"login": user.user_name, "remember": "y"},
        status=302,
    )
    assert res.location == "/auth/fido2"

    # Simulate what GET /auth/fido2 would do
    with testclient.session_transaction() as session:
        auth = session["auth"]
        auth["data"] = {"fido_challenge": "dGVzdF9jaGFsbGVuZ2U"}
        session["auth"] = auth

    mock_verification = MagicMock()
    mock_verification.new_sign_count = 1
    mock_verify.return_value = mock_verification

    credential_response = {
        "id": "test_id",
        "rawId": "dGVzdF9jcmVkZW50aWFsX2lkXzEyMzQ1Ng",  # base64url of test_credential_id_123456
        "type": "public-key",
        "response": {
            "authenticatorData": "eHh4eHh4eHh4",
            "clientDataJSON": "eHh4eHh4eHh4eHh4eHh4",
            "signature": "eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4",
            "userHandle": None,
        },
    }

    res = testclient.post_json("/auth/fido2", credential_response, status=200)
    data = json.loads(res.body)

    assert data["success"] is True
    assert "redirect" in data
    assert data["redirect"] == "/"

    with testclient.session_transaction() as session:
        assert "sessions" in session
        assert len(session["sessions"]) > 0
        assert "auth" not in session

    user_reloaded = backend.get(models.User, id=user.id)
    assert user_reloaded.webauthn_credentials[0].sign_count == 1
    assert user_reloaded.webauthn_credentials[0].last_used_at is not None


@patch("webauthn.verify_registration_response")
def test_full_login_flow_with_credential_setup(mock_verify, testclient, user, backend):
    """Test complete login flow requiring FIDO2 credential setup."""
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password", "fido2"]
    assert len(user.webauthn_credentials) == 0

    res = testclient.get("/login", status=200)
    assert b"Login" in res.body

    res = testclient.post(
        "/login",
        {"login": user.user_name, "remember": "y"},
        status=302,
    )
    assert res.location == "/auth/password"

    res = testclient.post(
        "/auth/password",
        {"password": "correct horse battery staple"},
        status=302,
    )
    assert res.location == "/auth/fido2"

    # User has no credential, should redirect to setup
    res = testclient.get("/auth/fido2", status=302)
    assert res.location == "/auth/fido2-setup"

    # Simulate what GET /auth/fido2-setup would do
    with testclient.session_transaction() as session:
        auth = session["auth"]
        auth["data"] = {"fido_challenge": "dGVzdF9jaGFsbGVuZ2U"}
        session["auth"] = auth

    mock_verified = MagicMock()
    mock_verified.credential_id = b"new_credential_id_123"
    mock_verified.credential_public_key = b"new_public_key_data"
    mock_verified.sign_count = 0
    mock_verified.aaguid = b"\x00" * 16
    mock_verified.credential_device_type = "single_device"
    mock_verified.credential_backed_up = False
    mock_verify.return_value = mock_verified

    registration_response = {
        "id": "bmV3X2NyZWRlbnRpYWxfaWRfMTIz",
        "rawId": "bmV3X2NyZWRlbnRpYWxfaWRfMTIz",
        "type": "public-key",
        "response": {
            "attestationObject": "dGVzdF9hdHRlc3RhdGlvbg",
            "clientDataJSON": "dGVzdF9jbGllbnQ",
        },
        "transports": ["usb", "nfc"],
    }

    res = testclient.post_json(
        "/auth/fido2-setup",
        {"credential": registration_response},
        status=200,
    )
    data = json.loads(res.body)

    assert data["success"] is True
    assert "redirect" in data
    assert data["redirect"] == "/"

    with testclient.session_transaction() as session:
        assert "sessions" in session
        assert len(session["sessions"]) > 0
        assert "auth" not in session

    user_reloaded = backend.get(models.User, id=user.id)
    assert len(user_reloaded.webauthn_credentials) > 0
    assert user_reloaded.webauthn_credentials[0].name == "My passkey"
    assert user_reloaded.webauthn_credentials[0].sign_count == 0


@patch("webauthn.generate_registration_options")
def test_generate_registration_options(mock_gen_options, testclient, user):
    """Test generation of registration options."""
    mock_options = MagicMock()
    mock_options.challenge = b"test_reg_challenge"
    mock_gen_options.return_value = mock_options

    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
        ).serialize()

    with patch("webauthn.options_to_json") as mock_to_json:
        mock_to_json.return_value = '{"challenge": "test_reg_challenge"}'

        testclient.get("/auth/fido2-setup", status=200)

        with testclient.session_transaction() as session:
            assert (
                session["auth"]["data"]["fido_challenge"] == "dGVzdF9yZWdfY2hhbGxlbmdl"
            )


@patch("webauthn.verify_registration_response")
def test_successful_registration(mock_verify, testclient, user, backend, caplog):
    """Test successful FIDO2 credential registration."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
            data={"fido_challenge": "dGVzdF9yZWdfY2hhbGxlbmdl"},
        ).serialize()

    mock_verification = MagicMock()
    mock_verification.credential_id = b"new_credential_id"
    mock_verification.credential_public_key = b"new_public_key"
    mock_verification.sign_count = 0
    mock_verification.aaguid = b"\x00" * 16
    mock_verify.return_value = mock_verification

    registration_response = {
        "credential": {
            "id": "new_id",
            "rawId": "bmV3X2lk",
            "type": "public-key",
            "response": {
                "attestationObject": "dGVzdF9hdHRlc3Q",
                "clientDataJSON": "dGVzdF9jbGllbnQ",
                "transports": ["usb", "nfc"],
            },
        },
    }

    res = testclient.post_json("/auth/fido2-setup", registration_response, status=200)
    data = json.loads(res.body)

    assert data["success"] is True

    user_reloaded = backend.get(models.User, id=user.id)
    assert len(user_reloaded.webauthn_credentials) > 0
    assert user_reloaded.webauthn_credentials[0].name == "My passkey"
    assert user_reloaded.webauthn_credentials[0].credential_id == b"new_credential_id"


def test_fido_disabled(testclient, user):
    """Test accessing FIDO endpoints when feature is disabled."""
    testclient.app.config["CANAILLE"]["JAVASCRIPT"] = False

    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
        ).serialize()

    testclient.get("/auth/fido2", status=404)
    testclient.get("/auth/fido2-setup", status=404)


def test_auth_without_credential(testclient, user):
    """Test authentication endpoint without credential redirects to setup."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
        ).serialize()

    res = testclient.get("/auth/fido2", status=302)
    assert res.location == "/auth/fido2-setup"


def test_auth_response_empty_body(testclient, user, fido_credential):
    """Test POST authentication with empty body."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
            data={"fido_challenge": "dGVzdF9jaGFsbGVuZ2U"},
        ).serialize()

    response = testclient.post_json(
        "/auth/fido2",
        None,
        status=400,
    )
    assert response.json["success"] is False
    assert "Invalid JSON" in response.json["error"]


def test_auth_response_missing_raw_id(testclient, user, fido_credential):
    """Test POST authentication with missing rawId field."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
            data={"fido_challenge": "dGVzdF9jaGFsbGVuZ2U"},
        ).serialize()

    response = testclient.post_json(
        "/auth/fido2",
        {
            "id": "test",
            # rawId is missing
            "type": "public-key",
            "response": {
                "authenticatorData": "dGVzdA",
                "clientDataJSON": "dGVzdA",
                "signature": "dGVzdA",
            },
        },
        status=400,
    )
    assert response.json["success"] is False
    assert "Invalid credential ID" in response.json["error"]


def test_auth_response_without_challenge(testclient, user, fido_credential):
    """Test POST authentication without challenge in session."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
        ).serialize()
        # No challenge in session

    response = testclient.post_json(
        "/auth/fido2",
        {"id": "test", "rawId": "dGVzdA", "type": "public-key"},
        status=400,
    )
    assert response.json["success"] is False
    assert "No challenge found" in response.json["error"]


def test_auth_response_with_exception(testclient, user, fido_credential, caplog):
    """Test POST authentication with verification exception."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
            data={"fido_challenge": "dGVzdF9jaGFsbGVuZ2U"},
        ).serialize()

    with patch("webauthn.verify_authentication_response") as mock_verify:
        mock_verify.side_effect = InvalidAuthenticationResponse("Verification failed")

        response = testclient.post_json(
            "/auth/fido2",
            {
                "id": "test",
                "rawId": "dGVzdF9jcmVkZW50aWFsX2lkXzEyMzQ1Ng",  # matches fixture credential_id
                "type": "public-key",
                "response": {
                    "authenticatorData": "dGVzdA",
                    "clientDataJSON": "dGVzdA",
                    "signature": "dGVzdA",
                },
            },
            status=400,
        )

    assert response.json["success"] is False
    assert "Verification failed" in response.json["error"]


def test_setup_without_user(testclient):
    """Test setup endpoint without authenticated user."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="nonexistent",
            remaining=["fido2"],
            achieved=["password"],
        ).serialize()

    res = testclient.get("/auth/fido2-setup", status=302)
    assert res.location == "/auth/fido2"


def test_setup_from_profile_without_auth(testclient, logged_user):
    """Test accessing setup directly from profile creates auth session."""
    testclient.get("/auth/fido2-setup", status=200)

    with testclient.session_transaction() as session:
        assert "auth" in session
        auth = AuthenticationSession.deserialize(session["auth"])
        assert auth.user_name == logged_user.user_name
        assert auth.remaining == ["fido2"]


def test_registration_empty_body(testclient, user):
    """Test POST registration with empty body."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
            data={"fido_challenge": "dGVzdF9jaGFsbGVuZ2U"},
        ).serialize()

    response = testclient.post_json(
        "/auth/fido2-setup",
        None,
        status=400,
    )
    assert response.json["success"] is False
    assert "Invalid JSON" in response.json["error"]


def test_registration_missing_credential(testclient, user):
    """Test POST registration with missing credential field."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
            data={"fido_challenge": "dGVzdF9jaGFsbGVuZ2U"},
        ).serialize()

    response = testclient.post_json(
        "/auth/fido2-setup",
        {"something": "else"},  # No 'credential' field
        status=400,
    )
    assert response.json["success"] is False
    assert "Missing credential data" in response.json["error"]


def test_registration_invalid_session(testclient, user):
    """Test registration without valid session data."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
        ).serialize()
        # No challenge or user_id in session

    response = testclient.post_json(
        "/auth/fido2-setup",
        {
            "credential": {"id": "test"},
        },
        status=400,
    )
    assert response.json["success"] is False
    assert "Invalid session" in response.json["error"]


def test_registration_with_exception(testclient, user, caplog):
    """Test registration with verification exception."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
            data={"fido_challenge": "dGVzdA"},
        ).serialize()

    with patch("webauthn.verify_registration_response") as mock_verify:
        mock_verify.side_effect = InvalidRegistrationResponse("Registration failed")

        response = testclient.post_json(
            "/auth/fido2-setup",
            {
                "credential": {"id": "test", "response": {}},
            },
            status=400,
        )

    assert response.json["success"] is False
    assert "Registration failed" in response.json["error"]


def test_registration_with_string_aaguid(testclient, user, backend):
    """Test registration with string AAGUID conversion."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
            data={"fido_challenge": "dGVzdA"},
        ).serialize()

    mock_verification = MagicMock()
    mock_verification.credential_id = b"test_id"
    mock_verification.credential_public_key = b"test_key"
    mock_verification.sign_count = 0
    # String AAGUID (UUID format)
    mock_verification.aaguid = "00000000-0000-0000-0000-000000000000"

    with patch("webauthn.verify_registration_response") as mock_verify:
        mock_verify.return_value = mock_verification

        testclient.post_json(
            "/auth/fido2-setup",
            {
                "credential": {"id": "test", "response": {}},
            },
            status=200,
        )

    user_reloaded = backend.get(models.User, id=user.id)
    assert len(user_reloaded.webauthn_credentials) > 0
    assert isinstance(user_reloaded.webauthn_credentials[0].aaguid, bytes)


def test_registration_with_uuid_aaguid(testclient, user, backend):
    """Test registration with UUID object AAGUID conversion."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
            data={"fido_challenge": "dGVzdA"},
        ).serialize()

    mock_verification = MagicMock()
    mock_verification.credential_id = b"test_id2"
    mock_verification.credential_public_key = b"test_key2"
    mock_verification.sign_count = 0
    # UUID object AAGUID
    mock_verification.aaguid = uuid.UUID("00000000-0000-0000-0000-000000000001")

    with patch("webauthn.verify_registration_response") as mock_verify:
        mock_verify.return_value = mock_verification

        testclient.post_json(
            "/auth/fido2-setup",
            {
                "credential": {"id": "test2", "response": {}},
            },
            status=200,
        )

    user_reloaded = backend.get(models.User, id=user.id)
    assert len(user_reloaded.webauthn_credentials) > 0
    assert isinstance(user_reloaded.webauthn_credentials[0].aaguid, bytes)


@patch("webauthn.generate_authentication_options")
def test_auth_with_credential_without_transports(
    mock_gen_options, testclient, user, backend
):
    """Test authentication with credential that has no transports."""
    credential = models.WebAuthnCredential(
        credential_id=b"test_credential_id",
        public_key=b"test_public_key",
        sign_count=0,
        aaguid=b"\x00" * 16,
        transports=None,  # No transports
        name="Test Key",
        created_at=datetime.datetime.now(datetime.UTC),
        user=user,
    )
    backend.save(credential)
    backend.reload(user)

    mock_options = MagicMock()
    mock_options.challenge = b"test_challenge"
    mock_gen_options.return_value = mock_options

    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
        ).serialize()

    with patch("webauthn.options_to_json") as mock_to_json:
        mock_to_json.return_value = '{"challenge": "test"}'
        testclient.get("/auth/fido2", status=200)

    assert mock_gen_options.called
    call_kwargs = mock_gen_options.call_args.kwargs
    assert "allow_credentials" in call_kwargs
    assert len(call_kwargs["allow_credentials"]) == 1


@patch("webauthn.generate_authentication_options")
def test_auth_with_credential_empty_transports(
    mock_gen_options, testclient, user, backend
):
    """Test authentication with credential that has empty transports list."""
    credential = models.WebAuthnCredential(
        credential_id=b"test_credential_id",
        public_key=b"test_public_key",
        sign_count=0,
        aaguid=b"\x00" * 16,
        transports="[]",  # Empty list
        name="Test Key",
        created_at=datetime.datetime.now(datetime.UTC),
        user=user,
    )
    backend.save(credential)
    backend.reload(user)

    mock_options = MagicMock()
    mock_options.challenge = b"test_challenge"
    mock_gen_options.return_value = mock_options

    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
        ).serialize()

    with patch("webauthn.options_to_json") as mock_to_json:
        mock_to_json.return_value = '{"challenge": "test"}'
        testclient.get("/auth/fido2", status=200)

    assert mock_gen_options.called
    call_kwargs = mock_gen_options.call_args.kwargs
    assert "allow_credentials" in call_kwargs
    assert len(call_kwargs["allow_credentials"]) == 1


@patch("webauthn.verify_registration_response")
def test_registration_with_none_aaguid(mock_verify, testclient, user, backend):
    """Test credential registration when aaguid is None."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
            data={"fido_challenge": "dGVzdF9jaGFsbGVuZ2U"},
        ).serialize()

    mock_verification = MagicMock()
    mock_verification.credential_id = b"credential_no_aaguid"
    mock_verification.credential_public_key = b"public_key"
    mock_verification.sign_count = 0
    mock_verification.aaguid = None  # aaguid is None
    mock_verify.return_value = mock_verification

    registration_response = {
        "credential": {
            "id": "test_id",
            "rawId": "dGVzdF9pZA",
            "type": "public-key",
            "response": {
                "attestationObject": "dGVzdF9hdHRlc3Q",
                "clientDataJSON": "dGVzdF9jbGllbnQ",
            },
        },
    }

    res = testclient.post_json("/auth/fido2-setup", registration_response, status=200)
    data = json.loads(res.body)

    assert data["success"] is True

    user_reloaded = backend.get(models.User, id=user.id)
    assert len(user_reloaded.webauthn_credentials) > 0
    assert user_reloaded.webauthn_credentials[0].aaguid is None


def test_auth_response_with_wrong_credential_id(testclient, user, fido_credential):
    """Test POST authentication with wrong credential rawId."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
            data={"fido_challenge": "dGVzdF9jaGFsbGVuZ2U"},
        ).serialize()

    response = testclient.post_json(
        "/auth/fido2",
        {
            "id": "wrong",
            "rawId": "d3JvbmdfY3JlZGVudGlhbF9pZA",  # "wrong_credential_id" in base64url
            "type": "public-key",
            "response": {
                "authenticatorData": "dGVzdA",
                "clientDataJSON": "dGVzdA",
                "signature": "dGVzdA",
            },
        },
        status=400,
    )
    assert response.json["success"] is False
    assert "Credential not found" in response.json["error"]


def test_max_credentials_reached_during_setup_get(testclient, logged_user, backend):
    """Test setup GET when user has reached max credentials limit."""
    user = logged_user
    # Create 5 credentials (default max)
    for i in range(5):
        credential = models.WebAuthnCredential(
            credential_id=f"credential_{i}".encode(),
            public_key=b"test_public_key",
            sign_count=0,
            aaguid=b"\x00" * 16,
            name=f"Key {i}",
            created_at=datetime.datetime.now(datetime.UTC),
            user=user,
        )
        backend.save(credential)
    backend.reload(user)

    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            data={"enrollment": True},
        ).serialize()

    res = testclient.get("/auth/fido2-setup", status=302)
    assert res.location == f"/profile/{user.user_name}/auth/fido2"
    assert any("Maximum number of passkeys reached" in msg for _, msg in res.flashes)


def test_max_credentials_reached_during_setup_post(testclient, logged_user, backend):
    """Test setup POST when user has reached max credentials limit (safety check)."""
    user = logged_user
    # Create 5 credentials (default max)
    for i in range(5):
        credential = models.WebAuthnCredential(
            credential_id=f"credential_{i}".encode(),
            public_key=b"test_public_key",
            sign_count=0,
            aaguid=b"\x00" * 16,
            name=f"Key {i}",
            created_at=datetime.datetime.now(datetime.UTC),
            user=user,
        )
        backend.save(credential)
    backend.reload(user)

    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            data={"fido_challenge": "dGVzdA", "enrollment": True},
        ).serialize()

    response = testclient.post_json(
        "/auth/fido2-setup",
        {
            "credential": {"id": "test", "response": {}},
        },
        status=400,
    )
    assert response.json["success"] is False
    assert "Maximum number of passkeys reached" in response.json["error"]


@patch("webauthn.generate_registration_options")
def test_setup_with_existing_credentials_with_transports(
    mock_gen_options, testclient, logged_user, backend
):
    """Test setup with existing credentials that have transports (exclude_credentials)."""
    user = logged_user
    for i in range(2):
        credential = models.WebAuthnCredential(
            credential_id=f"existing_{i}".encode(),
            public_key=b"test_public_key",
            sign_count=0,
            aaguid=b"\x00" * 16,
            transports='["usb", "nfc"]',
            name=f"Existing Key {i}",
            created_at=datetime.datetime.now(datetime.UTC),
            user=user,
        )
        backend.save(credential)
    backend.reload(user)

    mock_options = MagicMock()
    mock_options.challenge = b"test_challenge"
    mock_gen_options.return_value = mock_options

    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            data={"enrollment": True},
        ).serialize()

    with patch("webauthn.options_to_json") as mock_to_json:
        mock_to_json.return_value = '{"challenge": "test"}'
        testclient.get("/auth/fido2-setup", status=200)

    assert mock_gen_options.called
    call_kwargs = mock_gen_options.call_args.kwargs
    assert "exclude_credentials" in call_kwargs
    assert call_kwargs["exclude_credentials"] is not None
    assert len(call_kwargs["exclude_credentials"]) == 2


@patch("webauthn.generate_registration_options")
def test_setup_with_credentials_without_and_empty_transports(
    mock_gen_options, testclient, logged_user, backend
):
    """Test setup with credentials that have None or empty transports."""
    user = logged_user
    credential1 = models.WebAuthnCredential(
        credential_id=b"no_transports",
        public_key=b"test_public_key",
        sign_count=0,
        aaguid=b"\x00" * 16,
        transports=None,
        name="Key without transports",
        created_at=datetime.datetime.now(datetime.UTC),
        user=user,
    )
    backend.save(credential1)

    credential2 = models.WebAuthnCredential(
        credential_id=b"empty_transports",
        public_key=b"test_public_key",
        sign_count=0,
        aaguid=b"\x00" * 16,
        transports="[]",
        name="Key with empty transports",
        created_at=datetime.datetime.now(datetime.UTC),
        user=user,
    )
    backend.save(credential2)
    backend.reload(user)

    mock_options = MagicMock()
    mock_options.challenge = b"test_challenge"
    mock_gen_options.return_value = mock_options

    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            data={"enrollment": True},
        ).serialize()

    with patch("webauthn.options_to_json") as mock_to_json:
        mock_to_json.return_value = '{"challenge": "test"}'
        testclient.get("/auth/fido2-setup", status=200)

    assert mock_gen_options.called
    call_kwargs = mock_gen_options.call_args.kwargs
    assert "exclude_credentials" in call_kwargs
    # Both credentials should be in exclude list even without transports
    assert len(call_kwargs["exclude_credentials"]) == 2


@patch("webauthn.verify_registration_response")
def test_registration_from_profile_while_logged_in(
    mock_verify, testclient, logged_user, backend
):
    """Test credential registration when user is already logged in (adding from profile)."""
    testclient.post(
        f"/profile/{logged_user.user_name}/auth/fido2",
        {"action": "fido2-setup"},
        status=302,
    )

    # Simulate challenge set by GET /auth/fido2-setup
    with testclient.session_transaction() as session:
        auth = session["auth"]
        auth["data"]["fido_challenge"] = "dGVzdA"
        session["auth"] = auth

    mock_verification = MagicMock()
    mock_verification.credential_id = b"new_credential"
    mock_verification.credential_public_key = b"new_key"
    mock_verification.sign_count = 0
    mock_verification.aaguid = b"\x00" * 16
    mock_verify.return_value = mock_verification

    registration_response = {
        "credential": {
            "id": "new_id",
            "rawId": "bmV3X2lk",
            "type": "public-key",
            "response": {
                "attestationObject": "dGVzdA",
                "clientDataJSON": "dGVzdA",
            },
        },
    }

    res = testclient.post_json("/auth/fido2-setup", registration_response, status=200)
    data = json.loads(res.body)

    assert data["success"] is True
    assert data["redirect"] == f"/profile/{logged_user.user_name}/auth/fido2"

    user_reloaded = backend.get(models.User, id=logged_user.id)
    assert len(user_reloaded.webauthn_credentials) > 0

    with testclient.session_transaction() as session:
        assert "auth" not in session


REGISTRATION_RESPONSE = {
    "credential": {
        "id": "YXR0YWNrZXI",
        "rawId": "YXR0YWNrZXI",
        "type": "public-key",
        "response": {"attestationObject": "dGVzdA", "clientDataJSON": "dGVzdA"},
    },
}


def mock_registration(mock_verify):
    mock_verify.return_value = MagicMock(
        credential_id=b"attacker",
        credential_public_key=b"attacker_public_key",
        sign_count=0,
        aaguid=None,
    )


def set_fido_challenge(testclient):
    with testclient.session_transaction() as session:
        auth = session["auth"]
        auth["data"] = {"fido_challenge": "dGVzdA"}
        session["auth"] = auth


@patch("webauthn.verify_registration_response")
def test_fido_setup_before_password(mock_verify, testclient, backend, user):
    """The passkey setup page cannot be used to skip the password step."""
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password"]
    mock_registration(mock_verify)

    res = testclient.get("/login/user", status=302)
    assert res.location == "/auth/password"

    res = testclient.get("/auth/fido2-setup", status=302)
    assert res.location == "/auth/password"

    set_fido_challenge(testclient)
    res = testclient.post_json("/auth/fido2-setup", REGISTRATION_RESPONSE, status=400)
    assert res.json == {"success": False, "error": "Invalid session"}

    backend.reload(user)
    assert not user.webauthn_credentials
    with testclient.session_transaction() as session:
        assert not session.get("sessions")


@patch("webauthn.verify_registration_response")
def test_fido_setup_with_existing_credential(
    mock_verify, testclient, backend, user, fido_credential
):
    """Users who have a passkey cannot add another one during the login."""
    mock_registration(mock_verify)
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["fido2"],
            achieved=["password"],
            data={"fido_challenge": "dGVzdA"},
        ).serialize()

    res = testclient.get("/auth/fido2-setup", status=302)
    assert res.location == "/auth/fido2"

    res = testclient.post_json("/auth/fido2-setup", REGISTRATION_RESPONSE, status=400)
    assert res.json == {"success": False, "error": "Invalid session"}

    backend.reload(user)
    assert len(user.webauthn_credentials) == 1


def test_fido_setup_as_first_step(testclient, backend, user, caplog):
    """Users cannot enroll a passkey when it is the first authentication step."""
    res = testclient.post("/login", {"login": "user"}, status=302)
    assert res.location == "/auth/fido2"

    res = testclient.get("/auth/fido2", status=302)
    assert res.location == "/login"
    assert (
        "error",
        "This authentication method is not set up for your account. "
        "Please contact your administrator.",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Authentication factor enrollment refused for user",
    ) in caplog.record_tuples

    res = testclient.get("/auth/fido2-setup", status=302)
    assert res.location == "/login"

    backend.reload(user)
    assert not user.webauthn_credentials


@patch("webauthn.verify_registration_response")
def test_fido_setup_for_another_user_while_logged_in(
    mock_verify, testclient, backend, logged_user, admin
):
    """Logged-in users cannot enroll a passkey on another account they log in."""
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password"]
    mock_registration(mock_verify)

    res = testclient.post("/login", {"login": "admin"}, status=302)
    assert res.location == "/auth/password"

    set_fido_challenge(testclient)
    res = testclient.post_json("/auth/fido2-setup", REGISTRATION_RESPONSE, status=400)
    assert res.json == {"success": False, "error": "Invalid session"}

    backend.reload(admin)
    assert not admin.webauthn_credentials


def test_fido_setup_without_auth_session(testclient):
    """The passkey setup page needs a login in progress."""
    res = testclient.get("/auth/fido2-setup", status=302)
    assert res.location == "/login"

    res = testclient.post_json("/auth/fido2-setup", REGISTRATION_RESPONSE, status=400)
    assert res.json == {"success": False, "error": "Invalid session"}


@patch("webauthn.verify_registration_response")
def test_fido_setup_first_passkey_of_another_account(
    mock_verify, testclient, backend, logged_user, admin
):
    """Enrolling a first passkey while logging in to a second account finishes this login."""
    mock_registration(mock_verify)
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="admin",
            remaining=["fido2"],
            achieved=["password"],
            data={"fido_challenge": "dGVzdA"},
        ).serialize()

    res = testclient.post_json("/auth/fido2-setup", REGISTRATION_RESPONSE, status=200)
    assert res.json == {"success": True, "redirect": "/"}

    backend.reload(admin)
    assert len(admin.webauthn_credentials) == 1
    with testclient.session_transaction() as session:
        assert len(session["sessions"]) == 2
        assert "auth" not in session


def allowed_credentials_for(testclient, login):
    testclient.post("/login", {"login": login}, status=302)
    res = testclient.get("/auth/fido2", status=200)
    return json.loads(res.pyquery("#webauthn-options").val())["allowCredentials"]


def test_unknown_login_gets_a_fake_credential(testclient, fido_credential):
    """Unknown logins get a stable fake passkey, so they look like real accounts."""
    fake = get_fake_credential("nobody")
    unknown = allowed_credentials_for(testclient, "nobody")
    assert unknown == [
        {
            "id": bytes_to_base64url(fake.id),
            "transports": [transport.value for transport in fake.transports],
            "type": "public-key",
        }
    ]
    assert allowed_credentials_for(testclient, "nobody") == unknown
    assert allowed_credentials_for(testclient, "NoBody") == unknown
    assert allowed_credentials_for(testclient, "somebody") != unknown

    known = allowed_credentials_for(testclient, "user")
    assert known[0]["id"] == bytes_to_base64url(fido_credential.credential_id)
    assert set(known[0]) == set(unknown[0])


def test_unknown_login_authentication_fails(testclient):
    """Authentication with an unknown login fails like with an unknown passkey."""
    fake_id = bytes_to_base64url(get_fake_credential("nobody").id)
    allowed_credentials_for(testclient, "nobody")

    res = testclient.post_json("/auth/fido2", {"rawId": fake_id}, status=400)
    assert res.json == {"success": False, "error": "Credential not found"}
