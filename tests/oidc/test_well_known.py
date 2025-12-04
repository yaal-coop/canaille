from flask import g


def test_oauth_authorization_server(testclient):
    res = testclient.get("/.well-known/oauth-authorization-server", status=200).json
    assert "http://canaille.test" == res["issuer"]
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
        "issuer": "http://canaille.test",
        "jwks_uri": "http://canaille.test/oauth/jwks.json",
        "registration_endpoint": "http://canaille.test/oauth/register",
        "response_types_supported": [
            "code",
            "token",
            "id_token",
            "code token",
            "code id_token",
            "token id_token",
            "code id_token token",
        ],
        "revocation_endpoint": "http://canaille.test/oauth/revoke",
        "revocation_endpoint_auth_methods_supported": [
            "client_secret_basic",
        ],
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
        "token_endpoint_auth_signing_alg_values_supported": [
            "HS256",
            "HS384",
            "HS512",
            "RS256",
            "RS384",
            "RS512",
            "ES256",
            "ES384",
            "ES512",
            "PS256",
            "PS384",
            "PS512",
            "EdDSA",
            "ES256K",
            "Ed25519",
            "Ed448",
        ],
        "ui_locales_supported": g.available_language_codes,
        "userinfo_endpoint": "http://canaille.test/oauth/userinfo",
        "authorization_response_iss_parameter_supported": True,
    }


def test_openid_configuration(testclient):
    """Test openid-configuration endpoint.

    The fixture uses an RSA key, so server signing algorithms are RSA-based.
    """
    res = testclient.get("/.well-known/openid-configuration", status=200).json
    assert "http://canaille.test" == res["issuer"]
    assert res == {
        "authorization_endpoint": "http://canaille.test/oauth/authorize",
        "claim_types_supported": [
            "normal",
        ],
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
        "end_session_endpoint": "http://canaille.test/oauth/end_session",
        "grant_types_supported": [
            "authorization_code",
            "implicit",
            "password",
            "client_credentials",
            "refresh_token",
        ],
        "id_token_signing_alg_values_supported": [
            "none",
            "RS256",
            "RS384",
            "RS512",
            "PS256",
            "PS384",
            "PS512",
        ],
        "userinfo_signing_alg_values_supported": [
            "none",
            "RS256",
            "RS384",
            "RS512",
            "PS256",
            "PS384",
            "PS512",
        ],
        "introspection_endpoint": "http://canaille.test/oauth/introspect",
        "introspection_endpoint_auth_methods_supported": ["client_secret_basic"],
        "issuer": "http://canaille.test",
        "jwks_uri": "http://canaille.test/oauth/jwks.json",
        "registration_endpoint": "http://canaille.test/oauth/register",
        "request_parameter_supported": True,
        "request_uri_parameter_supported": True,
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
            "code id_token token",
        ],
        "revocation_endpoint": "http://canaille.test/oauth/revoke",
        "revocation_endpoint_auth_methods_supported": [
            "client_secret_basic",
        ],
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
        "token_endpoint_auth_signing_alg_values_supported": [
            "HS256",
            "HS384",
            "HS512",
            "RS256",
            "RS384",
            "RS512",
            "ES256",
            "ES384",
            "ES512",
            "PS256",
            "PS384",
            "PS512",
            "EdDSA",
            "ES256K",
            "Ed25519",
            "Ed448",
        ],
        "ui_locales_supported": g.available_language_codes,
        "userinfo_endpoint": "http://canaille.test/oauth/userinfo",
        "prompt_values_supported": ["none", "login", "consent", "select_account"],
        "authorization_response_iss_parameter_supported": True,
        "request_object_signing_alg_values_supported": [
            "none",
            "HS256",
            "HS384",
            "HS512",
            "RS256",
            "RS384",
            "RS512",
            "ES256",
            "ES384",
            "ES512",
            "PS256",
            "PS384",
            "PS512",
            "EdDSA",
            "ES256K",
            "Ed25519",
            "Ed448",
        ],
    }


def test_openid_configuration_prompt_value_create(testclient):
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    res = testclient.get("/.well-known/openid-configuration", status=200).json
    assert "create" in res["prompt_values_supported"]


def test_signing_alg_with_rsa_key(testclient):
    """Test that RSA keys expose RS256/RS384/RS512/PS256/PS384/PS512 algorithms."""
    res = testclient.get("/.well-known/openid-configuration", status=200).json

    expected_server_algs = [
        "none",
        "RS256",
        "RS384",
        "RS512",
        "PS256",
        "PS384",
        "PS512",
    ]
    assert res["id_token_signing_alg_values_supported"] == expected_server_algs
    assert res["userinfo_signing_alg_values_supported"] == expected_server_algs


def test_signing_alg_with_ec_p256_key(testclient, server_jwk, ec_jwk):
    """Test that EC P-256 keys expose ES256 algorithm.

    Note: OIDC Discovery spec requires RS256, so we include an RSA key too.
    """
    testclient.app.config["CANAILLE_OIDC"]["ACTIVE_JWKS"] = [
        ec_jwk.as_dict(),
        server_jwk.as_dict(),
    ]

    res = testclient.get("/.well-known/openid-configuration", status=200).json

    assert "ES256" in res["id_token_signing_alg_values_supported"]
    assert "RS256" in res["id_token_signing_alg_values_supported"]


def test_signing_alg_with_ed25519_key(testclient, server_jwk, okp_jwk):
    """Test that Ed25519 keys expose EdDSA algorithm.

    Note: OIDC Discovery spec requires RS256, so we include an RSA key too.
    """
    testclient.app.config["CANAILLE_OIDC"]["ACTIVE_JWKS"] = [
        okp_jwk.as_dict(),
        server_jwk.as_dict(),
    ]

    res = testclient.get("/.well-known/openid-configuration", status=200).json

    assert "EdDSA" in res["id_token_signing_alg_values_supported"]
    assert "RS256" in res["id_token_signing_alg_values_supported"]


def test_signing_alg_with_multiple_keys(testclient, server_jwk, ec_jwk, okp_jwk):
    """Test that multiple keys combine their algorithms without duplicates."""
    testclient.app.config["CANAILLE_OIDC"]["ACTIVE_JWKS"] = [
        server_jwk.as_dict(),
        ec_jwk.as_dict(),
        okp_jwk.as_dict(),
    ]

    res = testclient.get("/.well-known/openid-configuration", status=200).json

    expected_server_algs = [
        "none",
        "RS256",
        "RS384",
        "RS512",
        "PS256",
        "PS384",
        "PS512",
        "ES256",
        "EdDSA",
        "Ed25519",
    ]
    assert res["id_token_signing_alg_values_supported"] == expected_server_algs
    assert res["userinfo_signing_alg_values_supported"] == expected_server_algs


def test_token_endpoint_auth_alg_is_static(testclient):
    """Test that token_endpoint_auth_signing_alg_values_supported doesn't include 'none'.

    Per OIDC spec, 'none' MUST NOT be used for token endpoint authentication.
    """
    res = testclient.get("/.well-known/openid-configuration", status=200).json

    assert "none" not in res["token_endpoint_auth_signing_alg_values_supported"]
    assert "RS256" in res["token_endpoint_auth_signing_alg_values_supported"]


def test_request_object_alg_includes_none(testclient):
    """Test that request_object_signing_alg_values_supported includes 'none'.

    Per OIDC spec, 'none' MAY be used for request object signing.
    """
    res = testclient.get("/.well-known/openid-configuration", status=200).json

    assert "none" in res["request_object_signing_alg_values_supported"]
    assert res["request_object_signing_alg_values_supported"][0] == "none"
