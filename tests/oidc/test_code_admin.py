def test_no_logged_no_access(testclient):
    testclient.get("/admin/authorization", status=403)


def test_no_admin_no_access(testclient, logged_user):
    testclient.get("/admin/authorization", status=403)


def test_authorizaton_list(testclient, authorization, logged_admin):
    res = testclient.get("/admin/authorization")
    assert authorization.authorization_code_id in res.text


def test_authorizaton_view(testclient, authorization, logged_admin):
    res = testclient.get("/admin/authorization/" + authorization.authorization_code_id)
    for attr in authorization.may + authorization.must:
        assert attr in res.text
