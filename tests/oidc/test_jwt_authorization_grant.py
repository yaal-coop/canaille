import time
import uuid

from joserfc import jwt

from canaille.app import models


def test_nominal_case(testclient, logged_user, client, backend, server_jwk):
    """Test JWT grant for a client with consent."""
    now = time.time()
    client.trusted = True
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
