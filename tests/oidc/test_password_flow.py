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
    assert {
        "name": "John (johnny) Doe",
        "sub": "user",
        "family_name": "Doe",
        "preferred_username": "Johnny",
        "groups": [],
        "locale": "en",
    } == res.json


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
    assert {
        "name": "John (johnny) Doe",
        "sub": "user",
        "family_name": "Doe",
        "preferred_username": "Johnny",
        "groups": [],
        "locale": "en",
    } == res.json
