import logging
from unittest import mock

import time_machine
from flask import current_app
from flask import url_for

from canaille.app import models
from canaille.core.endpoints.account import RegistrationPayload


def test_registration_without_email_validation(testclient, backend, foo_group):
    """Tests a nominal registration without email validation."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    assert not backend.query(models.User, user_name="newuser")
    res = testclient.get(url_for("core.account.registration"), status=200)
    res.form["user_name"] = "newuser"
    res.form["password1"] = "i'm a little pea"
    res.form["password2"] = "i'm a little pea"
    res.form["family_name"] = "newuser"
    res.form["emails-0"] = "newuser@example.test"
    res = res.form.submit()
    assert ("success", "Your account has been created successfully.") in res.flashes

    user = backend.get(models.User, user_name="newuser")
    assert user
    backend.delete(user)


def test_registration_failure_with_different_passwords_and_too_short_password(
    testclient, backend, foo_group
):
    """Tests a nominal registration without email validation but with a wrong confirmation password and a too short password."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    assert not backend.query(models.User, user_name="newuser")
    res = testclient.get(url_for("core.account.registration"), status=200)
    res.form["user_name"] = "newuser"
    res.form["password1"] = "123"
    res.form["password2"] = "123"
    res.form["family_name"] = "newuser"
    res.form["emails-0"] = "newuser@example.test"
    res = res.form.submit()
    assert ("error", "User account creation failed.") in res.flashes
    res.mustcontain("Field must be at least 8 characters long.")

    res.form["password1"] = "i'm a little pea"
    res.form["password2"] = "i'm not a little pea"
    res = res.form.submit()
    res.mustcontain("Password and confirmation do not match.")
    res.mustcontain('data-percent="100"')

    res.form["password1"] = "i'm a little pea"
    res.form["password2"] = "i'm a little pea"
    res = res.form.submit()
    assert ("success", "Your account has been created successfully.") in res.flashes

    user = backend.get(models.User, user_name="newuser")
    assert user
    backend.delete(user)


def test_registration_with_email_validation(testclient, backend, smtpd, foo_group):
    """Tests a nominal registration with email validation."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True

    with time_machine.travel("2020-01-01 02:00:00+00:00", tick=False):
        res = testclient.get(url_for("core.account.join"))
        res.form["email"] = "foo@bar.test"
        res = res.form.submit()

    assert res.flashes == [
        (
            "success",
            "You will receive soon an email to continue the registration process.",
        )
    ]
    assert len(smtpd.messages) == 1

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
    text_mail = smtpd.messages[0].get_payload()[0].get_payload(decode=True).decode()
    assert registration_url in text_mail

    assert not backend.query(models.User, user_name="newuser")
    with time_machine.travel("2020-01-01 02:01:00+00:00", tick=False):
        res = testclient.get(registration_url, status=200)
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


def test_registration_with_email_already_taken(
    testclient, backend, smtpd, user, foo_group
):
    """Be sure to not leak email existence if HIDE_INVALID_LOGINS is true."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True

    testclient.app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] = True
    res = testclient.get(url_for("core.account.join"))
    res.form["email"] = "john@doe.test"
    res = res.form.submit()
    assert res.flashes == [
        (
            "success",
            "You will receive soon an email to continue the registration process.",
        )
    ]

    testclient.app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] = False
    res = testclient.get(url_for("core.account.join"))
    res.form["email"] = "john@doe.test"
    res = res.form.submit()
    assert res.flashes == []
    res.mustcontain("The email &#39;john@doe.test&#39; is already used")


def test_registration_with_email_validation_needs_a_valid_link(
    testclient, backend, smtpd, foo_group
):
    """Tests a nominal registration without email validation."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.get(url_for("core.account.registration"), status=403)


def test_join_page_registration_disabled(testclient, backend, smtpd, foo_group):
    """The join page should not be available if registration is disabled."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = False
    testclient.get(url_for("core.account.join"), status=404)


