def test_no_logged_no_access(testclient):
    testclient.get("/admin/token", status=403)


def test_no_admin_no_access(testclient, logged_user):
    testclient.get("/admin/token", status=403)


def test_token_list(testclient, token, logged_admin):
    res = testclient.get("/admin/token")
    assert token.access_token in res.text


def test_token_view(testclient, token, logged_admin):
    res = testclient.get("/admin/token/" + token.access_token)
    assert token.access_token in res.text
