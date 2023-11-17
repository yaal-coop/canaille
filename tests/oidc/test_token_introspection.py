from urllib.parse import parse_qs
from urllib.parse import urlsplit

from canaille.app import models

from . import client_credentials


def test_access_token_introspection(testclient, user, client, token):
    res = testclient.post(
        "/oauth/introspect",
        params={"token": token.access_token},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    assert {
        "active": True,
        "client_id": client.client_id,
        "token_type": token.type,
        "username": user.formatted_name,
        "scope": token.get_scope(),
        "sub": user.user_name,
        "aud": [client.client_id],
        "iss": "https://auth.mydomain.tld",
        "exp": token.get_expires_at(),
        "iat": token.get_issued_at(),
    } == res.json


def test_refresh_token_introspection(testclient, user, client, token):
    res = testclient.post(
        "/oauth/introspect",
        params={"token": token.refresh_token},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    assert {
        "active": True,
        "client_id": client.client_id,
        "token_type": token.type,
        "username": user.formatted_name,
        "scope": token.get_scope(),
        "sub": user.user_name,
        "aud": [client.client_id],
        "iss": "https://auth.mydomain.tld",
        "exp": token.get_expires_at(),
        "iat": token.get_issued_at(),
    } == res.json


def test_token_invalid(testclient, client):
    res = testclient.post(
        "/oauth/introspect",
        params=dict(token="invalid"),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    assert {"active": False} == res.json


def test_full_flow(testclient, logged_user, client, user, other_client):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="profile",
            nonce="somenonce",
        ),
        status=200,
    )

    res = res.form.submit(name="answer", value="accept", status=302)

    assert res.location.startswith(client.redirect_uris[0])
    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]
    authcode = models.AuthorizationCode.get(code=code)
    assert authcode is not None

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code,
            scope="profile",
            redirect_uri=client.redirect_uris[0],
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    access_token = res.json["access_token"]

    token = models.Token.get(access_token=access_token)
    assert token.client == client
    assert token.subject == logged_user

    res = testclient.post(
        "/oauth/introspect",
        params=dict(
            token=token.access_token,
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    assert {
        "aud": [client.client_id, other_client.client_id],
        "active": True,
        "client_id": client.client_id,
        "token_type": token.type,
        "username": user.formatted_name,
        "scope": token.get_scope(),
        "sub": user.user_name,
        "iss": "https://auth.mydomain.tld",
        "exp": token.get_expires_at(),
        "iat": token.get_issued_at(),
    } == res.json
