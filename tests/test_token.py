def test_no_logged_no_access(testclient):
    testclient.get("/token", status=403)


def test_client_list(testclient, slapd_connection, client, token, logged_user):
    res = testclient.get("/token")
    assert 200 == res.status_code
    assert token.oauthAccessToken in res.text

    res = testclient.get(f"/token/delete/{token.oauthAccessToken}")
    assert 302 == res.status_code

    res = res.follow()
    assert 200 == res.status_code
    assert token.oauthAccessToken not in res.text

    token.oauthRevokationDate = ""
    token.save(conn=slapd_connection)
