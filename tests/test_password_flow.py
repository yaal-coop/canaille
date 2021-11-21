from . import client_credentials
from canaille.models import Token


def test_password_flow_basic(testclient, slapd_connection, user, client):
    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="password",
            username="John Doe",
            password="correct horse battery staple",
            scope="profile",
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    assert res.json["scope"] == "openid profile groups"
    assert res.json["token_type"] == "Bearer"
    access_token = res.json["access_token"]

    token = Token.get(access_token, conn=slapd_connection)
    assert token is not None

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert {
        "name": "John Doe",
        "sub": "user",
        "family_name": "Doe",
        "groups": [],
    } == res.json


def test_password_flow_post(testclient, slapd_connection, user, client):
    client.oauthTokenEndpointAuthMethod = "client_secret_post"
    client.save(conn=slapd_connection)

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="password",
            username="John Doe",
            password="correct horse battery staple",
            scope="profile",
            client_id=client.oauthClientID,
            client_secret=client.oauthClientSecret,
        ),
        status=200,
    )

    assert res.json["scope"] == "openid profile groups"
    assert res.json["token_type"] == "Bearer"
    access_token = res.json["access_token"]

    token = Token.get(access_token, conn=slapd_connection)
    assert token is not None

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        status=200,
    )
    assert {
        "name": "John Doe",
        "sub": "user",
        "family_name": "Doe",
        "groups": [],
    } == res.json
