import base64


def test_success(testclient, user, client):
    client_credentials = base64.b64encode(
        client.oauthClientID.encode("utf-8")
        + b":"
        + client.oauthClientSecret.encode("utf-8")
    ).decode("utf-8")

    res = testclient.post(
        "/oauth/token",
        data=dict(
            grant_type="password",
            username=user.name,
            password="valid",
            scope="profile",
        ),
        headers={"Authorization": f"Basic {client_credentials}"},
    )
    assert 200 == res.status_code

    assert res.json["scope"] == ["openid", "profile"]
    assert res.json["token_type"] == "Bearer"
    access_token = res.json["access_token"]

    res = testclient.get(
        "/api/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert 200 == res.status_code
    assert {"foo": "bar"} == res.json
