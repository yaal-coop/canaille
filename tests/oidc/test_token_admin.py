def test_no_logged_no_access(testclient):
    testclient.get("/admin/token", status=403)


def test_no_admin_no_access(testclient, logged_user):
    testclient.get("/admin/token", status=403)


def test_token_list(testclient, token, logged_admin):
    res = testclient.get("/admin/token")
    assert token.oauthAccessToken in res.text


def test_token_view(testclient, token, logged_admin):
    res = testclient.get("/admin/token/" + token.oauthAccessToken)
    for attr in token.may + token.must:
        assert attr in res.text
