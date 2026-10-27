import base64
import time
import uuid

from joserfc import jwt


def client_credentials(client):
    return base64.b64encode(
        client.client_id.encode("utf-8") + b":" + client.client_secret.encode("utf-8")
    ).decode("utf-8")


def client_assertion(client, client_jwk):
    """Return the request parameters of a private_key_jwt client authentication."""
    now = time.time()
    payload = {
        "iss": client.client_id,
        "sub": client.client_id,
        "aud": "http://canaille.test/oauth/token",
        "nbf": now - 3600,
        "exp": now + 3600,
        "iat": now - 1,
        "jti": str(uuid.uuid4()),
    }
    return {
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": jwt.encode({"alg": "RS256"}, payload, client_jwk),
    }
