import datetime
import logging
from unittest import mock

import pytest


def test_password_forgotten_disabled(smtpd, testclient, user):
    testclient.app.config["CANAILLE"]["ENABLE_PASSWORD_RECOVERY"] = False

    testclient.get("/reset", status=404)
    testclient.get("/reset/user/hash", status=404)
    testclient.get("/reset-code/user", status=404)

    res = testclient.get("/login")
    res.mustcontain(no="Forgotten password")


def test_password_forgotten(smtpd, testclient, user, caplog):
    res = testclient.get("/reset", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert (
        "success",
        "A password reset link has been sent at your email address. You should receive "
        "it within a few minutes.",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Sending a reset password mail to john@doe.test for user",
    ) in caplog.record_tuples
    res.mustcontain("Send again")

    assert len(smtpd.messages) == 1


def test_password_forgotten_multiple_mails(smtpd, testclient, user, backend, caplog):
    user.emails = ["foo@bar.test", "foo@baz.test", "foo@foo.com"]
    backend.save(user)

    res = testclient.get("/reset", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert (
        "success",
        "A password reset link has been sent at your email address. You should receive "
        "it within a few minutes.",
    ) in res.flashes
    for email in user.emails:
        assert (
            "canaille",
            logging.SECURITY,
            f"Sending a reset password mail to {email} for user",
        ) in caplog.record_tuples
    res.mustcontain("Send again")

    assert len(smtpd.messages) == 3
    assert [message["X-RcptTo"] for message in smtpd.messages] == user.emails


def test_password_forgotten_invalid_form(smtpd, testclient, user):
    res = testclient.get("/reset", status=200)

    res.form["login"] = ""
    res = res.form.submit(status=200)
    assert ("error", "Could not send the password reset link.") in res.flashes

    assert len(smtpd.messages) == 0


def test_password_forgotten_invalid(smtpd, testclient, user):
    testclient.app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] = True
    res = testclient.get("/reset", status=200)

    res.form["login"] = "i-dont-really-exist"
    res = res.form.submit(status=200)
    assert (
        "success",
        "A password reset link has been sent at your email address. "
        "You should receive it within a few minutes.",
    ) in res.flashes
    res.mustcontain(no="The login &#39;i-dont-really-exist&#39; does not exist")

    testclient.app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] = False
    res = testclient.get("/reset", status=200)

    res.form["login"] = "i-dont-really-exist"
    res = res.form.submit(status=200)
    assert (
        "success",
        "A password reset link has been sent at your email address. "
        "You should receive it within a few minutes.",
    ) not in res.flashes
    res.mustcontain("The login &#39;i-dont-really-exist&#39; does not exist")

    assert len(smtpd.messages) == 0


def test_password_forgotten_invalid_when_user_cannot_self_edit(
    smtpd, testclient, user, backend
):
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    backend.reload(user)

    testclient.app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] = False
    res = testclient.get("/reset", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert (
        "success",
        "A password reset link has been sent at your email address. "
        "You should receive it within a few minutes.",
    ) not in res.flashes
    assert (
        "error",
        "The user 'John (johnny) Doe' does not have permissions to update their "
        "password. We cannot send a password reset email.",
    ) in res.flashes

    testclient.app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] = True
    backend.reload(user)
    res = testclient.get("/reset", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert (
        "error",
        "The user 'John (johnny) Doe' does not have permissions to update their "
        "password. We cannot send a password reset email.",
    ) not in res.flashes
    assert (
        "success",
        "A password reset link has been sent at your email address. "
        "You should receive it within a few minutes.",
    ) in res.flashes

    assert len(smtpd.messages) == 0


@mock.patch("smtplib.SMTP")
def test_password_forgotten_mail_error(SMTP, smtpd, testclient, user):
    SMTP.side_effect = mock.Mock(side_effect=OSError("unit test mail error"))
    res = testclient.get("/reset", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=200, expect_errors=True)
    assert (
        "success",
        "A password reset link has been sent at your email address. "
        "You should receive it within a few minutes.",
    ) not in res.flashes
    assert (
        "error",
        "We encountered an issue while we sent the password recovery email.",
    ) in res.flashes
    res.mustcontain("Send again")

    assert len(smtpd.messages) == 0


def test_password_forgotten_user_disabled(smtpd, testclient, user, caplog, backend):
    """No mail should be sent if a disabled user asks for a password reset."""
    user.lock_date = datetime.datetime.now(datetime.timezone.utc)
    backend.save(user)

    res = testclient.get("/reset", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert (
        "success",
        "A password reset link has been sent at your email address. You should receive "
        "it within a few minutes.",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Sending a reset password mail to john@doe.test for user",
    ) not in caplog.record_tuples

    assert len(smtpd.messages) == 0


def test_password_forgotten_without_trusted_hosts(
    smtpd, testclient, user, caplog, backend
):
    testclient.app.config["TRUSTED_HOSTS"] = None
    res = testclient.get("/reset", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    assert (
        "success",
        "A password reset code has been sent at your email address. You should receive "
        "it within a few minutes.",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Sending a reset password mail to john@doe.test for user",
    ) in caplog.record_tuples

    assert len(smtpd.messages) == 1

    res = res.follow(status=200)

    backend.reload(user)
    code = user.one_time_password
    email_content = str(smtpd.messages[0].get_payload()[0]).replace("=\n", "")
    assert code in email_content

    main_form = res.forms[0]
    main_form["code"] = code
    res = main_form.submit(status=302)
    res.follow(status=200)

    assert res.location == f"/reset/{user.user_name}/{code}"


def test_password_forgotten_without_trusted_hosts_wrong_code(
    smtpd, testclient, user, caplog, backend
):
    testclient.app.config["TRUSTED_HOSTS"] = None
    res = testclient.get("/reset", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    main_form = res.forms[0]
    main_form["code"] = "111111"
    res = main_form.submit(status=200)

    assert ("error", "Invalid code.") in res.flashes


def test_password_forgotten_trying_to_access_code_page_with_trusted_hosts_enabled(
    smtpd, testclient, user
):
    testclient.get("/reset-code/user", status=404)


def test_password_forgotten_trying_to_access_code_page_when_user_cannot_self_edit(
    smtpd, testclient, user, backend
):
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    testclient.app.config["TRUSTED_HOSTS"] = None
    backend.reload(user)

    testclient.app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] = False
    res = testclient.get("/reset-code/user", status=302)
    assert (
        "error",
        "The user 'John (johnny) Doe' does not have permissions to update their "
        "password.",
    ) not in res.flashes


def test_password_reset_with_wrong_host(
    configuration, smtpd, testclient, backend, user
):
    res = testclient.get("/reset", status=200)
    res.form["login"] = "user"
    # Raises an attribute error but a Security Error is raised before during host validation, causing the attribute error later
    with pytest.raises(AttributeError):
        res.form.submit(headers={"Host": "test.test"}, status=400)
