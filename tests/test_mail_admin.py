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
