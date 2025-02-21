from flask import g


def test_oauth_authorization_server(testclient):
    res = testclient.get("/.well-known/oauth-authorization-server", status=200).json
    assert "https://auth.test" == res["issuer"]
    assert res == {
        "authorization_endpoint": "http://canaille.test/oauth/authorize",
        "code_challenge_methods_supported": ["plain", "S256"],
        "grant_types_supported": [
            "authorization_code",
            "implicit",
            "password",
            "client_credentials",
            "refresh_token",
        ],
        "introspection_endpoint": "http://canaille.test/oauth/introspect",
        "introspection_endpoint_auth_methods_supported": ["client_secret_basic"],
        "introspection_endpoint_auth_signing_alg_values_supported": None,
        "issuer": "https://auth.test",
        "jwks_uri": "http://canaille.test/oauth/jwks.json",
        "op_policy_uri": None,
        "op_tos_uri": None,
        "registration_endpoint": "http://canaille.test/oauth/register",
        "response_types_supported": [
            "code",
            "token",
            "id_token",
            "code token",
            "code id_token",
            "token id_token",
        ],
        "revocation_endpoint": "http://canaille.test/oauth/revoke",
        "revocation_endpoint_auth_methods_supported": [
            "client_secret_basic",
        ],
        "revocation_endpoint_auth_signing_alg_values_supported": None,
        "scopes_supported": [
            "openid",
            "profile",
            "email",
            "address",
            "phone",
            "groups",
        ],
        "service_documentation": "https://canaille.readthedocs.io",
        "token_endpoint": "http://canaille.test/oauth/token",
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "private_key_jwt",
            "client_secret_post",
            "none",
        ],
        "token_endpoint_auth_signing_alg_values_supported": ["RS256", "ES256"],
        "ui_locales_supported": g.available_language_codes,
        "userinfo_endpoint": "http://canaille.test/oauth/userinfo",
        "authorization_response_iss_parameter_supported": True,
    }


def test_openid_configuration(testclient):
    res = testclient.get("/.well-known/openid-configuration", status=200).json
    assert "https://auth.test" == res["issuer"]
    assert res == {
        "acr_values_supported": None,
        "authorization_endpoint": "http://canaille.test/oauth/authorize",
        "claim_types_supported": [
            "normal",
        ],
        "claims_locales_supported": None,
        "claims_parameter_supported": False,
        "claims_supported": [
            "sub",
            "iss",
            "auth_time",
            "acr",
            "name",
            "given_name",
            "family_name",
            "nickname",
            "profile",
            "picture",
            "website",
            "email",
            "email_verified",
            "locale",
            "zoneinfo",
            "groups",
            "nonce",
        ],
        "code_challenge_methods_supported": ["plain", "S256"],
        "display_values_supported": None,
        "end_session_endpoint": "http://canaille.test/oauth/end_session",
        "grant_types_supported": [
            "authorization_code",
            "implicit",
            "password",
            "client_credentials",
            "refresh_token",
        ],
        "id_token_encryption_alg_values_supported": None,
        "id_token_encryption_enc_values_supported": None,
        "id_token_signing_alg_values_supported": ["RS256", "ES256", "HS256"],
        "userinfo_signing_alg_values_supported": ["RS256"],
        "introspection_endpoint": "http://canaille.test/oauth/introspect",
        "introspection_endpoint_auth_methods_supported": ["client_secret_basic"],
        "introspection_endpoint_auth_signing_alg_values_supported": None,
        "issuer": "https://auth.test",
        "jwks_uri": "http://canaille.test/oauth/jwks.json",
        "op_policy_uri": None,
        "op_tos_uri": None,
        "registration_endpoint": "http://canaille.test/oauth/register",
        "request_object_encryption_alg_values_supported": None,
        "request_object_encryption_enc_values_supported": None,
        "request_object_signing_alg_values_supported": [
            "none",
            "RS256",
        ],
        "request_parameter_supported": False,
        "request_uri_parameter_supported": False,
        "require_request_uri_registration": False,
        "response_modes_supported": [
            "query",
            "fragment",
        ],
        "response_types_supported": [
            "code",
            "token",
            "id_token",
            "code token",
            "code id_token",
            "token id_token",
        ],
        "revocation_endpoint": "http://canaille.test/oauth/revoke",
        "revocation_endpoint_auth_methods_supported": [
            "client_secret_basic",
        ],
        "revocation_endpoint_auth_signing_alg_values_supported": None,
        "scopes_supported": [
            "openid",
            "profile",
            "email",
            "address",
            "phone",
            "groups",
        ],
        "service_documentation": "https://canaille.readthedocs.io",
        "subject_types_supported": ["public"],
        "token_endpoint": "http://canaille.test/oauth/token",
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "private_key_jwt",
            "client_secret_post",
            "none",
        ],
        "token_endpoint_auth_signing_alg_values_supported": ["RS256", "ES256"],
        "ui_locales_supported": g.available_language_codes,
        "userinfo_endpoint": "http://canaille.test/oauth/userinfo",
        "userinfo_encryption_alg_values_supported": None,
        "userinfo_encryption_enc_values_supported": None,
        "prompt_values_supported": ["none"],
        "authorization_response_iss_parameter_supported": True,
    }


def test_openid_configuration_prompt_value_create(testclient):
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    res = testclient.get("/.well-known/openid-configuration", status=200).json
    assert "create" in res["prompt_values_supported"]
