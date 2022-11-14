def test_send_test_email(testclient, logged_admin, smtpd):
    assert len(smtpd.messages) == 0

    res = testclient.get("/admin/mail")
    res.form["mail"] = "test@test.com"
    res = res.form.submit()

    assert len(smtpd.messages) == 1


def test_mails(testclient, logged_admin):
    for base in ["password-init", "reset", "admin/admin@admin.com/invitation"]:
        testclient.get(f"/admin/mail/{base}.html")
        testclient.get(f"/admin/mail/{base}.txt")


def test_custom_from_addr(testclient, user, smtpd):
    testclient.app.config["NAME"] = "My Canaille"
    res = testclient.get("/reset", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert smtpd.messages[0]["X-MailFrom"] == "admin@mydomain.tld"
    assert smtpd.messages[0]["From"] == '"My Canaille" <admin@mydomain.tld>'


def test_default_from_addr(testclient, user, smtpd):
    del testclient.app.config["SMTP"]["FROM_ADDR"]
    res = testclient.get("/reset", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert smtpd.messages[0]["X-MailFrom"] == "admin@localhost"
    assert smtpd.messages[0]["From"] == '"Canaille" <admin@localhost>'
