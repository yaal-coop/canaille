from unittest import mock


def test_password_forgotten_disabled(smtpd, testclient, user):
    testclient.app.config["ENABLE_PASSWORD_RECOVERY"] = False

    testclient.get("/reset", status=404)
    testclient.get("/reset/uid/hash", status=404)

    res = testclient.get("/login")
    res.mustcontain(no="Forgotten password")


def test_password_forgotten(smtpd, testclient, user):
    res = testclient.get("/reset", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert (
        "success",
        "A password reset link has been sent at your email address. You should receive it within a few minutes.",
    ) in res.flashes
    res.mustcontain("Send again")

    assert len(smtpd.messages) == 1


def test_password_forgotten_invalid_form(smtpd, testclient, user):
    res = testclient.get("/reset", status=200)

    res.form["login"] = ""
    res = res.form.submit(status=200)
    assert ("error", "Could not send the password reset link.") in res.flashes

    assert len(smtpd.messages) == 0


def test_password_forgotten_invalid(smtpd, testclient, user):
    testclient.app.config["HIDE_INVALID_LOGINS"] = True
    res = testclient.get("/reset", status=200)

    res.form["login"] = "i-dont-really-exist"
    res = res.form.submit(status=200)
    assert (
        "success",
        "A password reset link has been sent at your email address. You should receive it within a few minutes.",
    ) in res.flashes
    res.mustcontain(no="The login &#39;i-dont-really-exist&#39; does not exist")

    testclient.app.config["HIDE_INVALID_LOGINS"] = False
    res = testclient.get("/reset", status=200)

    res.form["login"] = "i-dont-really-exist"
    res = res.form.submit(status=200)
    assert (
        "success",
        "A password reset link has been sent at your email address. You should receive it within a few minutes.",
    ) not in res.flashes
    res.mustcontain("The login &#39;i-dont-really-exist&#39; does not exist")

    assert len(smtpd.messages) == 0


def test_password_forgotten_invalid_when_user_cannot_self_edit(smtpd, testclient, user):
    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = []

    testclient.app.config["HIDE_INVALID_LOGINS"] = False
    res = testclient.get("/reset", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert (
        "success",
        "A password reset link has been sent at your email address. You should receive it within a few minutes.",
    ) not in res.flashes
    assert (
        "error",
        "The user 'John (johnny) Doe' does not have permissions to update their password. We cannot send a password reset email.",
    ) in res.flashes

    testclient.app.config["HIDE_INVALID_LOGINS"] = True
    res = testclient.get("/reset", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert (
        "error",
        "The user 'John (johnny) Doe' does not have permissions to update their password. We cannot send a password reset email.",
    ) not in res.flashes
    assert (
        "success",
        "A password reset link has been sent at your email address. You should receive it within a few minutes.",
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
        "A password reset link has been sent at your email address. You should receive it within a few minutes.",
    ) not in res.flashes
    assert (
        "error",
        "We encountered an issue while we sent the password recovery email.",
    ) in res.flashes
    res.mustcontain("Send again")

    assert len(smtpd.messages) == 0
