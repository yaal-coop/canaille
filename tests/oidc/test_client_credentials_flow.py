from canaille.app import models

from . import client_credentials


def test_nominal_case(testclient, client, keypair, trusted_client, backend, caplog):
    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="client_credentials",
            scope="openid profile email groups address phone",
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    access_token = res.json["access_token"]
    token = backend.get(models.Token, access_token=access_token)
    assert token.client == client
    assert token.subject is None
    assert set(token.scope) == {
        "openid",
        "profile",
        "email",
        "groups",
        "address",
        "phone",
    }
