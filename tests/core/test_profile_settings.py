import datetime
import logging
from unittest import mock

import pytest
from flask import current_app
from flask import g

from canaille.app import models


def test_edition(testclient, logged_user, admin, foo_group, bar_group, backend):
    res = testclient.get("/profile/user/settings", status=200)
    assert set(res.form["groups"].options) == {
        (foo_group.id, True, "foo"),
        (bar_group.id, False, "bar"),
    }
    assert logged_user.groups == [foo_group]
    assert foo_group.members == [logged_user]
    assert bar_group.members == [admin]
    assert "readonly" in res.form["groups"].attrs
    assert "readonly" in res.form["user_name"].attrs

    res.form["user_name"] = "toto"
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("error", "Profile edition failed.")]
    backend.reload(logged_user)

    assert logged_user.user_name == "user"

    backend.reload(foo_group)
    backend.reload(bar_group)
    assert logged_user.groups == [foo_group]
    assert foo_group.members == [logged_user]
    assert bar_group.members == [admin]
    assert "readonly" in res.form["groups"].attrs
    assert "readonly" in res.form["user_name"].attrs

    res = testclient.get("/profile/user/settings", status=200)
    res.form["user_name"] = "user"
    res.form["password1"] = "i'm a little pea"
    res.form["password2"] = "i'm a little pea"
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("success", "Profile updated successfully.")]

    backend.reload(logged_user)
    assert backend.check_user_password(logged_user, "i'm a little pea")[0]

    logged_user.user_name = "user"
    backend.save(logged_user)


def test_group_removal(testclient, logged_admin, user, foo_group, backend):
    """Tests that one can remove a group from a user."""
    foo_group.members = [user, logged_admin]
    backend.save(foo_group)
    backend.reload(user)
    assert foo_group in user.groups

    res = testclient.get("/profile/user/settings", status=200)
    res.form["groups"] = []
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("success", "Profile updated successfully.")]

    backend.reload(user)
    assert foo_group not in user.groups

    backend.reload(foo_group)
    backend.reload(logged_admin)
    assert foo_group.members == [logged_admin]


def test_empty_group_removal(testclient, logged_admin, user, foo_group, backend):
    """Tests that one cannot remove a group from a user, when was the last
    person in the group.

    This is because LDAP groups cannot be empty because
    groupOfNames.member is a MUST attribute.
    https://www.rfc-editor.org/rfc/rfc2256.html#section-7.10
    """
    assert foo_group in user.groups

    res = testclient.get("/profile/user/settings", status=200)
    res.form["groups"] = []
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("error", "Profile edition failed.")]

    res.mustcontain(
        "The group &#39;foo&#39; cannot be removed, because it must have at least one user left."
    )

    backend.reload(user)
    assert foo_group in user.groups


def test_profile_settings_edition_dynamic_validation(testclient, logged_admin):
    res = testclient.get("/profile/admin/settings")
    res = testclient.post(
        "/profile/admin/settings",
        {
            "csrf_token": res.form["csrf_token"].value,
            "password1": "short",
        },
        headers={
            "HX-Request": "true",
            "HX-Trigger-Name": "password1",
        },
    )
    res.mustcontain("Field must be at least 8 characters long.")


def test_profile_settings_minimum_password_length_validation(testclient, logged_user):
    """Tests minimum length of password defined in configuration."""

    def with_different_values(password, length):
        current_app.config["CANAILLE"]["MIN_PASSWORD_LENGTH"] = length
        res = testclient.get("/profile/user/settings")
        res = testclient.post(
            "/profile/user/settings",
            {
                "csrf_token": res.form["csrf_token"].value,
                "password1": password,
            },
            headers={
                "HX-Request": "true",
                "HX-Trigger-Name": "password1",
            },
        )
        res.mustcontain(f"Field must be at least {length} characters long.")

    with_different_values("short", 8)
    with_different_values("aa", 3)
    with_different_values("1234567890123456789", 20)


