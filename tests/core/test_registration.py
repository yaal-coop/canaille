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
    res.form["emails-0"] = "newuser@example.com"
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
        res.form["email"] = "foo@bar.com"
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
        email="foo@bar.com",
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
    res.form["email"] = "john@doe.com"
    res = res.form.submit()
    assert res.flashes == [
        (
            "success",
            "You will receive soon an email to continue the registration process.",
        )
    ]

    testclient.app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] = False
    res = testclient.get(url_for("core.account.join"))
    res.form["email"] = "john@doe.com"
    res = res.form.submit()
    assert res.flashes == []
    res.mustcontain("The email &#39;john@doe.com&#39; is already used")


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
    res.form["email"] = "foo@bar.com"
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


def test_registration_with_compromised_password(testclient, backend, foo_group):
    """Tests a nominal registration with compromised password."""
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    assert not backend.query(models.User, user_name="newuser")
    res = testclient.get(url_for("core.account.registration"), status=200)
    res.form["user_name"] = "newuser"
    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"
    res.form["family_name"] = "newuser"
    res.form["emails-0"] = "newuser@example.com"
    res = res.form.submit()
    res.mustcontain("This password is compromised.")

    user = backend.get(models.User, user_name="newuser")
    assert user is None


@mock.patch("requests.api.get")
def test_registration_with_compromised_password_request_api_failed_but_account_created(
    api_get, testclient, backend
):
    api_get.side_effect = mock.Mock(side_effect=Exception())
    current_app.config["CANAILLE"]["ACL"]["ADMIN"]["FILTER"] = {"groups": "admins"}
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    assert not backend.query(models.User, user_name="newuser")

    res = testclient.get(url_for("core.account.registration"), status=200)
    res.form["user_name"] = "newuser"
    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"
    res.form["family_name"] = "newuser"
    res.form["emails-0"] = "newuser@example.com"

    res = res.form.submit()

    assert (
        "error",
        "Password compromise investigation failed. Please contact the administrators.",
    ) in res.flashes
    assert ("success", "Your account has been created successfully.") in res.flashes

    user = backend.get(models.User, user_name="newuser")
    assert user
    backend.delete(user)


@mock.patch("requests.api.get")
def test_compromised_password_validator_with_failure_of_api_request_and_success_mail_to_admins_from_register_form_with_admin_group(
    api_get, testclient, backend, admins_group
):
    api_get.side_effect = mock.Mock(side_effect=Exception())
    current_app.config["CANAILLE"]["ACL"]["ADMIN"]["FILTER"] = {"groups": "admins"}
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    assert not backend.query(models.User, user_name="newuser")

    res = testclient.get(url_for("core.account.registration"), status=200)
    res.form["user_name"] = "newuser"
    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"
    res.form["family_name"] = "newuser"
    res.form["emails-0"] = "newuser@example.com"

    res = res.form.submit()

    assert (
        "error",
        "Password compromise investigation failed. Please contact the administrators.",
    ) in res.flashes
    assert (
        "success",
        "We have informed your administrator about the failure of the password compromise investigation.",
    ) in res.flashes
    assert ("success", "Your account has been created successfully.") in res.flashes

    user = backend.get(models.User, user_name="newuser")
    assert user
    backend.delete(user)


@mock.patch("requests.api.get")
def test_compromised_password_validator_with_failure_of_api_request_and_success_mail_to_admins_from_register_form_without_admin_group(
    api_get, testclient, backend, admins_group
):
    api_get.side_effect = mock.Mock(side_effect=Exception())
    current_app.config["CANAILLE"]["ACL"]["ADMIN"]["FILTER"] = None
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    assert not backend.query(models.User, user_name="newuser")

    res = testclient.get(url_for("core.account.registration"), status=200)
    res.form["user_name"] = "newuser"
    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"
    res.form["family_name"] = "newuser"
    res.form["emails-0"] = "newuser@example.com"

    res = res.form.submit()

    assert (
        "error",
        "Password compromise investigation failed. Please contact the administrators.",
    ) in res.flashes
    assert (
        "success",
        "We have informed your administrator about the failure of the password compromise investigation.",
    ) in res.flashes
    assert ("success", "Your account has been created successfully.") in res.flashes

    user = backend.get(models.User, user_name="newuser")
    assert user
    backend.delete(user)


@mock.patch("requests.api.get")
def test_compromised_password_validator_with_failure_of_api_request_and_fail_to_send_mail_to_admins_from_register_form(
    api_get, testclient, backend, admins_group
):
    api_get.side_effect = mock.Mock(side_effect=Exception())
    current_app.config["CANAILLE"]["ACL"]["ADMIN"]["FILTER"] = {"groups": "admins"}
    current_app.config["CANAILLE"]["SMTP"]["TLS"] = False
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    assert not backend.query(models.User, user_name="newuser")

    res = testclient.get(url_for("core.account.registration"), status=200)
    res.form["user_name"] = "newuser"
    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"
    res.form["family_name"] = "newuser"
    res.form["emails-0"] = "newuser@example.com"

    res = res.form.submit()

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
