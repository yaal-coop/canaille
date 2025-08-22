from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from joserfc.jwk import OKPKey


def make_default_jwk(seed=None):
    """Generate a deterministic JWK based on a seed if available.

    If seed is provided, it will be used to generate a deterministic Ed25519 key.
    Otherwise, a random Ed25519 key is generated.
    """
    if seed:
        salt = b"canaille-jwk-generation-salt-v1"

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        key_material = kdf.derive(seed.encode())

        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(key_material)
    else:
        private_key = ed25519.Ed25519PrivateKey.generate()

    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    key = OKPKey.import_key(pem)
    key.ensure_kid()

    return key
