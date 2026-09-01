import time
import uuid

from joserfc import jwt

from canaille.app import models


def test_nominal_case(testclient, logged_user, client, backend, server_jwk):
    """Test JWT grant for a client with consent."""
    now = time.time()
    client.client_uri = "https://client.trusted.test"
    client.redirect_uris = ["https://client.trusted.test/redirect1"]
    backend.save(client)

    header = {"alg": "RS256"}
    payload = {
        "iss": client.client_id,
        "sub": logged_user.user_name,
        "aud": "http://canaille.test/oauth/token",
        "nbf": now - 3600,
        "exp": now + 3600,
        "iat": now - 1,
        "jti": str(uuid.uuid4()),
    }
    client_jwt = jwt.encode(header, payload, server_jwk)

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="urn:ietf:params:oauth:grant-type:jwt-bearer",
            scope="openid profile email groups address phone",
            assertion=client_jwt,
            redirect_uri=client.redirect_uris[0],
        ),
        status=200,
    )

    access_token = res.json["access_token"]
    token = backend.get(models.Token, access_token=access_token)
    assert token.client == client
    assert token.subject == logged_user
    assert set(token.scope) == {
        "openid",
        "profile",
        "email",
        "groups",
        "address",
        "phone",
    }


def test_unknown_issuer(testclient, logged_user, client, backend, server_jwk):
    """An assertion whose 'iss' matches no client is refused."""
    now = time.time()
    payload = {
        "iss": "unknown-client-id",
        "sub": logged_user.user_name,
        "aud": "http://canaille.test/oauth/token",
        "nbf": now - 3600,
        "exp": now + 3600,
        "iat": now - 1,
        "jti": str(uuid.uuid4()),
    }
    client_jwt = jwt.encode({"alg": "RS256"}, payload, server_jwk)

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="urn:ietf:params:oauth:grant-type:jwt-bearer",
            scope="openid profile",
            assertion=client_jwt,
        ),
        status=400,
    )
    assert res.json["error"] == "invalid_grant"


def test_missing_issuer(testclient, logged_user, client, backend, server_jwk):
    """An assertion without an 'iss' claim is refused."""
    now = time.time()
    payload = {
        "sub": logged_user.user_name,
        "aud": "http://canaille.test/oauth/token",
        "exp": now + 3600,
        "jti": str(uuid.uuid4()),
    }
    client_jwt = jwt.encode({"alg": "RS256"}, payload, server_jwk)

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="urn:ietf:params:oauth:grant-type:jwt-bearer",
            scope="openid profile",
            assertion=client_jwt,
        ),
        status=400,
    )
    assert res.json["error"] == "invalid_grant"


def test_malformed_assertion(testclient, logged_user, client, backend):
    """An assertion that is not a JWT is refused."""
    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="urn:ietf:params:oauth:grant-type:jwt-bearer",
            scope="openid profile",
            assertion="not-a-jwt",
        ),
        status=400,
    )
    assert res.json["error"] == "invalid_grant"
