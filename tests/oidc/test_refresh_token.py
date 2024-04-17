import datetime
from urllib.parse import parse_qs
from urllib.parse import urlsplit

import freezegun

from canaille.app import models

from . import client_credentials


def test_refresh_token(testclient, user, client):
    assert not models.Consent.query()

    with freezegun.freeze_time("2020-01-01 01:00:00"):
        res = testclient.get(
            "/oauth/authorize",
            params=dict(
                response_type="code",
                client_id=client.client_id,
                scope="openid profile",
                nonce="somenonce",
            ),
        )
        res = res.follow()

        res.form["login"] = "user"
        res = res.form.submit(name="answer", value="accept")
        res = res.follow()
        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(name="answer", value="accept")
        res = res.follow()
        res = res.form.submit(name="answer", value="accept")

        assert res.location.startswith(client.redirect_uris[0])
        params = parse_qs(urlsplit(res.location).query)
        code = params["code"][0]
        authcode = models.AuthorizationCode.get(code=code)
        assert authcode is not None

        consents = models.Consent.query(client=client, subject=user)
        assert "profile" in consents[0].scope

    with freezegun.freeze_time("2020-01-01 00:01:00"):
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
        old_token = models.Token.get(access_token=access_token)
        assert old_token is not None
        assert not old_token.revokation_date

    with freezegun.freeze_time("2020-01-01 00:02:00"):
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
        new_token = models.Token.get(access_token=access_token)
        assert new_token is not None
        assert old_token.access_token != new_token.access_token

        old_token.reload()
        assert old_token.revokation_date

    with freezegun.freeze_time("2020-01-01 00:03:00"):
        res = testclient.get(
            "/oauth/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            status=200,
        )
        assert res.json["name"] == "John (johnny) Doe"

    for consent in consents:
        consent.delete()


def test_refresh_token_with_invalid_user(testclient, client):
    user = models.User(
        formatted_name="John Doe",
        family_name="Doe",
        user_name="temp",
        emails=["temp@temp.com"],
        password="correct horse battery staple",
    )
    user.save()

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
    models.AuthorizationCode.get(code=code)

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
    user.delete()

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
    models.Token.get(access_token=access_token).delete()


def test_cannot_refresh_token_for_locked_users(testclient, user, client):
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
    res = res.follow()

    res.form["login"] = "user"
    res = res.form.submit(name="answer", value="accept")
    res = res.follow()
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(name="answer", value="accept")
    res = res.follow()
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

    user.lock_date = datetime.datetime.now(datetime.timezone.utc)
    user.save()

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
