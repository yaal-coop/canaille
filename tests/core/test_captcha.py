import datetime
import logging

import pytest
import time_machine
from flask import g
from flask import url_for

from canaille.app import models
from canaille.core.captcha import should_show_captcha_on_login
from canaille.core.captcha import verify_captcha
from canaille.core.endpoints.account import RegistrationPayload


def test_captcha_not_shown_when_disabled(testclient, user):
    """CAPTCHA should not appear when explicitly disabled."""
    testclient.app.config["CANAILLE"]["CAPTCHA_ENABLED"] = False
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 0

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    res.mustcontain(no="captcha")
    assert "captcha" not in res.form.fields


def test_captcha_enabled_always_shown_when_threshold_zero(testclient, user):
    """CAPTCHA should always be shown when CAPTCHA_FAILURE_THRESHOLD is 0."""
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 0

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    res.mustcontain("captcha")
    assert "captcha" in res.form.fields
    assert "captcha_token" in res.form.fields


def test_captcha_not_shown_before_threshold(testclient, user):
    """CAPTCHA should not be shown before reaching the failure threshold."""
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 3

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    res.mustcontain(no="captcha")
    assert "captcha" not in res.form.fields


def test_captcha_shown_after_threshold(testclient, user, caplog, backend):
    """CAPTCHA should appear after reaching the failure threshold."""
    if backend.__class__.__name__ == "LDAPBackend":
        pytest.skip("LDAP server timestamps cannot be controlled")

    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 3

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    for _ in range(3):
        res.form["password"] = "incorrect horse"
        res = res.form.submit(status=200)
        assert (
            "error",
            "Login failed. Please check your information.",
        ) in res.flashes

    res.mustcontain("captcha")
    assert "captcha" in res.form.fields
    assert "captcha_token" in res.form.fields


def test_captcha_validation_success(testclient, user, caplog):
    """Valid CAPTCHA should allow login to proceed."""
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 0

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    with testclient.session_transaction() as session:
        captcha_token = res.form["captcha_token"].value
        captcha_text = session.get(f"captcha_{captcha_token}")

    res.form["password"] = "correct horse battery staple"
    res.form["captcha"] = captcha_text
    res = res.form.submit(status=302)

    assert ("success", "Connection successful. Welcome Johnny") in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Successful authentication for user",
    ) in caplog.record_tuples


def test_captcha_validation_failure(testclient, user, caplog):
    """Invalid CAPTCHA should prevent login."""
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 0

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    res.form["password"] = "correct horse battery staple"
    res.form["captcha"] = "WRONG"
    res = res.form.submit(status=200)

    assert "Invalid security code" in res.text
    assert (
        "canaille",
        logging.SECURITY,
        "Successful authentication for user",
    ) not in caplog.record_tuples


def test_captcha_validation_empty(testclient, user):
    """Empty CAPTCHA should be rejected."""
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 0

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    res.form["password"] = "correct horse battery staple"
    res.form["captcha"] = ""
    res = res.form.submit(status=200)

    assert "This field is required." in res.text


def test_captcha_case_insensitive(testclient, user, caplog):
    """CAPTCHA should be case-insensitive."""
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 0

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    with testclient.session_transaction() as session:
        captcha_token = res.form["captcha_token"].value
        captcha_text = session.get(f"captcha_{captcha_token}")

    res.form["password"] = "correct horse battery staple"
    res.form["captcha"] = captcha_text.lower()
    res = res.form.submit(status=302)

    assert ("success", "Connection successful. Welcome Johnny") in res.flashes


def test_captcha_token_consumed_after_validation(testclient, user):
    """CAPTCHA token should be removed from session after validation."""
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 0

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    with testclient.session_transaction() as session:
        captcha_token = res.form["captcha_token"].value
        captcha_text = session.get(f"captcha_{captcha_token}")
        assert captcha_text is not None

    res.form["password"] = "correct horse battery staple"
    res.form["captcha"] = captcha_text
    res = res.form.submit(status=302)

    with testclient.session_transaction() as session:
        assert session.get(f"captcha_{captcha_token}") is None


