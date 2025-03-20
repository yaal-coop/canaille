import json
from datetime import datetime
from unittest import mock

from authlib.jose import jwt

from canaille.app import models


def test_client_registration_with_authentication_static_token(
    testclient, backend, client, user
):
    assert not testclient.app.config["CANAILLE_OIDC"].get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )
    testclient.app.config["CANAILLE_OIDC"]["DYNAMIC_CLIENT_REGISTRATION_TOKENS"] = [
        "static-token"
    ]

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
        "response_types": ["code"],
    }
    headers = {"Authorization": "Bearer static-token"}

    res = testclient.post_json("/oauth/register", payload, headers=headers, status=201)
    client = backend.get(models.Client, client_id=res.json["client_id"])

    assert res.json == {
        "client_id": client.client_id,
        "client_secret": client.client_secret,
        "client_id_issued_at": mock.ANY,
        "client_name": "My Example Client",
        "client_secret_expires_at": 0,
        "jwks_uri": "https://client.test/my_public_keys.jwks",
        "logo_uri": "https://client.test/logo.webp",
        "redirect_uris": [
            "https://client.test/callback",
            "https://client.test/callback2",
        ],
        "token_endpoint_auth_method": "client_secret_basic",
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "scope": "openid",
        "application_type": "web",
        "id_token_signed_response_alg": "RS256",
        "require_auth_time": False,
    }

    assert client.client_name == "My Example Client"
    assert client.redirect_uris == [
        "https://client.test/callback",
        "https://client.test/callback2",
    ]
    assert client.post_logout_redirect_uris == [
        "https://client.test/logout_callback",
    ]
    assert client.token_endpoint_auth_method == "client_secret_basic"
    assert client.logo_uri == "https://client.test/logo.webp"
    assert client.jwks_uri == "https://client.test/my_public_keys.jwks"
    assert client in client.audience
    backend.delete(client)


def test_client_registration_with_uri_fragments(testclient, backend, client, user):
    testclient.app.config["CANAILLE_OIDC"]["DYNAMIC_CLIENT_REGISTRATION_TOKENS"] = [
        "static-token"
    ]

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
    headers = {"Authorization": "Bearer static-token"}

    res = testclient.post_json("/oauth/register", payload, headers=headers, status=400)

    assert res.json == {
        "error_description": "Redirect URI cannot contain fragment identifiers",
        "error": "invalid_request",
        "iss": "https://auth.test",
    }


def test_client_registration_with_authentication_no_token(
    testclient, backend, client, user
):
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


def test_client_registration_with_software_statement(testclient, backend, keypair):
    private_key, _ = keypair
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
        software_statement_header, software_statement_payload, private_key
    ).decode()

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
        "openid",
        redirect_uris=[
            "https://client.test/callback",
            "https://client.test/callback2",
        ],
        software_statement=software_statement,
    )


def test_client_registration_without_authentication_ok(testclient, backend):
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
    assert client.response_types == ["code", "token"]
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
    assert not testclient.app.config["CANAILLE_OIDC"].get(
        "DYNAMIC_CLIENT_REGISTRATION_OPEN"
    )
    testclient.app.config["CANAILLE_OIDC"]["DYNAMIC_CLIENT_REGISTRATION_TOKENS"] = [
        "static-token"
    ]

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
    }
    headers = {"Authorization": "Bearer static-token"}

    res = testclient.post_json("/oauth/register", payload, headers=headers, status=201)

    client = backend.get(models.Client, client_id=res.json["client_id"])
    assert res.json == {
        "client_id": client.client_id,
        "client_secret": client.client_secret,
        "client_id_issued_at": mock.ANY,
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
