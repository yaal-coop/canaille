import json
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest import mock

from joserfc import jws
from joserfc import jwt

from canaille.app import models
from canaille.oidc.jose import get_alg_for_key
from canaille.oidc.jose import server_jwks
from canaille.oidc.provider import get_issuer


def test_client_registration_with_authentication_jwt_token(
    testclient, backend, client, user
):
    """Test that client registration works with valid JWT token authentication."""
    assert not testclient.app.config["CANAILLE_OIDC"].get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )

    # Generate a valid JWT token
    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    client_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)

    jwt_payload = {
        "iss": get_issuer(),
        "sub": client_id,
        "aud": get_issuer(),
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "scope": "client:register",
    }

    registry = jws.JWSRegistry()
    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    payload = {
        "redirect_uris": [
            "https://client.test/callback",
            "https://client.test/callback2",
        ],
        "post_logout_redirect_uris": [
            "https://client.test/logout_callback",
        ],
        "client_name": "My Example Client",
        "token_endpoint_auth_method": "client_secret_basic",
        "logo_uri": "https://client.test/logo.webp",
        "jwks_uri": "https://client.test/my_public_keys.jwks",
        "grant_types": ["authorization_code"],
    }
    headers = {"Authorization": f"Bearer {token}"}

    res = testclient.post_json("/oauth/register", payload, headers=headers, status=201)
    created_client = backend.get(models.Client, client_id=res.json["client_id"])

    assert res.json == {
        "client_id": client_id,
        "client_secret": created_client.client_secret,
        "client_id_issued_at": mock.ANY,
        "client_name": "My Example Client",
        "client_secret_expires_at": 0,
        "jwks_uri": "https://client.test/my_public_keys.jwks",
        "logo_uri": "https://client.test/logo.webp",
        "redirect_uris": [
            "https://client.test/callback",
            "https://client.test/callback2",
        ],
        "registration_access_token": token,
        "registration_client_uri": f"http://canaille.test/oauth/register/{client_id}",
        "token_endpoint_auth_method": "client_secret_basic",
        "grant_types": ["authorization_code"],
        "scope": "",
        "application_type": "web",
        "id_token_signed_response_alg": "RS256",
        "require_auth_time": False,
        "require_signed_request_object": False,
    }

    assert created_client.client_name == "My Example Client"
    assert created_client.redirect_uris == [
        "https://client.test/callback",
        "https://client.test/callback2",
    ]
    assert created_client.post_logout_redirect_uris == [
        "https://client.test/logout_callback",
    ]
    assert created_client.token_endpoint_auth_method == "client_secret_basic"
    assert created_client.logo_uri == "https://client.test/logo.webp"
    assert created_client.jwks_uri == "https://client.test/my_public_keys.jwks"
    assert created_client in created_client.audience
    backend.delete(created_client)


def test_client_registration_with_uri_fragments(testclient, backend, client, user):
    """Test that client registration rejects redirect URIs containing fragments."""
    # Generate a valid JWT token
    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    client_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)

    jwt_payload = {
        "iss": get_issuer(),
        "sub": client_id,
        "aud": get_issuer(),
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "scope": "client:register",
    }

    registry = jws.JWSRegistry()
    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    payload = {
        "redirect_uris": [
            "https://client.example.test/callback",
            "https://client.example.test/callback2#foo",
        ],
        "post_logout_redirect_uris": [
            "https://client.example.test/logout_callback",
        ],
        "client_name": "My Example Client",
        "token_endpoint_auth_method": "client_secret_basic",
        "logo_uri": "https://client.example.test/logo.webp",
        "jwks_uri": "https://client.example.test/my_public_keys.jwks",
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
    }
    headers = {"Authorization": f"Bearer {token}"}

    res = testclient.post_json("/oauth/register", payload, headers=headers, status=400)

    assert res.json == {
        "error_description": "Invalid claim 'redirect_uris'",
        "error": "invalid_client_metadata",
    }


