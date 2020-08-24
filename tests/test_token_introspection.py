from . import client_credentials


def test_token_introspection(testclient, user, client, token):
    res = testclient.post(
        "/oauth/introspect",
        params=dict(token=token.oauthAccessToken,),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    )
    assert 200 == res.status_code
    assert {
        "active": True,
        "client_id": token.oauthClientID,
        "token_type": token.oauthTokenType,
        "username": user.name,
        "scope": token.get_scope(),
        "sub": token.oauthSubject,
        "aud": token.oauthClientID,
        "iss": "https://mydomain.tld",
        "exp": token.get_expires_at(),
        "iat": token.get_issued_at(),
    } == res.json


def test_token_invalid(testclient, client):
    res = testclient.post(
        "/oauth/introspect",
        params=dict(token="invalid"),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    )
    assert 200 == res.status_code
    assert {"active": False,} == res.json
