from flask import g


def test_oauth_authorization_server(testclient):
    res = testclient.get("/.well-known/oauth-authorization-server", status=200).json
    assert "https://auth.mydomain.tld" == res["issuer"]
    assert res == {
        "authorization_endpoint": "http://localhost.local/oauth/authorize",
        "code_challenge_methods_supported": ["plain", "S256"],
        "introspection_endpoint": "http://localhost.local/oauth/introspect",
        "issuer": "https://auth.mydomain.tld",
        "jwks_uri": "http://localhost.local/oauth/jwks.json",
        "registration_endpoint": "http://localhost.local/oauth/register",
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
        "token_endpoint": "http://localhost.local/oauth/token",
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "private_key_jwt",
            "client_secret_post",
            "none",
        ],
        "token_endpoint_auth_signing_alg_values_supported": ["RS256", "ES256"],
        "ui_locales_supported": g.available_language_codes,
        "userinfo_endpoint": "http://localhost.local/oauth/userinfo",
    }


def test_openid_configuration(testclient):
    res = testclient.get("/.well-known/openid-configuration", status=200).json
    assert "https://auth.mydomain.tld" == res["issuer"]
    assert res == {
        "authorization_endpoint": "http://localhost.local/oauth/authorize",
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
        "end_session_endpoint": "http://localhost.local/oauth/end_session",
        "id_token_signing_alg_values_supported": ["RS256", "ES256", "HS256"],
        "introspection_endpoint": "http://localhost.local/oauth/introspect",
        "issuer": "https://auth.mydomain.tld",
        "jwks_uri": "http://localhost.local/oauth/jwks.json",
        "registration_endpoint": "http://localhost.local/oauth/register",
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
        "token_endpoint": "http://localhost.local/oauth/token",
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "private_key_jwt",
            "client_secret_post",
            "none",
        ],
        "token_endpoint_auth_signing_alg_values_supported": ["RS256", "ES256"],
        "ui_locales_supported": g.available_language_codes,
        "userinfo_endpoint": "http://localhost.local/oauth/userinfo",
    }
