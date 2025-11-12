"""Tests for proxy header handling in Hypercorn deployment."""

import os

import pytest
from flask_webtest import TestApp

from canaille.hypercorn.app import create_app


@pytest.fixture
def configuration(configuration):
    configuration["CANAILLE_HYPERCORN"] = {
        "PROXY_MODE": "legacy",
        "PROXY_TRUSTED_HOPS": 1,
    }
    configuration["SERVER_NAME"] = "auth.canaille.test"
    configuration["PREFERRED_URL_SCHEME"] = "https"
    return configuration


@pytest.fixture
def app(configuration, backend):
    """Return a Hypercorn app with proxy mode enabled."""
    os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "true"

    flask_app = create_app(config=configuration, backend=backend, wrap_asgi=False)

    yield flask_app

    del os.environ["AUTHLIB_INSECURE_TRANSPORT"]


def test_proxy_headers_generate_https_urls(app):
    """Test that HTTPS URLs are generated when X-Forwarded-Proto header is present.

    This is a regression test for the issue where authorization_endpoint and other
    OIDC endpoints were generated with http:// instead of https:// when Canaille
    was deployed behind a reverse proxy.
    """
    testclient = TestApp(app)

    res = testclient.get(
        "/.well-known/openid-configuration",
        headers={
            "X-Forwarded-Proto": "https",
        },
        status=200,
    ).json

    assert res["authorization_endpoint"] == "https://auth.canaille.test/oauth/authorize"

    res = testclient.get(
        "/.well-known/openid-configuration",
        status=200,
    ).json

    assert res["authorization_endpoint"] == "http://auth.canaille.test/oauth/authorize"
