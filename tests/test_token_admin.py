def test_no_logged_no_access(testclient):
    testclient.get("/token", status=403)


def test_no_admin_no_access(testclient, logged_user):
    testclient.get("/token", status=403)


def test_token_list(testclient, token, logged_admin):
    res = testclient.get("/token")
    assert token.oauthAccessToken in res.text


def test_token_view(testclient, token, logged_admin):
    res = testclient.get("/token/" + token.oauthAccessToken)
    for attr in token.may + token.must:
        assert attr in res.text
