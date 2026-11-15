"""FIDO2/WebAuthn utilities and helpers."""

import hashlib
import hmac
import json

from flask import current_app
from flask import request
from webauthn.helpers.structs import AuthenticatorTransport
from webauthn.helpers.structs import PublicKeyCredentialDescriptor

from canaille.app import get_current_domain

FAKE_CREDENTIAL_TRANSPORTS = [
    [AuthenticatorTransport.INTERNAL, AuthenticatorTransport.HYBRID],
    [AuthenticatorTransport.USB, AuthenticatorTransport.NFC],
    [AuthenticatorTransport.USB],
    [AuthenticatorTransport.HYBRID],
]
"""Usual transports of passkeys, to make fake credentials look real."""


def get_fake_credential(login: str | None) -> PublicKeyCredentialDescriptor:
    """Build a stable passkey descriptor for a login that matches no user.

    Per WebAuthn Level 3 §14.6.2, unknown logins get a plausible credential,
    so the authentication options do not tell whether the account exists.
    """
    key = current_app.config["SECRET_KEY"].encode("utf-8")
    message = f"webauthn-credential:{(login or '').casefold()}".encode()
    digest = hmac.new(key, message, hashlib.sha256).digest()
    transports = FAKE_CREDENTIAL_TRANSPORTS[digest[0] % len(FAKE_CREDENTIAL_TRANSPORTS)]
    return PublicKeyCredentialDescriptor(id=digest, transports=transports)


def get_rp_id() -> str:
    """Get Relying Party ID from the current domain."""
    return get_current_domain().split(":")[0]


def get_rp_name() -> str:
    """Get Relying Party display name from CANAILLE.NAME configuration."""
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