def test_client_registration_with_authentication_no_token(
    testclient, backend, client, user
):
    """Test that client registration requires authentication when open registration is disabled."""
    assert not testclient.app.config["CANAILLE_OIDC"].get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )

    payload = {
        "redirect_uris": [
            "https://client.test/callback",
            "https://client.test/callback2",
        ],
        "client_name": "My Example Client",
        "token_endpoint_auth_method": "client_secret_basic",
        "logo_uri": "https://client.test/logo.webp",
        "jwks_uri": "https://client.test/my_public_keys.jwks",
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
    }

    res = testclient.post_json("/oauth/register", payload, status=400)
    assert res.json == {
        "error": "access_denied",
        "error_description": "The resource owner or authorization server denied the request",
    }

    headers = {"Authorization": "Bearer"}
    res = testclient.post_json("/oauth/register", payload, headers=headers, status=400)
    assert res.json == {
        "error": "access_denied",
        "error_description": "The resource owner or authorization server denied the request",
    }


def test_client_registration_with_authentication_invalid_token(
    testclient, backend, client, user
):
    """Test that client registration rejects invalid JWT tokens."""
    assert not testclient.app.config["CANAILLE_OIDC"].get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )

    payload = {
        "redirect_uris": [
            "https://client.test/callback",
            "https://client.test/callback2",
        ],
        "client_name": "My Example Client",
        "token_endpoint_auth_method": "client_secret_basic",
        "logo_uri": "https://client.test/logo.webp",
        "jwks_uri": "https://client.test/my_public_keys.jwks",
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
    }
    headers = {"Authorization": "Bearer invalid-token"}
    res = testclient.post_json("/oauth/register", payload, headers=headers, status=400)
    assert res.json == {
        "error": "access_denied",
        "error_description": "The resource owner or authorization server denied the request",
    }


def test_client_registration_with_software_statement(testclient, backend, server_jwk):
    """Test that client registration works with software statements."""
    testclient.app.config["CANAILLE_OIDC"]["DYNAMIC_CLIENT_REGISTRATION_OPEN"] = True

    software_statement_payload = {
        "software_id": "4NRB1-0XZABZI9E6-5SM3R",
        "client_name": "Example Statement-based Client",
        "client_uri": "https://client.test/",
        "response_types": ["code"],
        "grant_types": ["authorization_code"],
    }
    software_statement_header = {"alg": "RS256"}
    software_statement = jwt.encode(
        software_statement_header, software_statement_payload, server_jwk
    )

    def test_client_registration_with_software_statement_with_different_scopes(
        scope_value, **kwargs
    ):
        payload = kwargs

        res = testclient.post_json("/oauth/register", payload, status=201)

        client = backend.get(models.Client, client_id=res.json["client_id"])
        assert res.json == {
            "client_id": client.client_id,
            "client_secret": client.client_secret,
            "client_id_issued_at": mock.ANY,
            "client_secret_expires_at": 0,
            "redirect_uris": [
                "https://client.test/callback",
                "https://client.test/callback2",
            ],
            "registration_client_uri": f"http://canaille.test/oauth/register/{client.client_id}",
            "grant_types": ["authorization_code"],
            "response_types": ["code"],
            "scope": scope_value,
            "token_endpoint_auth_method": "client_secret_basic",
            "client_name": "Example Statement-based Client",
            "client_uri": "https://client.test/",
            "software_id": "4NRB1-0XZABZI9E6-5SM3R",
            "application_type": "web",
            "id_token_signed_response_alg": "RS256",
            "require_auth_time": False,
            "require_signed_request_object": False,
        }
        assert client.redirect_uris == [
            "https://client.test/callback",
            "https://client.test/callback2",
        ]
        assert client.token_endpoint_auth_method == "client_secret_basic"
        backend.delete(client)

    test_client_registration_with_software_statement_with_different_scopes(
        "openid profile",
        redirect_uris=[
            "https://client.test/callback",
            "https://client.test/callback2",
        ],
        software_statement=software_statement,
        scope="openid profile",
    )
    test_client_registration_with_software_statement_with_different_scopes(
        "",
        redirect_uris=[
            "https://client.test/callback",
            "https://client.test/callback2",
        ],
        software_statement=software_statement,
    )


