def test_no_logged_no_access(testclient):
    testclient.get("/authorization", status=403)


def test_no_admin_no_access(testclient, logged_user):
    testclient.get("/authorization", status=403)


def test_authorizaton_list(testclient, authorization, logged_admin):
    res = testclient.get("/authorization")
    assert authorization.oauthCode in res.text


def test_authorizaton_view(testclient, authorization, logged_admin):
    res = testclient.get("/authorization/" + authorization.oauthCode)
    for attr in authorization.may + authorization.must:
        assert attr in res.text
