def test_no_logged_no_access(testclient):
    testclient.get("/consent", status=403)


def test_consent_list(
    testclient, slapd_connection, client, consent, logged_user, token
):
    res = testclient.get("/consent", status=200)
    assert client.name in res.text
    assert not token.revoked

    res = testclient.get(f"/consent/delete/{consent.cn[0]}", status=302)

    res = res.follow(status=200)
    assert client.name not in res.text

    token.reload(conn=slapd_connection)
    assert token.revoked
