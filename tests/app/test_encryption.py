import logging

import pytest

from canaille.app.encryption import decrypt
from canaille.app.encryption import encrypt
from canaille.app.otp import is_otp_valid


@pytest.fixture(autouse=True)
def memory_only(backend):
    """Encryption does not depend on the backend."""
    if "memory" not in backend.__class__.__module__:
        pytest.skip()


def test_encrypt_decrypt(testclient):
    """A value can be decrypted, and each encryption gives another value."""
    encrypted = encrypt("secret", "client_secret")
    assert encrypted.startswith("enc:v1:")
    assert "secret" not in encrypted
    assert encrypt("secret", "client_secret") != encrypted
    assert decrypt(encrypted, "client_secret") == "secret"


def test_none(testclient):
    assert encrypt(None, "client_secret") is None
    assert decrypt(None, "client_secret") is None


def test_clear_text_values(testclient):
    """Values stored before encryption are read as is."""
    assert decrypt("secret", "client_secret") == "secret"


def test_context(testclient, caplog):
    """A value encrypted for a field cannot be decrypted for another one."""
    encrypted = encrypt("secret", "client_secret")
    assert decrypt(encrypted, "secret_token") is None
    assert (
        "canaille",
        logging.ERROR,
        "The stored secret_token cannot be decrypted with SECRET_KEY or SECRET_KEY_FALLBACKS",
    ) in caplog.record_tuples


def test_fallback_keys(testclient):
    """Values encrypted with a previous key can be decrypted with the fallback keys."""
    encrypted = encrypt("secret", "client_secret")

    old_key = testclient.app.config["SECRET_KEY"]
    testclient.app.config["SECRET_KEY"] = "new-secret-key"
    assert decrypt(encrypted, "client_secret") is None

    testclient.app.config["SECRET_KEY_FALLBACKS"] = ["other-key", old_key]
    assert decrypt(encrypted, "client_secret") == "secret"


def test_invalid_encrypted_value(testclient, caplog):
    assert decrypt("enc:v1:not base64!", "client_secret") is None
    assert (
        "canaille",
        logging.ERROR,
        "The stored client_secret is not a valid encrypted value",
    ) in caplog.record_tuples


def test_no_secret_key(testclient):
    """Without SECRET_KEY, values are stored in clear text."""
    testclient.app.config["SECRET_KEY"] = None
    assert encrypt("secret", "client_secret") == "secret"


def test_random_secret_key(testclient):
    """A random SECRET_KEY set at startup does not encrypt the secrets."""
    testclient.app.no_secret_key = True
    assert encrypt("secret", "client_secret") == "secret"


def test_otp_without_secret(testclient):
    """A secret that cannot be decrypted makes the passcode invalid."""
    assert is_otp_valid("123456", "TOTP", None) == (False, 0)
