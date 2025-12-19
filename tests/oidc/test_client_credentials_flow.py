import pytest

from canaille.app import models

from . import client_credentials


def test_missing_scope_uses_client_default(testclient, client, backend):
    """Per RFC 6749 Section 3.3, if scope is omitted, use client's default scope."""
    res = testclient.post(
        "/oauth/token",
        params=dict(grant_type="client_credentials"),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    access_token = res.json["access_token"]
    token = backend.get(models.Token, access_token=access_token)
    assert set(token.scope) == set(client.scope)


def test_missing_scope_with_no_client_default(testclient, client, backend):
    """If client has no default scope and scope is omitted, return empty scope."""
    client.scope = []
    backend.save(client)

    res = testclient.post(
        "/oauth/token",
        params=dict(grant_type="client_credentials"),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    access_token = res.json["access_token"]
    token = backend.get(models.Token, access_token=access_token)
    assert token.scope == []


@pytest.mark.skip(
    reason="get_allowed_scope currently returns empty string for clients without scope, not None"
)
def test_missing_scope_with_invalid_scope_error(testclient, client, backend):
    """If client.get_allowed_scope returns None, should raise invalid_scope."""
    pass


def test_nominal_case(testclient, client, trusted_client, backend, caplog):
    """Test that client credentials flow works correctly for machine-to-machine authentication."""
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
