def test_no_logged_no_access(testclient):
    testclient.get("/consent", status=403)


def test_client_list(testclient, slapd_connection, client, consent, logged_user, token):
    res = testclient.get("/consent")
    assert 200 == res.status_code
    assert client.oauthClientName in res.text
    assert not token.revoked

    res = testclient.get(f"/consent/delete/{consent.cn[0]}")
    assert 302 == res.status_code

    res = res.follow()
    assert 200 == res.status_code
    assert client.oauthClientName not in res.text

    token.reload(conn=slapd_connection)
    assert token.revoked
