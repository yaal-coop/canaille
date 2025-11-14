import json
import uuid
import warnings
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from joserfc import jwt
from joserfc.jwk import KeySet

from canaille.app import models
from canaille.oidc.jose import get_alg_for_key
from canaille.oidc.jose import registry
from canaille.oidc.jose import server_jwks
from canaille.oidc.provider import get_issuer


def test_get(testclient, backend, client, user, client_jwk):
    """Test that retrieving client configuration works with valid management token."""
    key_set = KeySet([client_jwk]).as_dict(private=False)
    assert not testclient.app.config["CANAILLE_OIDC"].get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )

    # Generate a valid JWT token for management
    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)

    jwt_payload = {
        "iss": get_issuer(),
        "exp": int(exp.timestamp()),
        "aud": get_issuer(),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "sub": client.client_id,
        "scope": "client:manage",
    }

    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    headers = {"Authorization": f"Bearer {token}"}
    res = testclient.get(
        f"/oauth/register/{client.client_id}", headers=headers, status=200
    )
    assert res.json == {
        "application_type": None,
        "client_id": client.client_id,
        "client_secret": client.client_secret,
        "client_id_issued_at": int(datetime.timestamp(client.client_id_issued_at)),
        "client_secret_expires_at": 0,
        "default_acr_values": [],
        "default_max_age": None,
        "redirect_uris": [
            "https://client.test/redirect1",
            "https://client.test/redirect2",
        ],
        "registration_access_token": token,
        "registration_client_uri": f"http://canaille.test/oauth/register/{client.client_id}",
        "token_endpoint_auth_method": "client_secret_basic",
        "grant_types": [
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
            "client_credentials",
            "urn:ietf:params:oauth:grant-type:jwt-bearer",
        ],
        "id_token_encrypted_response_alg": None,
        "id_token_encrypted_response_enc": None,
        "id_token_signed_response_alg": None,
        "initiate_login_uri": None,
        "response_types": ["code", "token", "id_token"],
        "client_name": "Some client",
        "client_uri": "https://client.test",
        "logo_uri": "https://client.test/logo.webp",
        "request_object_encryption_alg": None,
        "request_object_encryption_enc": None,
        "request_object_signing_alg": None,
        "request_uris": [],
        "require_auth_time": None,
        "scope": "openid email profile groups address phone",
        "sector_identifier_uri": None,
        "subject_type": None,
        "contacts": ["contact@mydomain.test"],
        "token_endpoint_auth_signing_alg": None,
        "tos_uri": "https://client.test/tos",
        "policy_uri": "https://client.test/policy",
        "jwks": json.dumps(key_set),
        "jwks_uri": None,
        "software_id": None,
        "software_version": None,
        "userinfo_encrypted_response_alg": None,
        "userinfo_encrypted_response_enc": None,
        "userinfo_signed_response_alg": None,
        "require_signed_request_object": None,
    }


def test_update(testclient, backend, client, user, client_jwk):
    """Test that updating client configuration works with valid management token."""
    key_set = KeySet([client_jwk]).as_dict(private=False)
    assert not testclient.app.config["CANAILLE_OIDC"].get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )

    # Generate a valid JWT token for management
    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)

    jwt_payload = {
        "iss": get_issuer(),
        "exp": int(exp.timestamp()),
        "aud": get_issuer(),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "sub": client.client_id,
        "scope": "client:manage",
    }

    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    assert client.redirect_uris != ["https://newname.example.test/callback"]
    assert client.token_endpoint_auth_method != "none"
    assert client.grant_types != ["refresh_token"]
    assert client.response_types != ["code"]
    assert client.client_name != "new name"
    assert client.client_uri != "https://newname.example.test"
    assert client.logo_uri != "https://newname.example.test/logo.webp"
    assert client.scope != ["openid", "profile", "email"]
    assert client.contacts != ["newcontact@example.test"]
    assert client.tos_uri != "https://newname.example.test/tos"
    assert client.policy_uri != "https://newname.example.test/policy"
    assert client.jwks_uri != "https://newname.example.test/my_public_keys.jwks"
    assert client.software_id != "new_software_id"
    assert client.software_version != "3.14"

    payload = {
        "client_id": client.client_id,
        "redirect_uris": ["https://newname.example.test/callback"],
        "token_endpoint_auth_method": "none",
        "grant_types": ["refresh_token"],
        "response_types": ["code"],
        "client_name": "new name",
        "client_uri": "https://newname.example.test",
        "logo_uri": "https://newname.example.test/logo.webp",
        "scope": "openid profile email",
        "contacts": ["newcontact@example.test"],
        "tos_uri": "https://newname.example.test/tos",
        "policy_uri": "https://newname.example.test/policy",
        "jwks_uri": "https://newname.example.test/my_public_keys.jwks",
        "require_auth_time": True,
        "software_id": "new_software_id",
        "software_version": "3.14",
    }

    headers = {"Authorization": f"Bearer {token}"}
    res = testclient.put_json(
        f"/oauth/register/{client.client_id}", payload, headers=headers, status=200
    )
    client = backend.get(models.Client, client_id=res.json["client_id"])

    assert res.json == {
        "application_type": "web",
        "client_id": client.client_id,
        "client_secret": client.client_secret,
        "client_id_issued_at": int(datetime.timestamp(client.client_id_issued_at)),
        "client_secret_expires_at": 0,
        "default_acr_values": [],
        "default_max_age": None,
        "id_token_encrypted_response_alg": None,
        "id_token_encrypted_response_enc": None,
        "id_token_signed_response_alg": "RS256",
        "initiate_login_uri": None,
        "redirect_uris": ["https://newname.example.test/callback"],
        "registration_access_token": token,
        "registration_client_uri": f"http://canaille.test/oauth/register/{client.client_id}",
        "request_object_encryption_alg": None,
        "request_object_encryption_enc": None,
        "request_object_signing_alg": None,
        "request_uris": [],
        "require_auth_time": True,
        "token_endpoint_auth_method": "none",
        "grant_types": ["refresh_token"],
        "response_types": ["code"],
        "client_name": "new name",
        "client_uri": "https://newname.example.test",
        "logo_uri": "https://newname.example.test/logo.webp",
        "scope": "openid profile email",
        "sector_identifier_uri": None,
        "subject_type": None,
        "contacts": ["newcontact@example.test"],
        "token_endpoint_auth_signing_alg": None,
        "tos_uri": "https://newname.example.test/tos",
        "policy_uri": "https://newname.example.test/policy",
        "jwks": json.dumps(key_set),
        "jwks_uri": "https://newname.example.test/my_public_keys.jwks",
        "software_id": "new_software_id",
        "software_version": "3.14",
        "userinfo_encrypted_response_alg": None,
        "userinfo_encrypted_response_enc": None,
        "userinfo_signed_response_alg": None,
        "require_signed_request_object": False,
    }

    assert client.redirect_uris == ["https://newname.example.test/callback"]
    assert client.token_endpoint_auth_method == "none"
    assert client.grant_types == ["refresh_token"]
    assert client.response_types == ["code"]
    assert client.client_name == "new name"
    assert client.client_uri == "https://newname.example.test"
    assert client.logo_uri == "https://newname.example.test/logo.webp"
    assert client.scope == ["openid", "profile", "email"]
    assert client.contacts == ["newcontact@example.test"]
    assert client.tos_uri == "https://newname.example.test/tos"
    assert client.policy_uri == "https://newname.example.test/policy"
    assert client.jwks_uri == "https://newname.example.test/my_public_keys.jwks"
    assert client.software_id == "new_software_id"
    assert client.software_version == "3.14"


