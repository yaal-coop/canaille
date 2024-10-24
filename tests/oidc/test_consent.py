import logging
from urllib.parse import parse_qs
from urllib.parse import urlsplit

from canaille.app import models

from . import client_credentials


def test_no_logged_no_access(testclient):
    testclient.get("/consent", status=403)


def test_revokation(testclient, client, consent, logged_user, token, backend, caplog):
    res = testclient.get("/consent", status=200)
    res.mustcontain(client.client_name)
    res.mustcontain("Revoke access")
    res.mustcontain(no="Restore access")
    assert not consent.revoked
    assert not token.revoked

    res = testclient.get(f"/consent/revoke/{consent.consent_id}", status=302)
    assert ("success", "The access has been revoked") in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        f"Consent revoked for {logged_user.user_name} in client {client.client_name} from unknown IP",
    ) in caplog.record_tuples
    res = res.follow(status=200)
    res.mustcontain(no="Revoke access")
    res.mustcontain("Restore access")

    backend.reload(consent)
    assert consent.revoked
    backend.reload(token)
    assert token.revoked


def test_revokation_already_revoked(testclient, client, consent, logged_user, backend):
    consent.revoke()

    assert consent.revoked

    res = testclient.get(f"/consent/revoke/{consent.consent_id}", status=302)
    assert ("error", "The access is already revoked") in res.flashes
    res = res.follow(status=200)

    backend.reload(consent)
    assert consent.revoked


def test_restoration(testclient, client, consent, logged_user, token, backend):
    consent.revoke()

    assert consent.revoked
    backend.reload(token)
    assert token.revoked

    res = testclient.get(f"/consent/restore/{consent.consent_id}", status=302)
    assert ("success", "The access has been restored") in res.flashes
    res = res.follow(status=200)

    backend.reload(consent)
    assert not consent.revoked
    backend.reload(token)
    assert token.revoked


def test_restoration_already_restored(testclient, client, consent, logged_user, token):
    assert not consent.revoked

    res = testclient.get(f"/consent/restore/{consent.consent_id}", status=302)
    assert ("error", "The access is not revoked") in res.flashes
    res = res.follow(status=200)


def test_invalid_consent_revokation(testclient, client, logged_user):
    res = testclient.get("/consent/revoke/invalid", status=302)
    assert ("success", "The access has been revoked") not in res.flashes
    assert ("error", "Could not revoke this access") in res.flashes


def test_someone_else_consent_revokation(testclient, client, consent, logged_moderator):
    res = testclient.get(f"/consent/revoke/{consent.consent_id}", status=302)
    assert ("success", "The access has been revoked") not in res.flashes
    assert ("error", "Could not revoke this access") in res.flashes


def test_invalid_consent_restoration(testclient, client, logged_user):
    res = testclient.get("/consent/restore/invalid", status=302)
    assert ("success", "The access has been restored") not in res.flashes
    assert ("error", "Could not restore this access") in res.flashes


def test_someone_else_consent_restoration(
    testclient, client, consent, logged_moderator
):
    res = testclient.get(f"/consent/restore/{consent.consent_id}", status=302)
    assert ("success", "The access has been restore") not in res.flashes
    assert ("error", "Could not restore this access") in res.flashes


def test_oidc_authorization_after_revokation(
    testclient, logged_user, client, keypair, consent, backend
):
    consent.revoke()

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

    consents = backend.query(models.Consent, client=client, subject=logged_user)
    backend.reload(consent)
    assert consents[0] == consent
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
    token = backend.get(models.Token, access_token=access_token)
    assert token.client == client
    assert token.subject == logged_user


def test_preconsented_client_appears_in_consent_list(
    testclient, client, logged_user, backend
):
    assert not client.preconsent
    res = testclient.get("/consent/pre-consents")
    res.mustcontain(no=client.client_name)

    client.preconsent = True
    backend.save(client)

    res = testclient.get("/consent/pre-consents")
    res.mustcontain(client.client_name)


def test_revoke_preconsented_client(testclient, client, logged_user, token, backend):
    client.preconsent = True
    backend.save(client)
    assert not backend.get(models.Consent)
    assert not token.revoked

    res = testclient.get(f"/consent/revoke-preconsent/{client.client_id}", status=302)
    assert ("success", "The access has been revoked") in res.flashes

    consent = backend.get(models.Consent)
    assert consent.client == client
    assert consent.subject == logged_user
    assert consent.scope == ["openid", "email", "profile", "groups", "address", "phone"]
    assert not consent.issue_date
    backend.reload(token)
    assert token.revoked

    res = testclient.get(f"/consent/restore/{consent.consent_id}", status=302)
    assert ("success", "The access has been restored") in res.flashes

    backend.reload(consent)
    assert not consent.revoked
    assert consent.issue_date
    backend.reload(token)
    assert token.revoked

    res = testclient.get(f"/consent/revoke/{consent.consent_id}", status=302)
    assert ("success", "The access has been revoked") in res.flashes
    backend.reload(consent)
    assert consent.revoked
    assert consent.issue_date


def test_revoke_invalid_preconsented_client(testclient, logged_user):
    res = testclient.get("/consent/revoke-preconsent/invalid", status=302)
    assert ("error", "Could not revoke this access") in res.flashes


def test_revoke_preconsented_client_with_manual_consent(
    testclient, logged_user, client, consent, backend
):
    client.preconsent = True
    backend.save(client)
    res = testclient.get(f"/consent/revoke-preconsent/{client.client_id}", status=302)
    res = res.follow()
    assert ("success", "The access has been revoked") in res.flashes


def test_revoke_preconsented_client_with_manual_revokation(
    testclient, logged_user, client, consent, backend
):
    client.preconsent = True
    backend.save(client)
    consent.revoke()
    backend.save(consent)

    res = testclient.get(f"/consent/revoke-preconsent/{client.client_id}", status=302)
    res = res.follow()
    assert ("error", "The access is already revoked") in res.flashes
