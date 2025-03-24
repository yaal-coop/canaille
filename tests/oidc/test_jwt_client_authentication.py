import datetime
import logging
import time
import uuid

from joserfc import jwt
from werkzeug.security import gen_salt

from canaille import create_app
from canaille.app import models


def test_no_server_name_config(configuration, caplog):
    """Tests that SERVER_NAME is needed to enable JWT client auth."""
    del configuration["SERVER_NAME"]
    create_app(configuration)
    assert (
        "canaille",
        logging.WARNING,
        "The 'SERVER_NAME' configuration parameter is unset. JWT client authentication is disabled.",
    ) in caplog.record_tuples


def test_client_jwks(
    testclient, client_jwks, client, authorization, caplog, backend, user
):
    """Test client JWT authentication as defined per RFC7523, using the client 'jwks' attribute."""
    now = time.time()

    authorization.issue_date = datetime.datetime.now(datetime.timezone.utc)
    backend.save(authorization)
    client.trusted = True
    client.token_endpoint_auth_method = "client_secret_jwt"
    backend.save(client)

    _, private_key = client_jwks
    header = {"alg": "RS256"}
    payload = {
        "iss": client.client_id,
        "sub": client.client_id,
        "aud": "http://canaille.test/oauth/token",
        "nbf": now - 3600,
        "exp": now + 3600,
        "iat": now - 1,
        "jti": str(uuid.uuid4()),
    }
    client_jwt = jwt.encode(header, payload, private_key)
    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=authorization.code,
            code_verifier=authorization.challenge,
            client_assertion_type="urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            client_assertion=client_jwt,
            scope="openid profile email groups address phone",
            redirect_uri=client.redirect_uris[0],
        ),
        status=200,
    )

    access_token = res.json["access_token"]
    token = backend.get(models.Token, access_token=access_token)
    assert token.client == client
    assert token.subject == user


def test_client_jwks_uri(
    testclient, client_jwks, client, authorization, caplog, backend, user, httpserver
):
    """Test client JWT authentication as defined per RFC7523, using the client 'jwks_uri' attribute."""
    now = time.time()
    public_key, private_key = client_jwks

    jwks_uri = "/.well-known/jwks.json"
    httpserver.expect_request(jwks_uri).respond_with_json(
        {"keys": [public_key.as_dict()]}
    )

    authorization.issue_date = datetime.datetime.now(datetime.timezone.utc)
    backend.save(authorization)
    client.trusted = True
    client.jwks_uri = f"http://{httpserver.host}:{httpserver.port}{jwks_uri}"
    client.jwks = None
    client.token_endpoint_auth_method = "client_secret_jwt"
    backend.save(client)

    header = {"alg": "RS256"}
    payload = {
        "iss": client.client_id,
        "sub": client.client_id,
        "aud": "http://canaille.test/oauth/token",
        "nbf": now - 3600,
        "exp": now + 3600,
        "iat": now - 1,
        "jti": str(uuid.uuid4()),
    }
    client_jwt = jwt.encode(header, payload, private_key)
    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=authorization.code,
            code_verifier=authorization.challenge,
            client_assertion_type="urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            client_assertion=client_jwt,
            scope="openid profile email groups address phone",
            redirect_uri=client.redirect_uris[0],
        ),
        status=200,
    )

    access_token = res.json["access_token"]
    token = backend.get(models.Token, access_token=access_token)
    assert token.client.client_id == client.client_id
    assert token.subject == user


def test_client_no_jwks(
    testclient, client_jwks, client, authorization, caplog, backend, user
):
    """Test client JWT authentication for a client without JWK being defined."""
    now = time.time()

    authorization.issue_date = datetime.datetime.now(datetime.timezone.utc)
    backend.save(authorization)
    client.trusted = True
    client.jwks = None
    client.token_endpoint_auth_method = "client_secret_jwt"
    backend.save(client)

    _, private_key = client_jwks
    header = {"alg": "RS256"}
    payload = {
        "iss": client.client_id,
        "sub": client.client_id,
        "aud": "http://canaille.test/oauth/token",
        "nbf": now - 3600,
        "exp": now + 3600,
        "iat": now - 1,
        "jti": str(uuid.uuid4()),
    }
    client_jwt = jwt.encode(header, payload, private_key)
    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=authorization.code,
            code_verifier=authorization.challenge,
            client_assertion_type="urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            client_assertion=client_jwt,
            scope="openid profile email groups address phone",
            redirect_uri=client.redirect_uris[0],
        ),
        status=400,
    )
    assert res.json == {
        "error": "invalid_client",
        "error_description": "No matching JWK",
    }


def test_same_jti_twice(
    testclient, client_jwks, client, authorization, caplog, backend, user
):
    """Test authenticating twice with the same jti."""
    now = time.time()
    jti = str(uuid.uuid4())

    authorization.issue_date = datetime.datetime.now(datetime.timezone.utc)
    backend.save(authorization)
    client.trusted = True
    client.token_endpoint_auth_method = "client_secret_jwt"
    backend.save(client)

    _, private_key = client_jwks
    header = {"alg": "RS256"}
    payload = {
        "iss": client.client_id,
        "sub": client.client_id,
        "aud": "http://canaille.test/oauth/token",
        "nbf": now - 3600,
        "exp": now + 3600,
        "iat": now - 1,
        "jti": jti,
    }
    client_jwt = jwt.encode(header, payload, private_key)
    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=authorization.code,
            code_verifier=authorization.challenge,
            client_assertion_type="urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            client_assertion=client_jwt,
            scope="openid profile email groups address phone",
            redirect_uri=client.redirect_uris[0],
        ),
        status=200,
    )

    access_token = res.json["access_token"]
    token = backend.get(models.Token, access_token=access_token)
    assert token.client == client
    assert token.subject == user

    new_code = models.AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code="my-code",
        client=client,
        subject=user,
        redirect_uri="https://client.test/redirect1",
        response_type="code",
        scope=["openid", "profile"],
        nonce="nonce",
        issue_date=datetime.datetime.now(datetime.timezone.utc),
        lifetime=3600,
        challenge=gen_salt(48),
        challenge_method="plain",
    )
    backend.save(new_code)

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=new_code.code,
            code_verifier=new_code.challenge,
            client_assertion_type="urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            client_assertion=client_jwt,
            scope="openid profile email groups address phone",
            redirect_uri=client.redirect_uris[0],
        ),
        status=400,
    )

    assert res.json == {
        "error": "invalid_client",
        "error_description": 'Invalid claim "jti"',
    }
    backend.delete(new_code)