def test_join_page_email_confirmation_disabled(testclient, backend, smtpd, foo_group):
    """The join page should directly redirect to the registration page if email
    confirmation is disabled."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False
    res = testclient.get(url_for("core.account.join"), status=302)
    assert res.location == url_for("core.account.registration")


def test_join_page_already_logged_in(testclient, backend, logged_user, foo_group):
    """The join page should not be accessible for logged users."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.get(url_for("core.account.join"), status=403)


@mock.patch("smtplib.SMTP")
def test_registration_mail_error(SMTP, testclient, backend, smtpd, foo_group):
    """Display an error message if the registration mail could not be sent."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    SMTP.side_effect = mock.Mock(side_effect=OSError("unit test mail error"))
    res = testclient.get(url_for("core.account.join"))
    res.form["email"] = "foo@bar.test"
    res = res.form.submit(expect_errors=True)

    assert res.flashes == [
        (
            "error",
            "An error happened while sending your registration mail. "
            "Please try again in a few minutes. "
            "If this still happens, please contact the administrators.",
        )
    ]
    assert len(smtpd.messages) == 0


@mock.patch("requests.api.get")
def test_registration_with_compromised_password(api_get, testclient, backend):
    """Tests a nominal registration with compromised password."""
    current_app.config["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = True
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    # This content simulates a result from the hibp api containing the suffixes of the following password hashes: 'password', '987654321', 'correct horse battery staple', 'zxcvbn123', 'azertyuiop123'
    class Response:
        content = b"1E4C9B93F3F0682250B6CF8331B7EE68FD8:3\r\nCAA6D483CC3887DCE9D1B8EB91408F1EA7A:3\r\nAD6438836DBE526AA231ABDE2D0EEF74D42:3\r\n8289894DDB6317178960AB5AE98B81BBF97:1\r\n5FF0B6F9EAC40D5CA7B4DAA7B64F0E6F4AA:2\r\n"

    api_get.return_value = Response

    assert not backend.query(models.User, user_name="newuser")
    res = testclient.get(url_for("core.account.registration"), status=200)
    res.form["user_name"] = "newuser"
    res.form["password1"] = "987654321"
    res.form["password2"] = "987654321"
    res.form["family_name"] = "newuser"
    res.form["emails-0"] = "newuser@example.test"
    res = res.form.submit()
    res.mustcontain(
        "This password appears on public compromission databases and is not secure."
    )

    user = backend.get(models.User, user_name="newuser")
    assert user is None


@mock.patch("requests.api.get")
def test_registration_with_compromised_password_request_api_failed_but_account_created(
    api_get, testclient, backend, caplog
):
    current_app.config["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = True
    api_get.side_effect = mock.Mock(side_effect=Exception())
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    assert not backend.query(models.User, user_name="newuser")

    res = testclient.get(url_for("core.account.registration"), status=200)
    res.form["user_name"] = "newuser"
    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"
    res.form["family_name"] = "newuser"
    res.form["emails-0"] = "newuser@example.test"

    res = res.form.submit()

    assert (
        "canaille",
        logging.ERROR,
        "Password compromise investigation failed on HIBP API.",
    ) in caplog.record_tuples
    assert (
        "error",
        "Password compromise investigation failed. Please contact the administrators.",
    ) in res.flashes
    assert ("success", "Your account has been created successfully.") in res.flashes

    user = backend.get(models.User, user_name="newuser")
    assert user
    backend.delete(user)


@mock.patch("requests.api.get")
def test_compromised_password_validator_with_failure_of_api_request_and_success_mail_to_admin_from_register_form(
    api_get, testclient, backend, caplog, smtpd
):
    current_app.config["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = True
    api_get.side_effect = mock.Mock(side_effect=Exception())
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    assert not backend.query(models.User, user_name="newuser")

    res = testclient.get(url_for("core.account.registration"), status=200)
    res.form["user_name"] = "newuser"
    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"
    res.form["family_name"] = "newuser"
    res.form["emails-0"] = "newuser@example.test"

    res = res.form.submit()

    assert (
        "canaille",
        logging.ERROR,
        "Password compromise investigation failed on HIBP API.",
    ) in caplog.record_tuples
    assert (
        "error",
        "Password compromise investigation failed. Please contact the administrators.",
    ) in res.flashes
    assert (
        "info",
        "We have informed your administrator about the failure of the password compromise investigation.",
    ) in res.flashes
    assert ("success", "Your account has been created successfully.") in res.flashes
    assert len(smtpd.messages) == 1

    user = backend.get(models.User, user_name="newuser")
    assert user
    backend.delete(user)


@mock.patch("requests.api.get")
def test_compromised_password_validator_with_failure_of_api_request_and_fail_to_send_mail_to_admin_from_register_form(
    api_get, testclient, backend, caplog
):
    current_app.config["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = True
    api_get.side_effect = mock.Mock(side_effect=Exception())
    current_app.config["CANAILLE"]["SMTP"]["TLS"] = False
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    assert not backend.query(models.User, user_name="newuser")

    res = testclient.get(url_for("core.account.registration"), status=200)
    res.form["user_name"] = "newuser"
    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"
    res.form["family_name"] = "newuser"
    res.form["emails-0"] = "newuser@example.test"

    res = res.form.submit()

    assert (
        "canaille",
        logging.ERROR,
        "Password compromise investigation failed on HIBP API.",
    ) in caplog.record_tuples
    assert (
        "error",
        "Password compromise investigation failed. Please contact the administrators.",
    ) in res.flashes
    assert (
        "error",
        "An error occurred while communicating the incident to the administrators. "
        "Please update your password as soon as possible. "
        "If this still happens, please contact the administrators.",
    ) in res.flashes
    assert ("success", "Your account has been created successfully.") in res.flashes

    user = backend.get(models.User, user_name="newuser")
    assert user
    backend.delete(user)


@mock.patch("requests.api.get")
def test_compromised_password_validator_with_failure_of_api_request_without_smtp_from_register_form(
    api_get, testclient, backend, caplog
):
    current_app.config["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = True
    api_get.side_effect = mock.Mock(side_effect=Exception())
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    assert not backend.query(models.User, user_name="newuser")

    current_app.config["CANAILLE"]["SMTP"] = None

    res = testclient.get(url_for("core.account.registration"), status=200)
    res.form["user_name"] = "newuser"
    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"
    res.form["family_name"] = "newuser"
    res.form["emails-0"] = "newuser@example.test"

    res = res.form.submit()

    assert (
        "canaille",
        logging.ERROR,
        "Password compromise investigation failed on HIBP API.",
    ) in caplog.record_tuples
    assert (
        "error",
        "Password compromise investigation failed. Please contact the administrators.",
    ) not in res.flashes

    user = backend.get(models.User, user_name="newuser")
    assert user
    backend.delete(user)


@mock.patch("requests.api.get")
def test_compromised_password_validator_with_failure_of_api_request_without_admin_email_from_register_form(
    api_get, testclient, backend, caplog
):
    current_app.config["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = True
    api_get.side_effect = mock.Mock(side_effect=Exception())
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    assert not backend.query(models.User, user_name="newuser")

    current_app.config["CANAILLE"]["ADMIN_EMAIL"] = None

    res = testclient.get(url_for("core.account.registration"), status=200)
    res.form["user_name"] = "newuser"
    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"
    res.form["family_name"] = "newuser"
    res.form["emails-0"] = "newuser@example.test"

    res = res.form.submit()

    assert (
        "canaille",
        logging.ERROR,
        "Password compromise investigation failed on HIBP API.",
    ) in caplog.record_tuples
    assert (
        "error",
        "Password compromise investigation failed. Please contact the administrators.",
    ) not in res.flashes

    user = backend.get(models.User, user_name="newuser")
    assert user
    backend.delete(user)
