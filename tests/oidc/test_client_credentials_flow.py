import time
import uuid

import pytest
from joserfc import jwt

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


def test_client_secret_post(testclient, client, backend):
    """Clients can send their credentials in the request body."""
    client.token_endpoint_auth_method = "client_secret_post"
    backend.save(client)

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="client_credentials",
            client_id=client.client_id,
            client_secret=client.client_secret,
        ),
        status=200,
    )

    token = backend.get(models.Token, access_token=res.json["access_token"])
    assert token.client == client


def test_private_key_jwt(testclient, client, client_jwk, backend):
    """Clients can authenticate with a JWT signed by their private key."""
    client.token_endpoint_auth_method = "private_key_jwt"
    backend.save(client)

    now = time.time()
    payload = {
        "iss": client.client_id,
        "sub": client.client_id,
        "aud": "http://canaille.test/oauth/token",
        "exp": now + 60,
        "iat": now,
        "jti": str(uuid.uuid4()),
    }
    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="client_credentials",
            client_assertion_type="urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            client_assertion=jwt.encode({"alg": "RS256"}, payload, client_jwk),
        ),
        status=200,
    )

    token = backend.get(models.Token, access_token=res.json["access_token"])
    assert token.client == client


def test_public_client_refused(testclient, client, backend):
    """Per RFC 6749 §4.4, public clients cannot use this grant."""
    client.token_endpoint_auth_method = "none"
    backend.save(client)

    res = testclient.post(
        "/oauth/token",
        params=dict(grant_type="client_credentials", client_id=client.client_id),
        expect_errors=True,
    )

    assert res.json["error"] == "invalid_client"
