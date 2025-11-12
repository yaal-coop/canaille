"""Tests for proxy header handling in Hypercorn deployment."""

import os

import pytest
from flask import request
from flask import url_for

from canaille.hypercorn.app import create_app


@pytest.fixture
def configuration(configuration):
    configuration["CANAILLE_HYPERCORN"] = {
        "PROXY_MODE": "legacy",
        "PROXY_TRUSTED_HOPS": 1,
    }
    configuration["SERVER_NAME"] = "auth.canaille.test"
    configuration["PREFERRED_URL_SCHEME"] = "http"
    return configuration


@pytest.fixture
def app(configuration, backend):
    """Return a Hypercorn app with proxy mode enabled."""
    os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "true"

    flask_app = create_app(config=configuration, backend=backend, wrap_asgi=False)

    yield flask_app

    del os.environ["AUTHLIB_INSECURE_TRANSPORT"]


def test_proxy_headers_generate_https_urls(app, testclient):
    """Test that HTTPS URLs are generated when X-Forwarded-Proto header is present.

    This is a regression test for the issue where URLs were generated with http://
    instead of https:// when Canaille was deployed behind a reverse proxy.
    """

    @app.route("/test-url-generation")
    def test_endpoint():
        return {
            "url_root": request.url_root,
            "about_url": url_for("core.account.about", _external=True),
        }

    # Test with X-Forwarded-Proto: https
    res = testclient.get(
        "/test-url-generation",
        headers={"X-Forwarded-Proto": "https"},
    )
    assert res.json["url_root"] == "https://auth.canaille.test/"
    assert res.json["about_url"] == "https://auth.canaille.test/about"

    # Test without X-Forwarded-Proto (should use PREFERRED_URL_SCHEME from config = http)
    res = testclient.get("/test-url-generation")
    assert res.json["url_root"] == "http://auth.canaille.test/"
    assert res.json["about_url"] == "http://auth.canaille.test/about"
