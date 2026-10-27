import datetime

from . import client_assertion
from . import client_credentials


def test_revoke_access_token(testclient, user, client, token, backend):
    assert not token.revokation_date

    res = testclient.post(
        "/oauth/revoke",
        params={"token": token.access_token},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    assert {} == res.json

    backend.reload(token)
    assert token.revokation_date

    testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token.access_token}"},
        status=401,
    )


def test_revoke_access_token_with_hint(testclient, user, client, token, backend):
    assert not token.revokation_date

    res = testclient.post(
        "/oauth/revoke",
        params={"token": token.access_token, "token_type_hint": "access_token"},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    assert {} == res.json

    backend.reload(token)
    assert token.revokation_date


def test_revoke_refresh_token(testclient, user, client, token, backend):
    assert not token.revokation_date

    res = testclient.post(
        "/oauth/revoke",
        params={"token": token.refresh_token},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    assert {} == res.json

    backend.reload(token)
    assert token.revokation_date


def test_revoke_refresh_token_with_hint(testclient, user, client, token, backend):
    assert not token.revokation_date

    res = testclient.post(
        "/oauth/revoke",
        params={"token": token.refresh_token, "token_type_hint": "refresh_token"},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    assert {} == res.json

    backend.reload(token)
    assert token.revokation_date


def test_cannot_refresh_after_revocation(testclient, user, client, token, backend):
    token.revokation_date = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
        days=7
    )
    backend.save(token)

    res = testclient.post(
        "/oauth/token",
        params={
            "grant_type": "refresh_token",
            "refresh_token": token.refresh_token,
        },
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json == {"error": "invalid_grant"}


def test_revoke_with_client_secret_post(testclient, client, token, backend):
    testclient.post(
        "/oauth/revoke",
        params={
            "token": token.access_token,
            "client_id": client.client_id,
            "client_secret": client.client_secret,
        },
        status=200,
    )
    backend.reload(token)
    assert token.revokation_date


def test_revoke_with_private_key_jwt(testclient, client, client_jwk, token, backend):
    client.token_endpoint_auth_method = "private_key_jwt"
    backend.save(client)

    testclient.post(
        "/oauth/revoke",
        params={"token": token.access_token, **client_assertion(client, client_jwk)},
        status=200,
    )
    backend.reload(token)
    assert token.revokation_date


def test_token_invalid(testclient, client):
    res = testclient.post(
        "/oauth/revoke",
        params={"token": "invalid"},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    assert {} == res.json
