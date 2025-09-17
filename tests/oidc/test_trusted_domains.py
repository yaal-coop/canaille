"""Tests for TRUSTED_DOMAINS functionality."""

from canaille.app import models


def test_trusted_domains_property(testclient, backend):
    """Test that the trusted property works with TRUSTED_DOMAINS configuration."""
    client_localhost = models.Client(
        client_id="localhost-client",
        client_name="Localhost Client",
        client_uri="http://localhost:3000",
    )
    backend.save(client_localhost)

    client_trusted = models.Client(
        client_id="trusted-client",
        client_name="Trusted Client",
        client_uri="https://client.trusted.test",
    )
    backend.save(client_trusted)

    client_subdomain = models.Client(
        client_id="subdomain-client",
        client_name="Subdomain Client",
        client_uri="https://app.trusted.test",
    )
    backend.save(client_subdomain)

    client_untrusted = models.Client(
        client_id="untrusted-client",
        client_name="Untrusted Client",
        client_uri="https://evil.example.com",
    )
    backend.save(client_untrusted)

    client_no_uri = models.Client(
        client_id="no-uri-client",
        client_name="No URI Client",
    )
    backend.save(client_no_uri)

    assert client_localhost.trusted
    assert client_trusted.trusted
    assert client_subdomain.trusted
    assert not client_untrusted.trusted
    assert not client_no_uri.trusted


def test_trusted_domains_consent_bypass(testclient, logged_user, backend):
    """Test that trusted clients bypass the consent page."""
    client = models.Client(
        client_id="test-client",
        client_name="Test Client",
        client_uri="https://localhost:3000",
        redirect_uris=["https://localhost:3000/callback"],
        grant_types=["authorization_code"],
        response_types=["code"],
        scope=["openid", "profile"],
    )
    backend.save(client)
    client.audience = [client]
    backend.save(client)

    res = testclient.get(
        "/oauth/authorize",
        {
            "response_type": "code",
            "client_id": client.client_id,
            "scope": "openid profile",
            "redirect_uri": "https://localhost:3000/callback",
            "nonce": "test-nonce",
        },
        status=302,
    )

    assert res.location.startswith("https://localhost:3000/callback?code=")


def test_untrusted_domains_show_consent(testclient, logged_user, backend):
    """Test that untrusted clients show the consent page."""
    client = models.Client(
        client_id="untrusted-consent-client",
        client_name="Untrusted Client",
        client_uri="https://untrusted.example.com",
        redirect_uris=["https://untrusted.example.com/callback"],
        grant_types=["authorization_code"],
        response_types=["code"],
        scope=["openid", "profile"],
    )
    backend.save(client)
    client.audience = [client]
    backend.save(client)

    res = testclient.get(
        "/oauth/authorize",
        {
            "response_type": "code",
            "client_id": client.client_id,
            "scope": "openid profile",
            "redirect_uri": "https://untrusted.example.com/callback",
            "nonce": "untrusted-test-nonce",
        },
        status=200,
    )

    res.mustcontain("is requesting access to")
    res.mustcontain("Untrusted Client")


def test_wildcard_and_exact_domain_matching(testclient, backend):
    """Test wildcard domains and exact domain matching."""
    testclient.app.config["CANAILLE_OIDC"]["TRUSTED_DOMAINS"] = [
        ".dev.test",
        "exact.test",
    ]

    client_wildcard_sub = models.Client(
        client_id="wildcard-sub-client",
        client_name="Wildcard Sub Client",
        client_uri="https://app.dev.test",
    )
    backend.save(client_wildcard_sub)

    client_wildcard_exact = models.Client(
        client_id="wildcard-exact-client",
        client_name="Wildcard Exact Client",
        client_uri="https://dev.test",
    )
    backend.save(client_wildcard_exact)

    client_exact_sub = models.Client(
        client_id="exact-sub-client",
        client_name="Exact Sub Client",
        client_uri="https://sub.exact.test",
    )
    backend.save(client_exact_sub)

    client_exact_exact = models.Client(
        client_id="exact-exact-client",
        client_name="Exact Exact Client",
        client_uri="https://exact.test",
    )
    backend.save(client_exact_exact)

    client_no_match = models.Client(
        client_id="no-match-client",
        client_name="No Match Client",
        client_uri="https://app.untrusted.test",
    )
    backend.save(client_no_match)

    assert client_wildcard_sub.trusted
    assert client_wildcard_exact.trusted
    assert not client_exact_sub.trusted
    assert client_exact_exact.trusted
    assert not client_no_match.trusted


def test_empty_trusted_domains(testclient, backend):
    """Test that clients are not trusted when TRUSTED_DOMAINS is empty."""
    testclient.app.config["CANAILLE_OIDC"]["TRUSTED_DOMAINS"] = []

    client = models.Client(
        client_id="empty-domains-client",
        client_name="Test Client",
        client_uri="https://example.com",
    )
    backend.save(client)

    assert not client.trusted


def test_invalid_client_uri_hostname(testclient, backend):
    """Test that clients with invalid URI hostnames are not trusted."""
    testclient.app.config["CANAILLE_OIDC"]["TRUSTED_DOMAINS"] = ["example.com"]

    client = models.Client(
        client_id="invalid-uri-client",
        client_name="Test Client",
        client_uri="invalid-uri-without-hostname",
    )
    backend.save(client)

    assert not client.trusted
