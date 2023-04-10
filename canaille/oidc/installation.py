import os

from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def install(config):
    if (
        not config.get("OIDC", {}).get("JWT")
        or os.path.exists(config["OIDC"]["JWT"]["PUBLIC_KEY"])
        or os.path.exists(config["OIDC"]["JWT"]["PRIVATE_KEY"])
    ):
        return

    key = rsa.generate_private_key(
        backend=crypto_default_backend(), public_exponent=65537, key_size=2048
    )
    private_key = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.PKCS8,
        crypto_serialization.NoEncryption(),
    )
    public_key = key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH, crypto_serialization.PublicFormat.OpenSSH
    )

    with open(config["OIDC"]["JWT"]["PUBLIC_KEY"], "wb") as fd:
        fd.write(public_key)

    with open(config["OIDC"]["JWT"]["PRIVATE_KEY"], "wb") as fd:
        fd.write(private_key)
