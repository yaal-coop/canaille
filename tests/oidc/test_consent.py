def test_no_logged_no_access(testclient):
    testclient.get("/consent", status=403)


def test_consent_list(testclient, client, consent, logged_user, token):
    res = testclient.get("/consent", status=200)
    assert client.client_name in res.text
    assert not token.revoked

    res = testclient.get(f"/consent/delete/{consent.cn[0]}", status=302)

    res = res.follow(status=200)
    assert client.client_name not in res.text

    token.reload()
    assert token.revoked