def test_captcha_audio_endpoint(testclient, user):
    """Audio CAPTCHA endpoint should serve WAV data."""
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 0

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    captcha_token = res.form["captcha_token"].value

    audio_res = testclient.get(
        url_for("core.account.captcha_audio", token=captcha_token), status=200
    )
    assert audio_res.content_type == "audio/wav"
    assert len(audio_res.body) > 0


def test_captcha_audio_endpoint_invalid_token(testclient, user):
    """Audio CAPTCHA endpoint should return 404 for invalid token."""
    testclient.get(url_for("core.account.captcha_audio", token="invalid"), status=404)


def test_captcha_audio_etag_header(testclient, user):
    """Audio CAPTCHA endpoint should return ETag header."""
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 0

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    captcha_token = res.form["captcha_token"].value

    audio_res = testclient.get(
        url_for("core.account.captcha_audio", token=captcha_token), status=200
    )
    assert "ETag" in audio_res.headers
    assert audio_res.headers["ETag"] == f'"{captcha_token}"'
    assert "Cache-Control" in audio_res.headers
    assert "private" in audio_res.headers["Cache-Control"]


def test_captcha_audio_if_none_match(testclient, user):
    """Audio CAPTCHA endpoint should return 304 for matching ETag."""
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 0

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    captcha_token = res.form["captcha_token"].value
    etag = f'"{captcha_token}"'

    audio_res = testclient.get(
        url_for("core.account.captcha_audio", token=captcha_token),
        headers={"If-None-Match": etag},
        status=304,
    )
    assert len(audio_res.body) == 0


def test_captcha_on_registration_always_shown(testclient, backend, foo_group):
    """CAPTCHA should always be shown on registration form when enabled."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 999

    res = testclient.get(url_for("core.account.registration"), status=200)

    res.mustcontain("captcha")
    assert "captcha" in res.form.fields
    assert "captcha_token" in res.form.fields


def test_captcha_on_registration_validation_success(testclient, backend, foo_group):
    """Valid CAPTCHA should allow registration to proceed."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    res = testclient.get(url_for("core.account.registration"), status=200)

    with testclient.session_transaction() as session:
        captcha_token = res.form["captcha_token"].value
        captcha_text = session.get(f"captcha_{captcha_token}")

    res.form["user_name"] = "newuser"
    res.form["password1"] = "i'm a little pea"
    res.form["password2"] = "i'm a little pea"
    res.form["family_name"] = "newuser"
    res.form["emails-0"] = "newuser@example.test"
    res.form["captcha"] = captcha_text
    res = res.form.submit()

    assert ("success", "Your account has been created successfully.") in res.flashes

    user = backend.get(models.User, user_name="newuser")
    assert user
    backend.delete(user)


