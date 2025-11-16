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
    """Create a simple Flask app for testing without request context."""
    app = Flask(__name__)
    app.config["CANAILLE"] = {}
    return app


def test_get_rp_id_with_override(simple_app):
    """Test get_rp_id with FIDO_RP_ID configured."""
    simple_app.config["CANAILLE"]["FIDO_RP_ID"] = "localhost"
    simple_app.config["SERVER_NAME"] = "canaille.example.com"

    # Outside request context, should use override
    with simple_app.app_context():
        rp_id = get_rp_id(simple_app)
        assert rp_id == "localhost"


def test_get_rp_id_without_request_context(simple_app):
    """Test get_rp_id without request context."""
    simple_app.config["SERVER_NAME"] = "example.com:5000"

    with simple_app.app_context():
        rp_id = get_rp_id(simple_app)
        assert rp_id == "example.com"


def test_get_rp_id_without_server_name():
    """Test get_rp_id raises error when SERVER_NAME is not configured."""
    app = Flask(__name__)
    app.config["CANAILLE"] = {}

    with pytest.raises(ValueError, match="SERVER_NAME must be configured"):
        get_rp_id(app)


def test_get_rp_name(simple_app):
    """Test get_rp_name returns CANAILLE.NAME."""
    simple_app.config["CANAILLE"]["NAME"] = "My Organization"

    with simple_app.app_context():
        name = get_rp_name(simple_app)
        assert name == "My Organization"


def test_get_origin_without_request_context(simple_app):
    """Test get_origin without request context."""
    simple_app.config["SERVER_NAME"] = "example.com"
    simple_app.config["PREFERRED_URL_SCHEME"] = "https"

    with simple_app.app_context():
        origin = get_origin(simple_app)
        assert origin == "https://example.com"


def test_get_origin_without_request_context_with_port(simple_app):
    """Test get_origin without request context with port."""
    simple_app.config["SERVER_NAME"] = "example.com:8080"
    simple_app.config["PREFERRED_URL_SCHEME"] = "http"

    with simple_app.app_context():
        origin = get_origin(simple_app)
        assert origin == "http://example.com:8080"


def test_get_origin_with_rp_id_override(simple_app):
    """Test get_origin with FIDO_RP_ID override."""
    simple_app.config["CANAILLE"]["FIDO_RP_ID"] = "localhost"
    simple_app.config["SERVER_NAME"] = "canaille.example.com:5000"
    simple_app.config["PREFERRED_URL_SCHEME"] = "http"

    with simple_app.app_context():
        origin = get_origin(simple_app)
        assert origin == "http://localhost:5000"


def test_get_origin_with_rp_id_override_no_port(simple_app):
    """Test get_origin with FIDO_RP_ID override without port."""
    simple_app.config["CANAILLE"]["FIDO_RP_ID"] = "localhost"
    simple_app.config["SERVER_NAME"] = "canaille.example.com"
    simple_app.config["PREFERRED_URL_SCHEME"] = "http"

    with simple_app.app_context():
        origin = get_origin(simple_app)
        assert origin == "http://localhost"


def test_get_origin_without_server_name():
    """Test get_origin raises error when SERVER_NAME is not configured."""
    app = Flask(__name__)
    app.config["CANAILLE"] = {}

    with pytest.raises(ValueError, match="SERVER_NAME must be configured"):
        get_origin(app)


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
