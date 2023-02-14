from urllib.parse import parse_qs
from urllib.parse import urlsplit

from canaille.oidc.models import Consent
from canaille.oidc.models import Token

from . import client_credentials


def test_no_logged_no_access(testclient):
    testclient.get("/consent", status=403)


def test_revokation(testclient, client, consent, logged_user, token):
    res = testclient.get("/consent", status=200)
    assert client.client_name in res.text
    assert "Revoke access" in res.text
    assert "Restore access" not in res.text
    assert not consent.revoked
    assert not token.revoked

    res = testclient.get(f"/consent/revoke/{consent.cn[0]}", status=302)
    assert ("success", "The access has been revoked") in res.flashes
    res = res.follow(status=200)
    assert "Revoke access" not in res.text
    assert "Restore access" in res.text

    consent.reload()
    assert consent.revoked
    token.reload()
    assert token.revoked


def test_revokation_already_revoked(testclient, client, consent, logged_user):
    consent.revoke()

    consent.reload()
    assert consent.revoked

    res = testclient.get(f"/consent/revoke/{consent.cn[0]}", status=302)
    assert ("error", "The access is already revoked") in res.flashes
    res = res.follow(status=200)

    consent.reload()
    assert consent.revoked


def test_restoration(testclient, client, consent, logged_user, token):
    consent.revoke()

    consent.reload()
    assert consent.revoked
    token.reload()
    assert token.revoked

    res = testclient.get(f"/consent/restore/{consent.cn[0]}", status=302)
    assert ("success", "The access has been restored") in res.flashes
    res = res.follow(status=200)

    consent.reload()
    assert not consent.revoked
    token.reload()
    assert token.revoked


def test_restoration_already_restored(testclient, client, consent, logged_user, token):
    assert not consent.revoked

    res = testclient.get(f"/consent/restore/{consent.cn[0]}", status=302)
    assert ("error", "The access is not revoked") in res.flashes
    res = res.follow(status=200)


def test_invalid_consent_revokation(testclient, client, logged_user):
    res = testclient.get(f"/consent/revoke/invalid", status=302)
    assert ("success", "The access has been revoked") not in res.flashes
    assert ("error", "Could not revoke this access") in res.flashes


def test_someone_else_consent_revokation(testclient, client, consent, logged_moderator):
    res = testclient.get(f"/consent/revoke/{consent.cn[0]}", status=302)
    assert ("success", "The access has been revoked") not in res.flashes
    assert ("error", "Could not revoke this access") in res.flashes


def test_invalid_consent_restoration(testclient, client, logged_user):
    res = testclient.get(f"/consent/restore/invalid", status=302)
    assert ("success", "The access has been restored") not in res.flashes
    assert ("error", "Could not restore this access") in res.flashes


def test_someone_else_consent_restoration(
    testclient, client, consent, logged_moderator
):
    res = testclient.get(f"/consent/restore/{consent.cn[0]}", status=302)
    assert ("success", "The access has been restore") not in res.flashes
    assert ("error", "Could not restore this access") in res.flashes


def test_oidc_authorization_after_revokation(
    testclient, logged_user, client, keypair, consent
):
    consent.revoke()

    consent.reload()
    assert consent.revoked

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    Consent.all()
    consents = Consent.filter(client=client.dn, subject=logged_user.dn)
    assert consents[0].dn == consent.dn
    consent.reload()
    assert not consent.revoked

    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="openid profile",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    access_token = res.json["access_token"]
    token = Token.get(access_token=access_token)
    assert token.client == client.dn
    assert token.subject == logged_user.dn