def test_captcha_on_registration_validation_failure(testclient, backend, foo_group):
    """Invalid CAPTCHA should prevent registration."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    res = testclient.get(url_for("core.account.registration"), status=200)

    res.form["user_name"] = "newuser"
    res.form["password1"] = "i'm a little pea"
    res.form["password2"] = "i'm a little pea"
    res.form["family_name"] = "newuser"
    res.form["emails-0"] = "newuser@example.test"
    res.form["captcha"] = "WRONG"
    res = res.form.submit(status=200)

    assert "Invalid security code" in res.text
    assert not backend.get(models.User, user_name="newuser")


def test_captcha_not_shown_on_profile_creation(testclient, logged_moderator):
    """CAPTCHA should not be shown on admin profile creation form."""
    res = testclient.get("/profile", status=200)

    res.mustcontain(no="captcha")
    assert "captcha" not in res.form.fields


def test_captcha_with_email_registration(testclient, backend, smtpd, foo_group):
    """CAPTCHA should work with email-validated registration (on /join page)."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True

    with time_machine.travel("2020-01-01 02:00:00+00:00", tick=False):
        res = testclient.get(url_for("core.account.join"))

        res.mustcontain("captcha")
        assert "captcha" in res.form.fields

        with testclient.session_transaction() as session:
            captcha_token = res.form["captcha_token"].value
            captcha_text = session.get(f"captcha_{captcha_token}")

        res.form["email"] = "foo@bar.test"
        res.form["captcha"] = captcha_text
        res = res.form.submit()

    payload = RegistrationPayload(
        creation_date_isoformat="2020-01-01T02:00:00+00:00",
        user_name="",
        user_name_editable=True,
        email="foo@bar.test",
        groups=[],
    )
    registration_url = url_for(
        "core.account.registration",
        data=payload.b64(),
        hash=payload.build_hash(),
        _external=True,
    )

    with time_machine.travel("2020-01-01 02:01:00+00:00", tick=False):
        res = testclient.get(registration_url, status=200)

        res.mustcontain(no="captcha")
        assert "captcha" not in res.form.fields

        res.form["user_name"] = "newuser"
        res.form["password1"] = "i'm a little pea"
        res.form["password2"] = "i'm a little pea"
        res.form["family_name"] = "newuser"
        res = res.form.submit()

    assert res.flashes == [
        ("success", "Your account has been created successfully."),
    ]

    user = backend.get(models.User, user_name="newuser")
    assert user
    backend.delete(user)


def test_captcha_refresh_on_join(testclient, backend, smtpd):
    """CAPTCHA refresh should work on join page."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True

    res = testclient.get(url_for("core.account.join"))
    old_token = res.form["captcha_token"].value

    with testclient.session_transaction() as session:
        assert f"captcha_{old_token}" in session

    res = res.form.submit(name="action", value="refresh_captcha")

    new_token = res.form["captcha_token"].value
    assert new_token != old_token

    with testclient.session_transaction() as session:
        assert f"captcha_{old_token}" not in session
        assert f"captcha_{new_token}" in session


def test_captcha_refresh_on_join_without_old_token(testclient, backend, smtpd):
    """CAPTCHA refresh should work even without old token."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True

    res = testclient.get(url_for("core.account.join"))
    res.form["captcha_token"].value = ""
    res = res.form.submit(name="action", value="refresh_captcha")

    new_token = res.form["captcha_token"].value
    assert new_token


def test_captcha_refresh_on_registration(testclient, backend):
    """CAPTCHA refresh should work on registration page."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    res = testclient.get(url_for("core.account.registration"))
    old_token = res.form["captcha_token"].value

    with testclient.session_transaction() as session:
        assert f"captcha_{old_token}" in session

    res = res.form.submit(name="action", value="refresh_captcha")

    new_token = res.form["captcha_token"].value
    assert new_token != old_token

    with testclient.session_transaction() as session:
        assert f"captcha_{old_token}" not in session
        assert f"captcha_{new_token}" in session


def test_captcha_refresh_on_registration_without_old_token(testclient, backend):
    """CAPTCHA refresh should work even without old token."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    res = testclient.get(url_for("core.account.registration"))
    res.form["captcha_token"].value = ""
    res = res.form.submit(name="action", value="refresh_captcha")

    new_token = res.form["captcha_token"].value
    assert new_token


def test_captcha_length_configuration(testclient, user):
    """CAPTCHA length should be configurable."""
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 0
    testclient.app.config["CANAILLE"]["CAPTCHA_LENGTH"] = 8

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    with testclient.session_transaction() as session:
        captcha_token = res.form["captcha_token"].value
        captcha_text = session.get(f"captcha_{captcha_token}")
        assert len(captcha_text) == 8


def test_captcha_regenerated_on_validation_failure(testclient, user):
    """New CAPTCHA should be generated after validation failure."""
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 0

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    old_token = res.form["captcha_token"].value

    res.form["password"] = "correct horse battery staple"
    res.form["captcha"] = "WRONG"
    res = res.form.submit(status=200)

    new_token = res.form["captcha_token"].value
    assert old_token != new_token

    with testclient.session_transaction() as session:
        assert session.get(f"captcha_{old_token}") is None
        assert session.get(f"captcha_{new_token}") is not None