def test_delete(testclient, backend, user):
    """Test that deleting a client works with valid management token."""
    assert not testclient.app.config["CANAILLE_OIDC"].get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )

    client = models.Client(client_id="foobar", client_name="Some client")
    backend.save(client)

    # Generate a valid JWT token for management
    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)

    jwt_payload = {
        "iss": get_issuer(),
        "exp": int(exp.timestamp()),
        "aud": get_issuer(),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "sub": client.client_id,
        "scope": "client:manage",
    }

    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    headers = {"Authorization": f"Bearer {token}"}
    with warnings.catch_warnings(record=True):
        testclient.delete(
            f"/oauth/register/{client.client_id}", headers=headers, status=204
        )
    assert not backend.get(models.Client, client_id=client.client_id)


def test_invalid_client(testclient, backend, user):
    """Test that managing a non-existent client returns an error."""
    assert not testclient.app.config["CANAILLE_OIDC"].get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )

    # Generate a valid JWT token for management of a non-existent client
    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)

    jwt_payload = {
        "iss": get_issuer(),
        "exp": int(exp.timestamp()),
        "aud": get_issuer(),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "sub": "invalid-client-id",
        "scope": "client:manage",
    }

    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    payload = {
        "client_id": "invalid-client-id",
        "redirect_uris": ["https://newname.example.test/callback"],
    }

    headers = {"Authorization": f"Bearer {token}"}
    res = testclient.put_json(
        "/oauth/register/invalid-client-id", payload, headers=headers, status=400
    )
    assert res.json == {
        "error": "access_denied",
        "error_description": "The resource owner or authorization server denied the request",
    }


def test_management_with_expired_token(testclient, backend, client):
    """Test that management with expired token is rejected."""
    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    now = datetime.now(timezone.utc)
    exp = now - timedelta(hours=1)

    jwt_payload = {
        "iss": get_issuer(),
        "sub": client.client_id,
        "aud": get_issuer(),
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "scope": "client:manage",
    }

    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    headers = {"Authorization": f"Bearer {token}"}
    res = testclient.get(
        f"/oauth/register/{client.client_id}", headers=headers, status=400
    )
    assert res.json["error"] == "access_denied"


def test_management_with_wrong_issuer(testclient, backend, client):
    """Test that management with wrong issuer is rejected."""
    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)

    jwt_payload = {
        "iss": "https://wrong.issuer",
        "sub": client.client_id,
        "aud": get_issuer(),
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "scope": "client:manage",
    }

    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    headers = {"Authorization": f"Bearer {token}"}
    res = testclient.get(
        f"/oauth/register/{client.client_id}", headers=headers, status=400
    )
    assert res.json["error"] == "access_denied"


def test_management_with_wrong_audience(testclient, backend, client):
    """Test that management with wrong audience is rejected."""
    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=1)

    jwt_payload = {
        "iss": get_issuer(),
        "sub": client.client_id,
        "aud": "https://wrong.audience",
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "scope": "client:manage",
    }

    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    headers = {"Authorization": f"Bearer {token}"}
    res = testclient.get(
        f"/oauth/register/{client.client_id}", headers=headers, status=400
    )
    assert res.json["error"] == "access_denied"


def test_management_with_wrong_scope(testclient, backend, client):
    """Test that management with wrong scope is rejected."""
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

    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    headers = {"Authorization": f"Bearer {token}"}
    res = testclient.get(
        f"/oauth/register/{client.client_id}", headers=headers, status=400
    )
    assert res.json["error"] == "access_denied"
