import datetime
import json
import time
import uuid

from joserfc import jwk
from joserfc import jwt

from canaille.app import models

TOKEN_ENDPOINT = "http://canaille.test/oauth/token"


def assertion(client, user, key, **claims):
    """Return a JWT bearer assertion of ``client`` for ``user``."""
    now = time.time()
    payload = {
        "iss": client.client_id,
        "sub": user.user_name,
        "aud": TOKEN_ENDPOINT,
        "exp": now + 600,
        "iat": now - 1,
        "jti": str(uuid.uuid4()),
        **claims,
    }
    payload = {key: value for key, value in payload.items() if value is not None}
    return jwt.encode({"alg": "RS256"}, payload, key)


def request_tokens(testclient, assertion, status, scope="openid profile"):
    return testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="urn:ietf:params:oauth:grant-type:jwt-bearer",
            scope=scope,
            assertion=assertion,
        ),
        status=status,
    )


def test_nominal_case(testclient, logged_user, client, backend, client_jwk):
    """Per RFC 7523 §2.1, a client gets tokens with an assertion signed with its key."""
    client.client_uri = "https://client.trusted.test"
    client.redirect_uris = ["https://client.trusted.test/redirect1"]
    backend.save(client)

    scope = "openid profile email groups address phone"
    res = request_tokens(
        testclient, assertion(client, logged_user, client_jwk), 200, scope=scope
    )

    token = backend.get(models.Token, access_token=res.json["access_token"])
    assert token.client == client
    assert token.subject == logged_user
    assert set(token.scope) == set(scope.split())


def test_unknown_issuer(testclient, logged_user, client, client_jwk):
    """An assertion whose 'iss' matches no client is refused."""
    res = request_tokens(
        testclient,
        assertion(client, logged_user, client_jwk, iss="unknown-client-id"),
        400,
    )
    assert res.json["error"] == "invalid_grant"


def test_missing_issuer(testclient, logged_user, client, client_jwk):
    """An assertion without an 'iss' claim is refused."""
    res = request_tokens(
        testclient, assertion(client, logged_user, client_jwk, iss=None), 400
    )
    assert res.json["error"] == "invalid_grant"


def test_malformed_assertion(testclient, logged_user, client):
    """An assertion that is not a JWT is refused."""
    res = request_tokens(testclient, "not-a-jwt", 400)
    assert res.json["error"] == "invalid_grant"


def test_assertion_signed_by_the_server(
    testclient, logged_user, client, consent, server_jwk
):
    """Per RFC 7523 §3, an assertion is signed by its issuer, and not by Canaille."""
    res = request_tokens(testclient, assertion(client, logged_user, server_jwk), 400)
    assert res.json["error"] == "invalid_grant"


def test_issuer_audience(testclient, logged_user, client, consent, client_jwk):
    """Per draft-ietf-oauth-rfc7523bis, the issuer is a valid audience."""
    request_tokens(
        testclient,
        assertion(client, logged_user, client_jwk, aud="http://canaille.test"),
        200,
    )


def test_other_audience(testclient, logged_user, client, consent, client_jwk):
    """Per RFC 7523 §3, an assertion for another audience is refused."""
    res = request_tokens(
        testclient,
        assertion(client, logged_user, client_jwk, aud="https://other.test"),
        400,
    )
    assert res.json["error"] == "invalid_grant"


def test_several_audiences(testclient, logged_user, client, consent, client_jwk):
    """An assertion for several audiences is refused, as it could be replayed elsewhere."""
    res = request_tokens(
        testclient,
        assertion(
            client, logged_user, client_jwk, aud=["https://other.test", TOKEN_ENDPOINT]
        ),
        400,
    )
    assert res.json["error_description"] == "The 'aud' claim must have a single value."


def test_client_without_keys(
    testclient, logged_user, client, consent, client_jwk, backend
):
    """A client without public keys cannot use the JWT bearer grant."""
    client.jwks = None
    backend.save(client)

    res = request_tokens(testclient, assertion(client, logged_user, client_jwk), 400)
    assert res.json == {
        "error": "invalid_grant",
        "error_description": "The client has no public key.",
    }


def test_encryption_key(testclient, logged_user, client, consent, backend):
    """Keys published for encryption cannot sign assertions."""
    key = jwk.generate_key("RSA", 2048)
    client.jwks = json.dumps({"keys": [{**key.as_dict(private=False), "use": "enc"}]})
    backend.save(client)

    res = request_tokens(testclient, assertion(client, logged_user, key), 400)
    assert res.json["error"] == "invalid_grant"


def test_missing_subject(testclient, logged_user, client, consent, client_jwk):
    """An assertion without user is refused. Clients use client_credentials instead."""
    res = request_tokens(
        testclient, assertion(client, logged_user, client_jwk, sub=None), 400
    )
    assert res.json["error"] == "invalid_grant"


def test_replayed_assertion(testclient, logged_user, client, consent, client_jwk):
    """Per RFC 7523 §3, an assertion can only be used once."""
    client_assertion = assertion(client, logged_user, client_jwk)
    request_tokens(testclient, client_assertion, 200)

    res = request_tokens(testclient, client_assertion, 400)
    assert res.json["error_description"] == "The assertion was already used."


def test_missing_jti(testclient, logged_user, client, consent, client_jwk):
    """An assertion without 'jti' is refused, as its replay could not be detected."""
    res = request_tokens(
        testclient, assertion(client, logged_user, client_jwk, jti=None), 400
    )
    assert res.json["error"] == "invalid_grant"


def test_long_lived_assertion(testclient, logged_user, client, consent, client_jwk):
    """Per RFC 7523 §3, an assertion that expires too late is refused."""
    res = request_tokens(
        testclient,
        assertion(client, logged_user, client_jwk, exp=time.time() + 86400),
        400,
    )
    assert res.json["error_description"] == "The assertion expires too late."


def test_scope_beyond_consent(testclient, logged_user, client, consent, client_jwk):
    """The client cannot get scopes that the user did not consent to."""
    res = request_tokens(
        testclient,
        assertion(client, logged_user, client_jwk),
        400,
        scope="openid profile email",
    )
    assert res.json["error"] == "invalid_client"


def test_locked_user(testclient, logged_user, client, consent, client_jwk, backend):
    """A locked user cannot get tokens."""
    logged_user.lock_date = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
        seconds=1
    )
    backend.save(logged_user)

    res = request_tokens(testclient, assertion(client, logged_user, client_jwk), 400)
    assert res.json["error"] == "invalid_grant"
