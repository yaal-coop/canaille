from flask import g


def test_oauth_authorization_server(testclient):
    res = testclient.get("/.well-known/oauth-authorization-server", status=200).json
    assert "https://auth.mydomain.test" == res["issuer"]
    assert res == {
        "authorization_endpoint": "http://canaille.test/oauth/authorize",
        "code_challenge_methods_supported": ["plain", "S256"],
        "introspection_endpoint": "http://canaille.test/oauth/introspect",
        "issuer": "https://auth.mydomain.test",
        "jwks_uri": "http://canaille.test/oauth/jwks.json",
        "registration_endpoint": "http://canaille.test/oauth/register",
        "response_types_supported": [
            "code",
            "token",
            "id_token",
            "code token",
            "code id_token",
            "token id_token",
        ],
        "scopes_supported": [
            "openid",
            "profile",
            "email",
            "address",
            "phone",
            "groups",
        ],
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
    }


def test_openid_configuration(testclient):
    res = testclient.get("/.well-known/openid-configuration", status=200).json
    assert "https://auth.mydomain.test" == res["issuer"]
    assert res == {
        "authorization_endpoint": "http://canaille.test/oauth/authorize",
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
        "id_token_signing_alg_values_supported": ["RS256", "ES256", "HS256"],
        "introspection_endpoint": "http://canaille.test/oauth/introspect",
        "issuer": "https://auth.mydomain.test",
        "jwks_uri": "http://canaille.test/oauth/jwks.json",
        "registration_endpoint": "http://canaille.test/oauth/register",
        "response_types_supported": [
            "code",
            "token",
            "id_token",
            "code token",
            "code id_token",
            "token id_token",
        ],
        "scopes_supported": [
            "openid",
            "profile",
            "email",
            "address",
            "phone",
            "groups",
        ],
        "subject_types_supported": ["pairwise", "public"],
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
        "prompt_values_supported": ["none"],
    }


def test_openid_configuration_prompt_value_create(testclient):
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    res = testclient.get("/.well-known/openid-configuration", status=200).json
    assert "create" in res["prompt_values_supported"]
