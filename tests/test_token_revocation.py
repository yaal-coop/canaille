from . import client_credentials


def test_token_revocation(testclient, user, client, token, slapd_connection):
    assert not token.revoked

    res = testclient.post(
        "/oauth/revoke",
        params=dict(token=token.oauthAccessToken,),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    )
    assert 200 == res.status_code
    assert {} == res.json

    token.reload(slapd_connection)
    assert token.revoked


def test_token_invalid(testclient, client):
    res = testclient.post(
        "/oauth/revoke",
        params=dict(token="invalid"),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
    )
    assert 200 == res.status_code
    assert {} == res.json
