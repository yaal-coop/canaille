from werkzeug.security import gen_salt

from canaille.app import models
from canaille.oidc.cors import get_allowed_origins
from canaille.oidc.cors import get_client_origin


def test_get_client_origin_from_client_uri(testclient, client):
    """Origin is extracted from client_uri."""
    assert get_client_origin(client) == "https://client.test"


def test_get_client_origin_none(testclient, backend):
    """When client_uri is not set, return None."""
    c = models.Client(
        client_id=gen_salt(24),
        client_name="Client without client_uri",
        redirect_uris=["https://app.example.com/callback"],
        client_secret=gen_salt(48),
    )
    backend.save(c)

    try:
        assert get_client_origin(c) is None
    finally:
        backend.delete(c)


def test_get_allowed_origins(testclient, client, trusted_client):
    """Allowed origins are collected from all registered clients."""
    origins = get_allowed_origins()
    assert "https://client.test" in origins
    assert "https://client.trusted.test" in origins


def test_cors_allowed_on_well_known(testclient, client):
    """CORS headers are present for allowed origins on .well-known endpoints."""
    res = testclient.get(
        "/.well-known/openid-configuration",
        headers={"Origin": "https://client.test"},
    )
    assert res.headers.get("Access-Control-Allow-Origin") == "https://client.test"


def test_cors_allowed_on_token_endpoint(testclient, client):
    """CORS headers are present for allowed origins on token endpoint."""
    res = testclient.options(
        "/oauth/token",
        headers={
            "Origin": "https://client.test",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.headers.get("Access-Control-Allow-Origin") == "https://client.test"


def test_cors_allowed_on_userinfo_endpoint(testclient, client):
    """CORS headers are present for allowed origins on userinfo endpoint."""
    res = testclient.options(
        "/oauth/userinfo",
        headers={
            "Origin": "https://client.test",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.headers.get("Access-Control-Allow-Origin") == "https://client.test"


def test_cors_allowed_on_jwks_endpoint(testclient, client):
    """CORS headers are present for allowed origins on JWKS endpoint."""
    res = testclient.get(
        "/oauth/jwks.json",
        headers={"Origin": "https://client.test"},
    )
    assert res.headers.get("Access-Control-Allow-Origin") == "https://client.test"


def test_cors_allowed_on_introspect_endpoint(testclient, client):
    """CORS headers are present for allowed origins on introspect endpoint."""
    res = testclient.options(
        "/oauth/introspect",
        headers={
            "Origin": "https://client.test",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.headers.get("Access-Control-Allow-Origin") == "https://client.test"


def test_cors_allowed_on_revoke_endpoint(testclient, client):
    """CORS headers are present for allowed origins on revoke endpoint."""
    res = testclient.options(
        "/oauth/revoke",
        headers={
            "Origin": "https://client.test",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.headers.get("Access-Control-Allow-Origin") == "https://client.test"


def test_cors_allowed_on_scim_endpoint(testclient, client):
    """CORS headers are present for allowed origins on SCIM endpoints."""
    res = testclient.options(
        "/scim/v2/Users",
        headers={
            "Origin": "https://client.test",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.headers.get("Access-Control-Allow-Origin") == "https://client.test"


def test_cors_denied_for_unknown_origin(testclient, client):
    """CORS headers are not present for unknown origins."""
    res = testclient.get(
        "/.well-known/openid-configuration",
        headers={"Origin": "https://malicious.test"},
    )
    assert res.headers.get("Access-Control-Allow-Origin") is None


def test_cors_not_on_authorize_endpoint(testclient, client):
    """CORS headers are not present on authorize endpoint (per OAuth spec)."""
    res = testclient.get(
        "/oauth/authorize",
        headers={"Origin": "https://client.test"},
        expect_errors=True,
    )
    assert res.headers.get("Access-Control-Allow-Origin") is None


def test_cors_preflight_returns_allowed_methods(testclient, client):
    """Preflight requests return allowed methods."""
    res = testclient.options(
        "/oauth/token",
        headers={
            "Origin": "https://client.test",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "POST" in res.headers.get("Access-Control-Allow-Methods", "")


def test_cors_preflight_returns_allowed_headers(testclient, client):
    """Preflight requests return allowed headers."""
    res = testclient.options(
        "/oauth/token",
        headers={
            "Origin": "https://client.test",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Authorization",
        },
    )
    allowed_headers = res.headers.get("Access-Control-Allow-Headers", "")
    assert (
        "Content-Type" in allowed_headers or "content-type" in allowed_headers.lower()
    )


def test_cors_with_credentials(testclient, client):
    """CORS responses include credentials support."""
    res = testclient.get(
        "/.well-known/openid-configuration",
        headers={"Origin": "https://client.test"},
    )
    assert res.headers.get("Access-Control-Allow-Credentials") == "true"


def test_cors_no_origin_header(testclient, client):
    """No CORS headers when Origin header is absent."""
    res = testclient.get("/.well-known/openid-configuration")
    assert res.headers.get("Access-Control-Allow-Origin") is None


def test_cors_preflight_no_origin_header(testclient, client):
    """Preflight without Origin header returns no CORS headers."""
    res = testclient.options(
        "/oauth/token",
        headers={"Access-Control-Request-Method": "POST"},
    )
    assert res.headers.get("Access-Control-Allow-Origin") is None


def test_cors_preflight_denied_for_unknown_origin(testclient, client):
    """Preflight with unknown origin returns no CORS headers."""
    res = testclient.options(
        "/oauth/token",
        headers={
            "Origin": "https://malicious.test",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.headers.get("Access-Control-Allow-Origin") is None


def test_cors_preflight_not_on_authorize_endpoint(testclient, client):
    """Preflight on authorize endpoint returns no CORS headers."""
    res = testclient.options(
        "/oauth/authorize",
        headers={
            "Origin": "https://client.test",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.headers.get("Access-Control-Allow-Origin") is None


def test_get_client_origin_invalid_client_uri(testclient, backend):
    """Invalid client_uri (no scheme) returns None."""
    c = models.Client(
        client_id=gen_salt(24),
        client_name="Client with invalid URI",
        client_uri="not-a-valid-uri",
        client_secret=gen_salt(48),
    )
    backend.save(c)

    try:
        assert get_client_origin(c) is None
    finally:
        backend.delete(c)


def test_get_allowed_origins_no_valid_origins(testclient, backend):
    """Return empty set when no client has a valid origin."""
    c = models.Client(
        client_id=gen_salt(24),
        client_name="Client with invalid client_uri",
        client_uri="invalid",
        client_secret=gen_salt(48),
    )
    backend.save(c)

    try:
        origins = get_allowed_origins()
        assert "invalid" not in origins
    finally:
        backend.delete(c)
