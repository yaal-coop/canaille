def test_password_forgotten(smtpd, testclient, slapd_connection, user):
    res = testclient.get("/reset", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert "A password reset link has been sent at your email address." in res.text
    assert "Send again" in res.text

    assert len(smtpd.messages) == 1


def test_password_forgotten_invalid_form(smtpd, testclient, slapd_connection, user):
    res = testclient.get("/reset", status=200)

    res.form["login"] = ""
    res = res.form.submit(status=200)
    assert "Could not send the password reset link." in res.text

    assert len(smtpd.messages) == 0


def test_password_forgotten_invalid(smtpd, testclient, slapd_connection, user):
    testclient.app.config["HIDE_INVALID_LOGINS"] = False
    res = testclient.get("/reset", status=200)

    res.form["login"] = "i-dont-really-exist"
    res = res.form.submit(status=200)
    assert "A password reset link has been sent at your email address." in res.text
    assert "The login 'i-dont-really-exist' does not exist" not in res.text

    testclient.app.config["HIDE_INVALID_LOGINS"] = True
    res = testclient.get("/reset", status=200)

    res.form["login"] = "i-dont-really-exist"
    res = res.form.submit(status=200)
    assert "A password reset link has been sent at your email address." not in res.text
    assert "The login 'i-dont-really-exist' does not exist" in res.text

    assert len(smtpd.messages) == 0
