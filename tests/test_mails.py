import warnings
from unittest import mock


def test_send_test_email(testclient, logged_admin, smtpd):
    assert len(smtpd.messages) == 0

    res = testclient.get("/admin/mail")
    res.form["mail"] = "test@test.com"
    res = res.form.submit()
    assert "The test invitation mail has been sent correctly" in res.text

    assert len(smtpd.messages) == 1


@mock.patch("smtplib.SMTP")
def test_send_test_email_failed(SMTP, testclient, logged_admin):
    SMTP.side_effect = mock.Mock(side_effect=OSError("unit test mail error"))
    res = testclient.get("/admin/mail")
    res.form["mail"] = "test@test.com"
    with warnings.catch_warnings(record=True):
        res = res.form.submit(expect_errors=True)
    assert "The test invitation mail has not been sent correctly" in res.text


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
