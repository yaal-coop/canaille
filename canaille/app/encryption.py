"""Encryption of the secrets stored in the database.

Per RFC 6819 §5.1.4.1.3, secrets that must be read back in clear text are
encrypted. The key is derived from the Flask ``SECRET_KEY``. The keys of
``SECRET_KEY_FALLBACKS`` can still decrypt, so ``SECRET_KEY`` can be rotated.
"""

import base64
import binascii
import functools
import os
from contextvars import ContextVar

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from flask import current_app

PREFIX = "enc:v1:"
NONCE_SIZE = 12

decryption_failures: ContextVar[list[str] | None] = ContextVar(
    "decryption_failures", default=None
)
"""When set to a list, the fields that cannot be decrypted are added to it."""


@functools.lru_cache(maxsize=8)
def derive_key(secret_key: str) -> bytes:
    """Derive an AES-256 key from a Flask secret key."""
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"canaille secrets encryption",
    ).derive(secret_key.encode())


def is_encrypted(value: str | None) -> bool:
    """Whether a stored value is encrypted."""
    return bool(value) and value.startswith(PREFIX)


def encrypt(value: str | None, context: str) -> str | None:
    """Encrypt a value with the ``SECRET_KEY``.

    ``context`` is the name of the field. A value encrypted for a field
    cannot be decrypted for another one. Without ``SECRET_KEY``,
    the value is stored in clear text.
    """
    secret_key = current_app.config.get("SECRET_KEY")
    # A random SECRET_KEY can be set at startup when none is configured.
    # Secrets encrypted with it would be lost at the next restart.
    if value is None or not secret_key or getattr(current_app, "no_secret_key", False):
        return value

    nonce = os.urandom(NONCE_SIZE)
    ciphertext = AESGCM(derive_key(secret_key)).encrypt(
        nonce, value.encode(), context.encode()
    )
    return PREFIX + base64.urlsafe_b64encode(nonce + ciphertext).decode()


def decrypt(value: str | None, context: str) -> str | None:
    """Decrypt a value with the ``SECRET_KEY`` or one of the ``SECRET_KEY_FALLBACKS``.

    Values stored before encryption are returned as is.
    Return :data:`None` when no key can decrypt the value.
    """
    if value is None or not is_encrypted(value):
        return value

    try:
        payload = base64.urlsafe_b64decode(value.removeprefix(PREFIX))
    except (binascii.Error, ValueError):
        current_app.logger.error(
            "The stored %s is not a valid encrypted value", context
        )
        return None

    nonce, ciphertext = payload[:NONCE_SIZE], payload[NONCE_SIZE:]
    secret_keys = [
        current_app.config.get("SECRET_KEY"),
        *(current_app.config.get("SECRET_KEY_FALLBACKS") or []),
    ]
    for secret_key in filter(None, secret_keys):
        try:
            return (
                AESGCM(derive_key(secret_key))
                .decrypt(nonce, ciphertext, context.encode())
                .decode()
            )
        except InvalidTag:
            continue

    current_app.logger.error(
        "The stored %s cannot be decrypted with SECRET_KEY or SECRET_KEY_FALLBACKS",
        context,
    )
    if (failures := decryption_failures.get()) is not None:
        failures.append(context)

    return None
