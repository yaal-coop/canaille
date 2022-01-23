from . import client_credentials


def test_token_revocation(testclient, user, client, token, slapd_connection):
    assert not token.revokation_date

    res = testclient.post(
        "/oauth/revoke",
        params=dict(
            token=token.access_token,
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    assert {} == res.json

    token.reload(slapd_connection)
    assert token.revokation_date


def test_token_invalid(testclient, client):
    res = testclient.post(
        "/oauth/revoke",
        params=dict(token="invalid"),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    assert {} == res.json