def test_client_registration_without_authentication_ok(testclient, backend):
    """Test that client registration works without authentication when open registration is enabled."""
    testclient.app.config["CANAILLE_OIDC"]["DYNAMIC_CLIENT_REGISTRATION_OPEN"] = True

    payload = {
        "redirect_uris": [
            "https://client.test/callback",
            "https://client.test/callback2",
        ],
        "client_name": "My Example Client",
        "client_uri": "https://client.test",
        "token_endpoint_auth_method": "client_secret_basic",
        "logo_uri": "https://client.test/logo.webp",
        "jwks_uri": "https://client.test/my_public_keys.jwks",
        "grant_types": ["authorization_code", "implicit"],
        "response_types": ["code", "token"],
        "scope": "openid profile",
        "contacts": ["contact@test"],
        "tos_uri": "https://client.test/uri",
        "policy_uri": "https://client.test/policy",
        "software_id": "example",
        "software_version": "x.y.z",
    }

    res = testclient.post_json("/oauth/register", payload, status=201)

    client = backend.get(models.Client, client_id=res.json["client_id"])
    assert res.json == {
        "client_id": mock.ANY,
        "client_secret": mock.ANY,
        "client_id_issued_at": mock.ANY,
        "client_name": "My Example Client",
        "client_uri": "https://client.test",
        "client_secret_expires_at": 0,
        "jwks_uri": "https://client.test/my_public_keys.jwks",
        "logo_uri": "https://client.test/logo.webp",
        "redirect_uris": [
            "https://client.test/callback",
            "https://client.test/callback2",
        ],
        "registration_client_uri": f"http://canaille.test/oauth/register/{client.client_id}",
        "token_endpoint_auth_method": "client_secret_basic",
        "grant_types": ["authorization_code", "implicit"],
        "response_types": ["code", "token"],
        "scope": "openid profile",
        "contacts": ["contact@test"],
        "tos_uri": "https://client.test/uri",
        "policy_uri": "https://client.test/policy",
        "software_id": "example",
        "software_version": "x.y.z",
        "application_type": "web",
        "id_token_signed_response_alg": "RS256",
        "require_auth_time": False,
        "require_signed_request_object": False,
    }
    assert client.client_name == "My Example Client"
    assert client.client_uri == "https://client.test"
    assert client.redirect_uris == [
        "https://client.test/callback",
        "https://client.test/callback2",
    ]
    assert client.token_endpoint_auth_method == "client_secret_basic"
    assert client.logo_uri == "https://client.test/logo.webp"
    assert client.jwks_uri == "https://client.test/my_public_keys.jwks"
    assert client.grant_types == ["authorization_code", "implicit"]
    assert set(client.response_types) == {"code", "token"}
    assert client.scope == ["openid", "profile"]
    assert client.contacts == ["contact@test"]
    assert client.tos_uri == "https://client.test/uri"
    assert client.policy_uri == "https://client.test/policy"
    assert client.software_id == "example"
    assert client.software_version == "x.y.z"
    backend.delete(client)