def test_captcha_whitespace_trimmed(testclient, user, caplog):
    """CAPTCHA should accept answers with leading/trailing whitespace."""
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 0

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    with testclient.session_transaction() as session:
        captcha_token = res.form["captcha_token"].value
        captcha_text = session.get(f"captcha_{captcha_token}")

    res.form["password"] = "correct horse battery staple"
    res.form["captcha"] = f"  {captcha_text}  "
    res = res.form.submit(status=302)

    assert ("success", "Connection successful. Welcome Johnny") in res.flashes


def test_captcha_persists_until_successful_login(testclient, user, caplog, backend):
    """CAPTCHA persists after threshold is reached, regardless of time elapsed."""
    if backend.__class__.__name__ == "LDAPBackend":
        pytest.skip("LDAP server timestamps cannot be controlled")

    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 2

    with time_machine.travel(
        datetime.datetime.now(datetime.timezone.utc), tick=False
    ) as traveller:
        res = testclient.get("/login", status=200)
        res.form["login"] = "user"
        res = res.form.submit(status=302).follow()

        for _ in range(2):
            res.form["password"] = "incorrect"
            res = res.form.submit(status=200)

        res.mustcontain("captcha")

        traveller.shift(datetime.timedelta(minutes=11))

        res = testclient.get("/login", status=200)
        res.form["login"] = "user"
        res = res.form.submit(status=302).follow()

        res.mustcontain("captcha")


def test_captcha_failure_increments_counter(testclient, user, backend, caplog):
    """Failed login with CAPTCHA should still increment failure counter."""
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 0

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    initial_failures = len(user.password_failure_timestamps or [])

    with testclient.session_transaction() as session:
        captcha_token = res.form["captcha_token"].value
        captcha_text = session.get(f"captcha_{captcha_token}")

    res.form["password"] = "wrong password"
    res.form["captcha"] = captcha_text
    res = res.form.submit(status=200)

    user = backend.get(models.User, user_name="user")
    assert len(user.password_failure_timestamps or []) > initial_failures


def test_verify_captcha_empty_token(testclient):
    """verify_captcha should return False for empty token."""
    assert verify_captcha("", "response") is False
    assert verify_captcha(None, "response") is False


def test_verify_captcha_empty_response(testclient):
    """verify_captcha should return False for empty response."""
    assert verify_captcha("token", "") is False
    assert verify_captcha("token", None) is False


def test_verify_captcha_invalid_token(testclient):
    """verify_captcha should return False for invalid token."""
    assert verify_captcha("nonexistent_token", "response") is False


def test_should_show_captcha_no_auth(testclient):
    """should_show_captcha_on_login should return False when no auth session."""
    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 3

    with testclient.app.test_request_context():
        g.auth = None
        assert should_show_captcha_on_login() is False


def test_captcha_failure_counter_reset_after_successful_login(
    testclient, user, backend, caplog
):
    """Failed login counter should be reset after successful login."""
    if backend.__class__.__name__ == "LDAPBackend":
        pytest.skip("LDAP server timestamps cannot be controlled")

    testclient.app.config["CANAILLE"]["CAPTCHA_FAILURE_THRESHOLD"] = 2

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    for _ in range(2):
        res.form["password"] = "incorrect"
        res = res.form.submit(status=200)

    res.mustcontain("captcha")

    with testclient.session_transaction() as session:
        captcha_token = res.form["captcha_token"].value
        captcha_text = session.get(f"captcha_{captcha_token}")

    res.form["password"] = "correct horse battery staple"
    res.form["captcha"] = captcha_text
    res = res.form.submit(status=302)

    assert ("success", "Connection successful. Welcome Johnny") in res.flashes

    user = backend.get(models.User, user_name="user")
    assert user.password_failure_timestamps == []

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=302).follow()

    res.mustcontain(no="captcha")
    assert "captcha" not in res.form.fields