def test_profile_settings_too_long_password(testclient, logged_user):
    """Tests maximum length of password."""

    def with_different_values(password, length, message):
        current_app.config["CANAILLE"]["MAX_PASSWORD_LENGTH"] = length
        res = testclient.get("/profile/user/settings")
        res = testclient.post(
            "/profile/user/settings",
            {
                "csrf_token": res.form["csrf_token"].value,
                "password1": password,
            },
            headers={
                "HX-Request": "true",
                "HX-Trigger-Name": "password1",
            },
        )
        res.mustcontain(message)

    with_different_values(
        "a" * 1001, 1000, "Field cannot be longer than 1000 characters."
    )
    with_different_values("a1!A" * 250, 1000, 'data-percent="25"')
    with_different_values("a" * 501, 500, "Field cannot be longer than 500 characters.")
    with_different_values("a1!A" * 125, 500, 'data-percent="25"')
    with_different_values("a" * 4097, 0, "Field cannot be longer than 4096 characters.")
    with_different_values(
        "a" * 4097, None, "Field cannot be longer than 4096 characters."
    )
    with_different_values(
        "a" * 4097, 5000, "Field cannot be longer than 4096 characters."
    )


@mock.patch("requests.api.get")
def test_profile_settings_compromised_password(api_get, testclient, logged_user):
    current_app.config["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = True
    """Tests if password is compromised."""

    # This content simulates a result from the hibp api containing the suffixes of the following password hashes: 'password', '987654321', 'correct horse battery staple', 'zxcvbn123', 'azertyuiop123'
    class Response:
        content = b"1E4C9B93F3F0682250B6CF8331B7EE68FD8:3\r\nCAA6D483CC3887DCE9D1B8EB91408F1EA7A:3\r\nAD6438836DBE526AA231ABDE2D0EEF74D42:3\r\n8289894DDB6317178960AB5AE98B81BBF97:1\r\n5FF0B6F9EAC40D5CA7B4DAA7B64F0E6F4AA:2\r\n"

    api_get.return_value = Response

    def with_different_values(password, message):
        res = testclient.get("/profile/user/settings")
        res = testclient.post(
            "/profile/user/settings",
            {
                "csrf_token": res.form["csrf_token"].value,
                "password1": password,
            },
            headers={
                "HX-Request": "true",
                "HX-Trigger-Name": "password1",
            },
        )
        res.mustcontain(message)

    with_different_values(
        "password",
        "This password appears on public compromission databases and is not secure.",
    )
    with_different_values(
        "azertyuiop123",
        "This password appears on public compromission databases and is not secure.",
    )
    with_different_values("a" * 1000, 'data-percent="25"')
    with_different_values("i'm a little pea", 'data-percent="100"')


@mock.patch("requests.api.get")
def test_profile_settings_compromised_password_request_api_failed_but_password_updated(
    api_get, testclient, logged_user, backend, caplog
):
    current_app.config["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = True
    api_get.side_effect = mock.Mock(side_effect=Exception())

    current_app.config["CANAILLE"]["ACL"]["ADMIN"]["FILTER"] = {"groups": "admins"}

    res = testclient.get("/profile/user/settings", status=200)

    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"

    res = res.form.submit(name="action", value="edit-settings")

    assert (
        "canaille",
        logging.ERROR,
        "Password compromise investigation failed on HIBP API.",
    ) in caplog.record_tuples
    assert (
        "error",
        "Password compromise investigation failed. Please contact the administrators.",
    ) in res.flashes
    assert ("success", "Profile updated successfully.") in res.flashes

    backend.reload(logged_user)

    assert logged_user.user_name == "user"
    assert backend.check_user_password(logged_user, "123456789")[0]


@mock.patch("requests.api.get")
def test_compromised_password_validator_with_failure_of_api_request_and_success_mail_to_admin_from_settings_form(
    api_get, testclient, backend, user, logged_user, caplog, smtpd
):
    current_app.config["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = True
    api_get.side_effect = mock.Mock(side_effect=Exception())

    res = testclient.get("/profile/user/settings", status=200)

    res.form.user = user
    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"

    res = res.form.submit(name="action", value="edit-settings")

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
    assert ("success", "Profile updated successfully.") in res.flashes
    assert len(smtpd.messages) == 1


@mock.patch("requests.api.get")
def test_compromised_password_validator_with_failure_of_api_request_and_fail_to_send_mail_to_admin_from_settings_form(
    api_get, testclient, backend, user, logged_user, caplog, smtpd
):
    current_app.config["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = True
    api_get.side_effect = mock.Mock(side_effect=Exception())
    current_app.config["CANAILLE"]["SMTP"]["TLS"] = False

    res = testclient.get("/profile/user/settings", status=200)
    res.form.user = user
    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"

    res = res.form.submit(name="action", value="edit-settings")

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
    assert ("success", "Profile updated successfully.") in res.flashes
    assert len(smtpd.messages) == 0


@mock.patch("requests.api.get")
def test_compromised_password_validator_with_failure_of_api_request_without_smtp_or_without_admin_email_from_settings_form(
    api_get, testclient, backend, user, logged_user, caplog
):
    def without_smtp_or_without_admin_email(smtp, mail):
        current_app.config["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = True
        api_get.side_effect = mock.Mock(side_effect=Exception())
        current_app.config["CANAILLE"]["SMTP"] = smtp
        current_app.config["CANAILLE"]["ADMIN_EMAIL"] = mail

        res = testclient.get("/profile/user/settings", status=200)
        res.form.user = user
        res.form["password1"] = "123456789"
        res.form["password2"] = "123456789"

        res = res.form.submit(name="action", value="edit-settings")

        assert (
            "canaille",
            logging.ERROR,
            "Password compromise investigation failed on HIBP API.",
        ) in caplog.record_tuples
        assert (
            "error",
            "Password compromise investigation failed. Please contact the administrators.",
        ) not in res.flashes

    without_smtp_or_without_admin_email(
        None, current_app.config["CANAILLE"]["ADMIN_EMAIL"]
    )
    without_smtp_or_without_admin_email(current_app.config["CANAILLE"]["SMTP"], None)


def test_edition_without_groups(
    testclient,
    logged_user,
    admin,
    backend,
):
    res = testclient.get("/profile/user/settings", status=200)
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["READ"] = []

    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("success", "Profile updated successfully.")]
    res = res.follow()

    backend.reload(logged_user)

    assert logged_user.user_name == "user"
    assert backend.check_user_password(logged_user, "correct horse battery staple")[0]

    logged_user.user_name = "user"
    backend.save(logged_user)


def test_password_change(testclient, logged_user, backend, caplog):
    res = testclient.get("/profile/user/settings", status=200)

    res.form["password1"] = "i'm a little pea"
    res.form["password2"] = "i'm a little pea"

    res = res.form.submit(name="action", value="edit-settings").follow()

    backend.reload(logged_user)
    assert backend.check_user_password(logged_user, "i'm a little pea")[0]

    res = testclient.get("/profile/user/settings", status=200)

    res.form["password1"] = "i'm a little chickpea"
    res.form["password2"] = "i'm a little chickpea"

    res = res.form.submit(name="action", value="edit-settings")
    assert ("success", "Profile updated successfully.") in res.flashes

    assert (
        "canaille",
        logging.SECURITY,
        "Changed password in settings for user from unknown IP",
    ) in caplog.record_tuples

    res = res.follow()

    backend.reload(logged_user)
    assert backend.check_user_password(logged_user, "i'm a little chickpea")[0]


def test_password_change_fail(testclient, logged_user, backend):
    res = testclient.get("/profile/user/settings", status=200)

    res.form["password1"] = "i'm a little pea"
    res.form["password2"] = "i'm a little chickpea"

    res = res.form.submit(name="action", value="edit-settings", status=200)

    backend.reload(logged_user)
    assert backend.check_user_password(logged_user, "correct horse battery staple")[0]

    res = testclient.get("/profile/user/settings", status=200)

    res.form["password1"] = "i'm a little pea"
    res.form["password2"] = ""

    res = res.form.submit(name="action", value="edit-settings", status=200)

    backend.reload(logged_user)
    assert backend.check_user_password(logged_user, "correct horse battery staple")[0]


def test_password_initialization_mail(smtpd, testclient, backend, logged_admin):
    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.test"],
    )
    backend.save(u)

    res = testclient.get("/profile/temp/settings", status=200)
    res.mustcontain("This user does not have a password yet")
    res.mustcontain("Send")

    res = res.form.submit(name="action", value="password-initialization-mail")
    assert (
        "success",
        "A password initialization link has been sent at the user email address. "
        "It should be received within a few minutes.",
    ) in res.flashes
    assert len(smtpd.messages) == 1
    assert smtpd.messages[0]["X-RcptTo"] == "john@doe.test"

    backend.reload(u)
    u.password = "correct horse battery staple"
    backend.save(u)

    res = testclient.get("/profile/temp/settings", status=200)
    res.mustcontain(no="This user does not have a password yet")

    backend.delete(u)


@mock.patch("smtplib.SMTP")
def test_password_initialization_mail_send_fail(
    SMTP, smtpd, testclient, backend, logged_admin
):
    SMTP.side_effect = mock.Mock(side_effect=OSError("unit test mail error"))
    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.test"],
    )
    backend.save(u)

    res = testclient.get("/profile/temp/settings", status=200)
    res.mustcontain("This user does not have a password yet")
    res.mustcontain("Send")

    res = res.form.submit(
        name="action", value="password-initialization-mail", expect_errors=True
    )
    assert (
        "success",
        "A password initialization link has been sent at the user email address. "
        "It should be received within a few minutes.",
    ) not in res.flashes
    assert ("error", "Could not send the password initialization email") in res.flashes
    assert len(smtpd.messages) == 0

    backend.delete(u)


def test_password_initialization_invalid_user(smtpd, testclient, backend, logged_admin):
    assert len(smtpd.messages) == 0
    res = testclient.get("/profile/admin/settings")
    testclient.post(
        "/profile/invalid/settings",
        {
            "action": "password-initialization-mail",
            "csrf_token": res.form["csrf_token"].value,
        },
        status=404,
    )
    assert len(smtpd.messages) == 0


def test_password_reset_invalid_user(smtpd, testclient, backend, logged_admin):
    assert len(smtpd.messages) == 0
    res = testclient.get("/profile/admin/settings")
    testclient.post(
        "/profile/invalid/settings",
        {"action": "password-reset-mail", "csrf_token": res.form["csrf_token"].value},
        status=404,
    )
    assert len(smtpd.messages) == 0


def test_delete_invalid_user(testclient, backend, logged_admin):
    res = testclient.get("/profile/admin/settings")
    testclient.post(
        "/profile/invalid/settings",
        {"action": "delete", "csrf_token": res.form["csrf_token"].value},
        status=404,
    )


def test_impersonate_invalid_user(testclient, backend, logged_admin):
    testclient.get("/impersonate/invalid", status=404)


def test_impersonate_locked_user(testclient, backend, logged_admin, user):
    res = testclient.get("/profile/user/settings")
    res.mustcontain("Impersonate")

    user.lock_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=1
    )
    backend.save(user)

    assert user.locked
    res = testclient.get("/profile/user/settings")
    res.mustcontain(no="Impersonate")

    res = testclient.get("/impersonate/user", status=403)
    res.mustcontain("Locked users cannot be impersonated.")


def test_invalid_form_request(testclient, logged_admin):
    res = testclient.get("/profile/admin/settings")
    res = res.form.submit(name="action", value="invalid-action", status=400)


def test_password_reset_email(smtpd, testclient, backend, logged_admin):
    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.test"],
        password="correct horse battery staple",
    )
    backend.save(u)

    res = testclient.get("/profile/temp/settings", status=200)
    res.mustcontain("If the user has forgotten his password")
    res.mustcontain("Send")

    res = res.form.submit(name="action", value="password-reset-mail")
    assert (
        "success",
        "A password reset link has been sent at the user email address. "
        "It should be received within a few minutes.",
    ) in res.flashes
    assert len(smtpd.messages) == 1
    assert smtpd.messages[0]["X-RcptTo"] == "john@doe.test"

    backend.delete(u)