def test_client_registration_with_jwks(testclient, backend):
    """Nominal test case for a registration with the 'jwks' parameter."""
    testclient.app.config["CANAILLE_OIDC"]["DYNAMIC_CLIENT_REGISTRATION_OPEN"] = True

    payload = {
        "redirect_uris": [
            "https://client.test/callback",
            "https://client.test/callback2",
        ],
        "client_name": "My Example Client",
        "client_uri": "https://client.test",
        "token_endpoint_auth_method": "client_secret_basic",
        "logo_uri": "https://client.test/logo.webp",
        "grant_types": ["authorization_code", "implicit"],
        "response_types": ["code", "token"],
        "scope": "openid profile",
        "jwks": {
            "keys": [
                {
                    "alg": "RS256",
                    "e": "AQAB",
                    "kty": "RSA",
                    "n": "wbLxLf5qi3iO_3pQPbulxfPm7p5Ameeow-On-ssQBjkaOrK9ZLHQZtCDxzEw VGmWPIe5jRx3Ot97PPHZz2ldvKN6rLlG7YiXCiijuz_an-ppWC52xa0Ue6l5iSIxS7Ot6WWyxgP0wA3JrDy85TNUYZ1O3hWSSJJjgO9RpY2JZLW_UVQFOy9HdsUHio46eTQ_vCqP9sK gRz3W5Al82ZL1iZhKye86FbgHIG4SXGjQB0kopT6DEjz_Bf-rxGmD9mu7Fx6DSn7qEXQZja35ELAvtuasYHvpMYCFUXLIlzN8H_HmsMfN-Fai7_FFsuss6Cpqt0NJUSrqxRZGOsoLj4 icJw",
                    "use": "sig",
                }
            ]
        },
    }
    res = testclient.post_json("/oauth/register", payload, status=201)

    client = backend.get(models.Client, client_id=res.json["client_id"])
    assert res.json["jwks"] == {
        "keys": [
            {
                "alg": "RS256",
                "e": "AQAB",
                "kty": "RSA",
                "n": "wbLxLf5qi3iO_3pQPbulxfPm7p5Ameeow-On-ssQBjkaOrK9ZLHQZtCDxzEw VGmWPIe5jRx3Ot97PPHZz2ldvKN6rLlG7YiXCiijuz_an-ppWC52xa0Ue6l5iSIxS7Ot6WWyxgP0wA3JrDy85TNUYZ1O3hWSSJJjgO9RpY2JZLW_UVQFOy9HdsUHio46eTQ_vCqP9sK gRz3W5Al82ZL1iZhKye86FbgHIG4SXGjQB0kopT6DEjz_Bf-rxGmD9mu7Fx6DSn7qEXQZja35ELAvtuasYHvpMYCFUXLIlzN8H_HmsMfN-Fai7_FFsuss6Cpqt0NJUSrqxRZGOsoLj4 icJw",
                "use": "sig",
            }
        ]
    }
    assert json.loads(client.jwks) == {
        "keys": [
            {
                "alg": "RS256",
                "e": "AQAB",
                "kty": "RSA",
                "n": "wbLxLf5qi3iO_3pQPbulxfPm7p5Ameeow-On-ssQBjkaOrK9ZLHQZtCDxzEw VGmWPIe5jRx3Ot97PPHZz2ldvKN6rLlG7YiXCiijuz_an-ppWC52xa0Ue6l5iSIxS7Ot6WWyxgP0wA3JrDy85TNUYZ1O3hWSSJJjgO9RpY2JZLW_UVQFOy9HdsUHio46eTQ_vCqP9sK gRz3W5Al82ZL1iZhKye86FbgHIG4SXGjQB0kopT6DEjz_Bf-rxGmD9mu7Fx6DSn7qEXQZja35ELAvtuasYHvpMYCFUXLIlzN8H_HmsMfN-Fai7_FFsuss6Cpqt0NJUSrqxRZGOsoLj4 icJw",
                "use": "sig",
            }
        ]
    }

    backend.delete(client)


def test_client_registration_with_all_attributes(testclient, backend, user):
    """Test that client registration works with all supported attributes."""
    assert not testclient.app.config["CANAILLE_OIDC"].get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )

    # Generate a valid JWT token
    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    client_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)

    jwt_payload = {
        "iss": get_issuer(),
        "sub": client_id,
        "aud": get_issuer(),
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "scope": "client:register",
    }

    registry = jws.JWSRegistry()
    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    payload = {
        "redirect_uris": [
            "https://client.test/callback",
            "https://client.test/callback2",
        ],
        "client_name": "My Example Client",
        "client_uri": "https://client.test",
        "token_endpoint_auth_method": "client_secret_basic",
        "token_endpoint_auth_signing_alg": "RS256",
        "logo_uri": "https://client.test/logo.webp",
        "jwks_uri": "https://client.test/my_public_keys.jwks",
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "tos_uri": "https://client.test/uri",
        "policy_uri": "https://client.test/policy",
        "sector_identifier_uri": "https://client.test/sector.json",
        "subject_type": "public",
        "software_id": "example-software",
        "software_version": "x.y.z",
        "application_type": "web",
        "id_token_signed_response_alg": "RS256",
        "id_token_encrypted_response_alg": "RS256",
        "id_token_encrypted_response_enc": "A128CBC-HS256",
        "userinfo_signed_response_alg": "RS256",
        "userinfo_encrypted_response_alg": "RS256",
        "userinfo_encrypted_response_enc": "A128CBC-HS256",
        "default_max_age": 12345,
        "require_auth_time": True,
        "default_acr_values": ["basic", "mfa", "high"],
        "initiate_login_uri": "https://client.test/login",
        "request_object_signing_alg": "RS256",
        "request_object_encryption_alg": "RS256",
        "request_object_encryption_enc": "A128CBC-HS256",
        "request_uris": [
            "https://client.test/request_objects_1",
            "https://client.test/request_objects_2",
        ],
        "client_secret_expires_at": 0,
        "scope": "openid",
        "require_signed_request_object": True,
    }
    headers = {"Authorization": f"Bearer {token}"}

    res = testclient.post_json("/oauth/register", payload, headers=headers, status=201)

    created_client = backend.get(models.Client, client_id=res.json["client_id"])
    assert res.json == {
        "client_id": client_id,
        "client_secret": created_client.client_secret,
        "client_id_issued_at": mock.ANY,
        "registration_access_token": token,
        "registration_client_uri": f"http://canaille.test/oauth/register/{client_id}",
        **payload,
    }

    client = backend.get(models.Client, client_id=res.json["client_id"])
    for key, payload_value in payload.items():
        client_value = getattr(client, key)

        if isinstance(client_value, datetime):
            client_value = client_value.timestamp()

        if key == "scope":
            client_value = " ".join(client_value)

        assert client_value == payload_value
    backend.delete(client)


