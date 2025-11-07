import logging
from unittest import mock

from canaille.app import models


def test_user_without_password_first_login(testclient, backend, smtpd, caplog):
    """Test that users without passwords are redirected to first login flow and receive initialization email."""
    assert len(smtpd.messages) == 0
    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.test", "johhny@doe.test"],
    )
    backend.save(u)

    res = testclient.get("/login", status=200)
    res.form["login"] = "temp"
    res = res.form.submit(status=302)

    assert res.location == "/firstlogin/temp"
    res = res.follow(status=200)
    res.mustcontain("First login")

    res = res.form.submit(name="action", value="sendmail")

    assert (
        "info",
        "Sending password initialization link at your email address. "
        "It should be received within a few minutes.",
    ) in res.flashes

    assert (
        "canaille",
        logging.INFO,
        "The mail has been sent correctly.",
    ) in caplog.record_tuples

    assert len(smtpd.messages) == 2
    assert [message["X-RcptTo"] for message in smtpd.messages] == u.emails
    assert "Password initialization" in smtpd.messages[0].get("Subject")
    backend.delete(u)


@mock.patch("smtplib.SMTP")
def test_first_login_account_initialization_mail_sending_failed(
    SMTP, testclient, backend, smtpd, caplog
):
    """Test that first login initialization handles email sending failures gracefully."""
    SMTP.side_effect = mock.Mock(side_effect=OSError("unit test mail error"))
    assert len(smtpd.messages) == 0

    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.test"],
    )
    backend.save(u)

    res = testclient.get("/firstlogin/temp")
    res = res.form.submit(name="action", value="sendmail", expect_errors=True)

    assert (
        "info",
        "Sending password initialization link at your email address. "
        "It should be received within a few minutes.",
    ) in res.flashes

    assert (
        "canaille",
        logging.WARNING,
        "Could not send email: unit test mail error",
    ) in caplog.record_tuples

    assert len(smtpd.messages) == 0
    backend.delete(u)


def test_first_login_form_error(testclient, backend, smtpd):
    """Test that first login form validates CSRF tokens properly."""
    assert len(smtpd.messages) == 0
    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.test"],
    )
    backend.save(u)

    res = testclient.get("/firstlogin/temp", status=200)
    res.form["csrf_token"] = "invalid"
    res = res.form.submit(
        name="action", value="sendmail", status=400, expect_errors=True
    )
    assert len(smtpd.messages) == 0
    backend.delete(u)


def test_first_login_page_unavailable_for_users_with_password(
    testclient, backend, user
):
    """Test that first login page is not accessible for users who already have passwords."""
    testclient.get("/firstlogin/user", status=404)


def test_user_password_deleted_during_login(testclient, backend, smtpd):
    """Test that users are redirected to first login if their password is deleted during authentication."""
    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.test"],
        password="correct horse battery staple",
    )
    backend.save(u)

    res = testclient.get("/login")
    res.form["login"] = "temp"
    res = res.form.submit().follow()
    res.form["password"] = "correct horse battery staple"

    u.password = None
    backend.save(u)

    res = res.form.submit(status=302)
    assert res.location == "/firstlogin/temp"

    backend.delete(u)


def test_smtp_disabled(testclient, backend, smtpd):
    """Test that users without passwords can still attempt authentication when SMTP is disabled."""
    testclient.app.config["CANAILLE"]["SMTP"] = None

    assert len(smtpd.messages) == 0
    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.test", "johhny@doe.test"],
    )
    backend.save(u)

    res = testclient.get("/login", status=200)
    res.form["login"] = "temp"
    res = res.form.submit()
    res = res.follow()
    res.form["password"] = "incorrect horse"
    res = res.form.submit()
    assert ("error", "Login failed, please check your information") in res.flashes
    res.form["password"] = ""
    res = res.form.submit()
    assert ("error", "Login failed, please check your information") in res.flashes

    backend.delete(u)
