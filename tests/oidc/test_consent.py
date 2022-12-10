import datetime


def test_no_logged_no_access(testclient):
    testclient.get("/consent", status=403)


def test_delete(testclient, client, consent, logged_user, token):
    res = testclient.get("/consent", status=200)
    assert client.client_name in res.text
    assert not token.revoked

    res = testclient.get(f"/consent/delete/{consent.cn[0]}", status=302)
    res = res.follow(status=200)
    assert "The access has been revoked" in res.text
    assert client.client_name not in res.text

    token.reload()
    assert token.revoked


def test_delete_token_already_revoked(testclient, client, consent, logged_user, token):
    revokation_date = datetime.datetime.utcnow().replace(
        microsecond=0
    ) - datetime.timedelta(days=7)
    token.revokation_date = revokation_date
    token.save()

    token.reload()
    assert token.revoked
    assert token.revokation_date == revokation_date

    res = testclient.get(f"/consent/delete/{consent.cn[0]}", status=302)
    res = res.follow(status=200)
    assert "The access has been revoked" in res.text
    assert client.client_name not in res.text

    token.reload()
    assert token.revoked
    assert token.revokation_date == revokation_date


def test_invalid_consent_delete(testclient, client, logged_user):
    res = testclient.get(f"/consent/delete/invalid", status=302)
    res = res.follow(status=200)
    assert "The access has been revoked" not in res.text
    assert "Could not delete this access" in res.text


def test_someone_else_consent_delete(testclient, client, consent, logged_moderator):
    res = testclient.get(f"/consent/delete/{consent.cn[0]}", status=302)
    res = res.follow(status=200)
    assert "The access has been revoked" not in res.text
    assert "Could not delete this access" in res.text
