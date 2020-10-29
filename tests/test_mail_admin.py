def test_reset_html(testclient, logged_admin):
    testclient.get("/admin/mail/reset.html")


def test_reset_txt(testclient, logged_admin):
    testclient.get("/admin/mail/reset.txt")