def test_client_registration_with_expired_token(testclient, backend):
    """Test that registration with expired token is rejected."""
    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    client_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    exp = now - timedelta(hours=1)

    jwt_payload = {
        "iss": get_issuer(),
        "sub": client_id,
        "aud": get_issuer(),
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "scope": "client:register",
    }

    registry = jws.JWSRegistry()
    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    payload = {
        "redirect_uris": ["https://client.test/callback"],
        "client_name": "Test Client",
    }
    headers = {"Authorization": f"Bearer {token}"}

    res = testclient.post_json("/oauth/register", payload, headers=headers, status=400)
    assert res.json["error"] == "access_denied"


def test_client_registration_with_wrong_issuer(testclient, backend):
    """Test that registration with wrong issuer is rejected."""
    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    client_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)

    jwt_payload = {
        "iss": "https://wrong.issuer",
        "sub": client_id,
        "aud": get_issuer(),
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "scope": "client:register",
    }

    registry = jws.JWSRegistry()
    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    payload = {
        "redirect_uris": ["https://client.test/callback"],
        "client_name": "Test Client",
    }
    headers = {"Authorization": f"Bearer {token}"}

    res = testclient.post_json("/oauth/register", payload, headers=headers, status=400)
    assert res.json["error"] == "access_denied"


def test_client_registration_with_wrong_audience(testclient, backend):
    """Test that registration with wrong audience is rejected."""
    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    client_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)

    jwt_payload = {
        "iss": get_issuer(),
        "sub": client_id,
        "aud": "https://wrong.audience",
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "scope": "client:register",
    }

    registry = jws.JWSRegistry()
    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    payload = {
        "redirect_uris": ["https://client.test/callback"],
        "client_name": "Test Client",
    }
    headers = {"Authorization": f"Bearer {token}"}

    res = testclient.post_json("/oauth/register", payload, headers=headers, status=400)
    assert res.json["error"] == "access_denied"


def test_client_registration_with_wrong_scope(testclient, backend):
    """Test that registration with wrong scope is rejected."""
    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    client_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)

    jwt_payload = {
        "iss": get_issuer(),
        "sub": client_id,
        "aud": get_issuer(),
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "scope": "client:manage",
    }

    registry = jws.JWSRegistry()
    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    payload = {
        "redirect_uris": ["https://client.test/callback"],
        "client_name": "Test Client",
    }
    headers = {"Authorization": f"Bearer {token}"}

    res = testclient.post_json("/oauth/register", payload, headers=headers, status=400)
    assert res.json["error"] == "access_denied"


def test_client_registration_with_existing_client_id(testclient, backend, client):
    """Test that registration with an existing client_id is rejected."""
    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)

    jwt_payload = {
        "iss": get_issuer(),
        "sub": client.client_id,
        "aud": get_issuer(),
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "scope": "client:register",
    }

    registry = jws.JWSRegistry()
    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    payload = {
        "redirect_uris": ["https://client.test/callback"],
        "client_name": "Test Client",
    }
    headers = {"Authorization": f"Bearer {token}"}

    res = testclient.post_json("/oauth/register", payload, headers=headers, status=400)
    assert res.json["error"] == "access_denied"
