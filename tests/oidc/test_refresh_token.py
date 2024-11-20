import datetime
import logging
from urllib.parse import parse_qs
from urllib.parse import urlsplit

from canaille.app import models

from . import client_credentials


def test_refresh_token(testclient, logged_user, client, backend, caplog):
    assert not backend.query(models.Consent)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
        ),
    )
    res = res.form.submit(name="answer", value="accept")

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = backend.get(models.AuthorizationCode, code=code)
    assert authcode is not None

    consents = backend.query(models.Consent, client=client, subject=logged_user)
    assert "profile" in consents[0].scope

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
    old_token = backend.get(models.Token, access_token=access_token)
    assert old_token is not None
    assert not old_token.revokation_date

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="refresh_token",
            refresh_token=res.json["refresh_token"],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    access_token = res.json["access_token"]
    new_token = backend.get(models.Token, access_token=access_token)
    assert new_token is not None
    assert old_token.access_token != new_token.access_token
    assert (
        "canaille",
        logging.SECURITY,
        "Issued refresh_token token for user in client Some client from unknown IP",
    ) in caplog.record_tuples
    backend.reload(old_token)
    assert old_token.revokation_date

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"

    for consent in consents:
        backend.delete(consent)


def test_refresh_token_with_invalid_user(testclient, client, backend):
    user = models.User(
        formatted_name="John Doe",
        family_name="Doe",
        user_name="temp",
        emails=["temp@temp.test"],
        password="correct horse battery staple",
    )
    backend.save(user)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
        ),
    ).follow()

    res.form["login"] = "temp"
    res = res.form.submit(name="answer", value="accept", status=302).follow()

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(name="answer", value="accept", status=302).follow()
    res = res.form.submit(name="answer", value="accept", status=302)

    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    backend.get(models.AuthorizationCode, code=code)

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

    refresh_token = res.json["refresh_token"]
    access_token = res.json["access_token"]
    backend.delete(user)

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="refresh_token",
            refresh_token=refresh_token,
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json == {
        "error": "invalid_request",
        "error_description": 'There is no "user" for this token.',
    }
    token = backend.get(models.Token, access_token=access_token)
    backend.delete(token)


def test_cannot_refresh_token_for_locked_users(
    testclient, logged_user, client, backend
):
    """Canaille should not issue new tokens for locked users."""
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            nonce="somenonce",
        ),
    )
    res = res.form.submit(name="answer", value="accept")

    assert res.location.startswith(client.redirect_uris[0])
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

    logged_user.lock_date = datetime.datetime.now(datetime.timezone.utc)
    backend.save(logged_user)

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="refresh_token",
            refresh_token=res.json["refresh_token"],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert "access_token" not in res.json
