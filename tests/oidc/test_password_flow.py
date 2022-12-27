from canaille.oidc.models import Token

from . import client_credentials


def test_password_flow_basic(testclient, user, client):
    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="password",
            username="John (johnny) Doe",
            password="correct horse battery staple",
            scope="openid profile groups",
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    assert res.json["scope"] == "openid profile groups"
    assert res.json["token_type"] == "Bearer"
    access_token = res.json["access_token"]

    token = Token.get(access_token=access_token)
    assert token is not None

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"


def test_password_flow_post(testclient, user, client):
    client.token_endpoint_auth_method = "client_secret_post"
    client.save()

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="password",
            username="John (johnny) Doe",
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

    token = Token.get(access_token=access_token)
    assert token is not None

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert res.json["name"] == "John (johnny) Doe"


def test_invalid_credentials(testclient, user, client):
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
        "error_description": 'Invalid "username" or "password" in request.',
    }
