"""Tests for FIDO2/WebAuthn utility functions."""

import pytest
from flask import Flask

from canaille.app.fido import deserialize_transports
from canaille.app.fido import get_origin
from canaille.app.fido import get_rp_id
from canaille.app.fido import get_rp_name
from canaille.app.fido import serialize_transports


@pytest.fixture
def simple_app():
    """Create a simple Flask app for testing."""
    app = Flask(__name__)
    app.config["CANAILLE"] = {"NAME": "Test App"}
    return app


def test_get_rp_id(simple_app):
    """Test get_rp_id returns domain from request host."""
    with simple_app.test_request_context(base_url="https://example.com:5000"):
        rp_id = get_rp_id()
        assert rp_id == "example.com"


def test_get_rp_name(simple_app):
    """Test get_rp_name returns CANAILLE.NAME."""
    simple_app.config["CANAILLE"]["NAME"] = "My Organization"

    with simple_app.test_request_context():
        name = get_rp_name()
        assert name == "My Organization"


def test_get_origin(simple_app):
    """Test get_origin returns full origin URL."""
    with simple_app.test_request_context(base_url="https://example.com"):
        origin = get_origin()
        assert origin == "https://example.com"


def test_get_origin_with_port(simple_app):
    """Test get_origin with port."""
    with simple_app.test_request_context(base_url="http://example.com:8080"):
        origin = get_origin()
        assert origin == "http://example.com:8080"


def test_serialize_transports_none():
    """Test serialize_transports with None."""
    result = serialize_transports(None)
    assert result is None


def test_serialize_transports_with_list():
    """Test serialize_transports with a list."""
    result = serialize_transports(["usb", "nfc"])
    assert result == '["usb", "nfc"]'


def test_deserialize_transports_none():
    """Test deserialize_transports with None."""
    result = deserialize_transports(None)
    assert result is None


def test_deserialize_transports_with_json():
    """Test deserialize_transports with JSON string."""
    from webauthn.helpers.structs import AuthenticatorTransport

    result = deserialize_transports('["usb", "nfc"]')
    assert len(result) == 2
    assert result[0] == AuthenticatorTransport.USB
    assert result[1] == AuthenticatorTransport.NFC
