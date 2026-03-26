"""FIDO2/WebAuthn utilities and helpers."""

import json

from flask import request
from webauthn.helpers.structs import AuthenticatorTransport

from canaille.app import get_current_domain


def get_rp_id() -> str:
    """Get Relying Party ID from the current domain."""
    return get_current_domain().split(":")[0]


def get_rp_name() -> str:
    """Get Relying Party display name from CANAILLE.NAME configuration."""
    from flask import current_app

    return current_app.config["CANAILLE"]["NAME"]


def get_origin() -> str:
    """Get expected origin URL for WebAuthn operations."""
    return f"{request.scheme}://{request.host}"


def serialize_transports(transports: list[str] | None) -> str | None:
    """Serialize transport list to JSON string for database storage."""
    if transports is None:
        return None
    return json.dumps(transports)


def deserialize_transports(transports_json: str | None) -> list | None:
    """Deserialize transport list from JSON string.

    Returns a list of AuthenticatorTransport enums from py_webauthn.
    """
    if transports_json is None:
        return None

    transport_strings = json.loads(transports_json)
    return [AuthenticatorTransport(t) for t in transport_strings]