@mock.patch("smtplib.SMTP")
def test_password_reset_email_failed(SMTP, smtpd, testclient, backend, logged_admin):
    SMTP.side_effect = mock.Mock(side_effect=OSError("unit test mail error"))
    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.test"],
        password="correct horse battery staple",
    )
    backend.save(u)

    res = testclient.get("/profile/temp/settings", status=200)
    res.mustcontain("If the user has forgotten his password")
    res.mustcontain("Send")

    res = res.form.submit(
        name="action", value="password-reset-mail", expect_errors=True
    )
    assert (
        "success",
        "A password reset link has been sent at the user email address. "
        "It should be received within a few minutes.",
    ) not in res.flashes
    assert ("error", "Could not send the password reset email") in res.flashes
    assert len(smtpd.messages) == 0

    backend.delete(u)


def test_admin_bad_request(testclient, logged_admin):
    res = testclient.get("/profile/admin/settings")
    testclient.post(
        "/profile/admin/settings",
        {"action": "foobar", "csrf_token": res.form["csrf_token"].value},
        status=400,
    )
    testclient.get("/profile/foobar/settings", status=404)


def test_edition_permission(
    testclient,
    logged_user,
    admin,
    backend,
):
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    backend.reload(logged_user)
    testclient.get("/profile/user/settings", status=404)

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = ["edit_self"]
    backend.reload(g.user)
    testclient.get("/profile/user/settings", status=200)


