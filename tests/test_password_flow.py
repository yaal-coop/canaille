from . import client_credentials
from web.models import Token


def test_success(testclient, slapd_connection, user, client):
    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="password",
            username=user.name,
            password="correct horse battery staple",
            scope="profile",
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    )
    assert 200 == res.status_code

    assert res.json["scope"] == ["openid", "profile"]
    assert res.json["token_type"] == "Bearer"
    access_token = res.json["access_token"]

    token = Token.get(access_token, slapd_connection)
    assert token is not None

    res = testclient.get("/api/me", headers={"Authorization": f"Bearer {access_token}"})
    assert 200 == res.status_code
    assert {"foo": "bar"} == res.json
