from unittest import mock

from authlib.jose import jwt
from canaille.app import models


def test_client_registration_with_authentication_static_token(
    testclient, backend, client, user
):
    assert not testclient.app.config.get("OIDC", {}).get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )
    testclient.app.config["OIDC"]["DYNAMIC_CLIENT_REGISTRATION_TOKENS"] = [
        "static-token"
    ]

    payload = {
        "redirect_uris": [
            "https://client.example.org/callback",
            "https://client.example.org/callback2",
        ],
        "client_name": "My Example Client",
        "token_endpoint_auth_method": "client_secret_basic",
        "logo_uri": "https://client.example.org/logo.webp",
        "jwks_uri": "https://client.example.org/my_public_keys.jwks",
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
    }
    headers = {"Authorization": "Bearer static-token"}

    res = testclient.post_json("/oauth/register", payload, headers=headers, status=201)
    client = models.Client.get(client_id=res.json["client_id"])

    assert res.json == {
        "client_id": client.client_id,
        "client_secret": client.client_secret,
        "client_id_issued_at": mock.ANY,
        "client_name": "My Example Client",
        "client_secret_expires_at": 0,
        "jwks_uri": "https://client.example.org/my_public_keys.jwks",
        "logo_uri": "https://client.example.org/logo.webp",
        "redirect_uris": [
            "https://client.example.org/callback",
            "https://client.example.org/callback2",
        ],
        "token_endpoint_auth_method": "client_secret_basic",
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
    }

    assert client.client_name == "My Example Client"
    assert client.redirect_uris == [
        "https://client.example.org/callback",
        "https://client.example.org/callback2",
    ]
    assert client.token_endpoint_auth_method == "client_secret_basic"
    assert client.logo_uri == "https://client.example.org/logo.webp"
    assert client.jwks_uri == "https://client.example.org/my_public_keys.jwks"
    client.delete()


def test_client_registration_with_authentication_no_token(
    testclient, backend, client, user
):
    assert not testclient.app.config.get("OIDC", {}).get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )

    payload = {
        "redirect_uris": [
            "https://client.example.org/callback",
            "https://client.example.org/callback2",
        ],
        "client_name": "My Example Client",
        "token_endpoint_auth_method": "client_secret_basic",
        "logo_uri": "https://client.example.org/logo.webp",
        "jwks_uri": "https://client.example.org/my_public_keys.jwks",
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
    assert not testclient.app.config.get("OIDC", {}).get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )

    payload = {
        "redirect_uris": [
            "https://client.example.org/callback",
            "https://client.example.org/callback2",
        ],
        "client_name": "My Example Client",
        "token_endpoint_auth_method": "client_secret_basic",
        "logo_uri": "https://client.example.org/logo.webp",
        "jwks_uri": "https://client.example.org/my_public_keys.jwks",
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
    }
    headers = {"Authorization": "Bearer invalid-token"}
    res = testclient.post_json("/oauth/register", payload, headers=headers, status=400)
    assert res.json == {
        "error": "access_denied",
        "error_description": "The resource owner or authorization server denied the request",
    }


def test_client_registration_with_software_statement(testclient, backend, keypair):
    private_key, _ = keypair
    testclient.app.config["OIDC"]["DYNAMIC_CLIENT_REGISTRATION_OPEN"] = True

    software_statement_payload = {
        "software_id": "4NRB1-0XZABZI9E6-5SM3R",
        "client_name": "Example Statement-based Client",
        "client_uri": "https://client.example.net/",
        "response_types": ["code"],
        "grant_types": ["authorization_code"],
    }
    software_statement_header = {"alg": "RS256"}
    software_statement = jwt.encode(
        software_statement_header, software_statement_payload, private_key
    ).decode()

    payload = {
        "redirect_uris": [
            "https://client.example.org/callback",
            "https://client.example.org/callback2",
        ],
        "software_statement": software_statement,
        "scope": "openid profile",
    }
    res = testclient.post_json("/oauth/register", payload, status=201)

    client = models.Client.get(client_id=res.json["client_id"])
    assert res.json == {
        "client_id": client.client_id,
        "client_secret": client.client_secret,
        "client_id_issued_at": mock.ANY,
        "client_secret_expires_at": 0,
        "redirect_uris": [
            "https://client.example.org/callback",
            "https://client.example.org/callback2",
        ],
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "scope": "openid profile",
        "token_endpoint_auth_method": "client_secret_basic",
        "client_name": "Example Statement-based Client",
        "client_uri": "https://client.example.net/",
        "software_id": "4NRB1-0XZABZI9E6-5SM3R",
    }
    assert client.redirect_uris == [
        "https://client.example.org/callback",
        "https://client.example.org/callback2",
    ]
    assert client.token_endpoint_auth_method == "client_secret_basic"
    client.delete()


def test_client_registration_without_authentication_ok(testclient, backend):
    testclient.app.config["OIDC"]["DYNAMIC_CLIENT_REGISTRATION_OPEN"] = True

    payload = {
        "redirect_uris": [
            "https://client.example.org/callback",
            "https://client.example.org/callback2",
        ],
        "client_name": "My Example Client",
        "client_uri": "https://example.com",
        "token_endpoint_auth_method": "client_secret_basic",
        "logo_uri": "https://client.example.org/logo.webp",
        "jwks_uri": "https://client.example.org/my_public_keys.jwks",
        "grant_types": ["authorization_code", "implicit"],
        "response_types": ["code", "token"],
        "scope": "openid profile",
        "contacts": ["contact@example.com"],
        "tos_uri": "https://example.com/uri",
        "policy_uri": "https://example.com/policy",
        "software_id": "example",
        "software_version": "x.y.z",
    }

    res = testclient.post_json("/oauth/register", payload, status=201)

    client = models.Client.get(client_id=res.json["client_id"])
    assert res.json == {
        "client_id": mock.ANY,
        "client_secret": mock.ANY,
        "client_id_issued_at": mock.ANY,
        "client_name": "My Example Client",
        "client_uri": "https://example.com",
        "client_secret_expires_at": 0,
        "jwks_uri": "https://client.example.org/my_public_keys.jwks",
        "logo_uri": "https://client.example.org/logo.webp",
        "redirect_uris": [
            "https://client.example.org/callback",
            "https://client.example.org/callback2",
        ],
        "token_endpoint_auth_method": "client_secret_basic",
        "grant_types": ["authorization_code", "implicit"],
        "response_types": ["code", "token"],
        "scope": "openid profile",
        "contacts": ["contact@example.com"],
        "tos_uri": "https://example.com/uri",
        "policy_uri": "https://example.com/policy",
        "software_id": "example",
        "software_version": "x.y.z",
    }
    assert client.client_name == "My Example Client"
    assert client.client_uri == "https://example.com"
    assert client.redirect_uris == [
        "https://client.example.org/callback",
        "https://client.example.org/callback2",
    ]
    assert client.token_endpoint_auth_method == "client_secret_basic"
    assert client.logo_uri == "https://client.example.org/logo.webp"
    assert client.jwks_uri == "https://client.example.org/my_public_keys.jwks"
    assert client.grant_types == ["authorization_code", "implicit"]
    assert client.response_types == ["code", "token"]
    assert client.scope == ["openid", "profile"]
    assert client.contacts == ["contact@example.com"]
    assert client.tos_uri == "https://example.com/uri"
    assert client.policy_uri == "https://example.com/policy"
    assert client.software_id == "example"
    assert client.software_version == "x.y.z"
    client.delete()