def test_account_locking(
    testclient,
    backend,
    logged_admin,
    user,
):
    res = testclient.get("/profile/user/settings")
    assert not user.lock_date
    assert not user.locked
    res.mustcontain("Lock the account")
    res.mustcontain(no="Unlock")

    res = res.form.submit(name="action", value="confirm-lock")
    res = res.form.submit(name="action", value="lock")
    user = backend.get(models.User, id=user.id)
    assert user.lock_date <= datetime.datetime.now(datetime.timezone.utc)
    assert user.locked
    res.mustcontain("The account has been locked")
    res.mustcontain(no="Lock the account")
    res.mustcontain("Unlock")

    res = res.form.submit(name="action", value="unlock")
    user = backend.get(models.User, id=user.id)
    assert not user.lock_date
    assert not user.locked
    res.mustcontain("The account has been unlocked")
    res.mustcontain("Lock the account")
    res.mustcontain(no="Unlock")


def test_past_lock_date(
    testclient,
    backend,
    logged_admin,
    user,
):
    res = testclient.get("/profile/user/settings", status=200)
    assert not user.lock_date
    assert not user.locked

    expiration_datetime = datetime.datetime.now(datetime.timezone.utc).replace(
        second=0, microsecond=0
    ) - datetime.timedelta(days=30)
    res.form["lock_date"] = expiration_datetime.strftime("%Y-%m-%d %H:%M")
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("success", "Profile updated successfully.")]

    res = res.follow()
    user = backend.get(models.User, id=user.id)
    assert user.lock_date == expiration_datetime
    assert user.locked


