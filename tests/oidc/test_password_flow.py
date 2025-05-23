import time
import uuid

from joserfc import jwt

from canaille.app import models

from . import client_credentials


def test_password_flow_basic(testclient, user, client, backend):
    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="password",
            username="user",
            password="correct horse battery staple",
            scope="openid profile groups",
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    assert res.json["scope"] == "openid profile groups"
    assert res.json["token_type"] == "Bearer"
    access_token = res.json["access_token"]

    token = backend.get(models.Token, access_token=access_token)
    assert token is not None

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"


def test_password_flow_post(testclient, user, client, backend):
    client.token_endpoint_auth_method = "client_secret_post"
    backend.save(client)

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="password",
            username="user",
            password="correct horse battery staple",
            scope="openid profile groups",
            client_id=client.client_id,
            client_secret=client.client_secret,
        ),
        status=200,
    )

    assert res.json["scope"] == "openid profile groups"
    assert res.json["token_type"] == "Bearer"
    access_token = res.json["access_token"]

    token = backend.get(models.Token, access_token=access_token)
    assert token is not None

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"


def test_invalid_user(testclient, user, client):
    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="password",
            username="invalid",
            password="invalid",
            scope="openid profile groups",
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )

    assert res.json == {
        "error": "invalid_request",
        "error_description": "Invalid 'username' or 'password' in request.",
    }


def test_invalid_credentials(testclient, user, client):
    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="password",
            username="user",
            password="invalid",
            scope="openid profile groups",
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )

    assert res.json == {
        "error": "invalid_request",
        "error_description": "Invalid 'username' or 'password' in request.",
    }


def test_jwt_auth(testclient, client_jwk, client, token, caplog, backend, user):
    """Test client JWT authentication as defined per RFC7523, for a password grant."""
    now = time.time()

    client.trusted = True
    client.token_endpoint_auth_method = "client_secret_jwt"
    backend.save(client)

    header = {"alg": "RS256"}
    payload = {
        "iss": client.client_id,
        "sub": client.client_id,
        "aud": "http://canaille.test/oauth/token",
        "nbf": now - 3600,
        "exp": now + 3600,
        "iat": now - 1,
        "jti": str(uuid.uuid4()),
    }
    client_jwt = jwt.encode(header, payload, client_jwk)
    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="password",
            username="user",
            password="correct horse battery staple",
            scope="openid profile groups",
            client_assertion=client_jwt,
            client_assertion_type="urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        ),
        status=200,
    )

    assert res.json["scope"] == "openid profile groups"
    assert res.json["token_type"] == "Bearer"
    access_token = res.json["access_token"]

    token = backend.get(models.Token, access_token=access_token)
    assert token is not None
