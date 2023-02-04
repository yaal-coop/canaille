def test_no_logged_no_access(testclient):
    testclient.get("/admin/token", status=403)


def test_no_admin_no_access(testclient, logged_user):
    testclient.get("/admin/token", status=403)


def test_token_list(testclient, token, logged_admin):
    res = testclient.get("/admin/token")
    assert token.token_id in res.text


def test_token_view(testclient, token, logged_admin):
    res = testclient.get("/admin/token/" + token.token_id)
    assert token.access_token in res.text


def test_token_not_found(testclient, logged_admin):
    res = testclient.get("/admin/token/" + "yolo", status=404)


def test_revoke_token(testclient, token, logged_admin):
    assert not token.revoked

    res = testclient.get(f"/admin/token/{token.token_id}/revoke")
    assert ("success", "The token has successfully been revoked.") in res.flashes

    token.reload()
    assert token.revoked


def test_revoke_invalid_token(testclient, logged_admin):
    testclient.get(f"/admin/token/invalid/revoke", status=404)