def test_future_lock_date(
    testclient,
    backend,
    logged_admin,
    user,
):
    res = testclient.get("/profile/user/settings", status=200)
    assert not user.lock_date
    assert not user.locked

    expiration_datetime = datetime.datetime.now(datetime.timezone.utc).replace(
        second=0, microsecond=0
    ) + datetime.timedelta(days=30)
    res.form["lock_date"] = expiration_datetime.strftime("%Y-%m-%d %H:%M")
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("success", "Profile updated successfully.")]

    res = res.follow()
    user = backend.get(models.User, id=user.id)
    assert user.lock_date == expiration_datetime
    assert not user.locked
    assert res.form["lock_date"].value == expiration_datetime.strftime("%Y-%m-%d %H:%M")


def test_empty_lock_date(
    testclient,
    backend,
    logged_admin,
    user,
):
    expiration_datetime = datetime.datetime.now(datetime.timezone.utc).replace(
        second=0, microsecond=0
    ) + datetime.timedelta(days=30)
    user.lock_date = expiration_datetime
    backend.save(user)

    res = testclient.get("/profile/user/settings", status=200)
    res.form["lock_date"] = ""
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("success", "Profile updated successfully.")]

    res = res.follow()
    backend.reload(user)
    assert not user.lock_date


def test_account_limit_values(
    testclient,
    backend,
    logged_admin,
    user,
):
    res = testclient.get("/profile/user/settings", status=200)
    assert not user.lock_date
    assert not user.locked

    expiration_datetime = datetime.datetime.max.replace(
        microsecond=0, tzinfo=datetime.timezone.utc
    )
    res.form["lock_date"] = expiration_datetime.strftime("%Y-%m-%d %H:%M:%S")
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("success", "Profile updated successfully.")]

    res = res.follow()
    user = backend.get(models.User, id=user.id)
    assert user.lock_date == expiration_datetime
    assert not user.locked


def test_edition_invalid_group(testclient, logged_admin, user, foo_group):
    res = testclient.get("/profile/user/settings", status=200)
    res.form["groups"].force_value("invalid")
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("error", "Profile edition failed.")]
    res.mustcontain("Invalid choice(s): one or more data inputs could not be coerced.")


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_account_reset_otp(
    testclient, backend, caplog, logged_admin, user_otp, otp_method
):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    old_token = user_otp.secret_token
    assert old_token is not None
    assert user_otp.last_otp_login is not None

    res = testclient.get("/profile/user/settings")
    res.mustcontain("Reset one-time password authentication")

    res = res.form.submit(name="action", value="confirm-reset-otp")
    res = res.form.submit(name="action", value="reset-otp")
    user = backend.get(models.User, id=user_otp.id)
    assert user.secret_token is not None
    assert user.secret_token != old_token
    assert user.last_otp_login is None
    if otp_method == "HOTP":
        assert user.hotp_counter == 1
    res.mustcontain("One-time password authentication has been reset")
    assert (
        "canaille",
        logging.SECURITY,
        "Reset one-time password authentication for user by admin from unknown IP",
    ) in caplog.record_tuples
