def generate_keypair():
    from cryptography.hazmat.backends import default_backend as crypto_default_backend
    from cryptography.hazmat.primitives import serialization as crypto_serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

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
    return private_key, public_key


def install(config, debug=False):
    if (
        not debug
        or not config.get("OIDC", {}).get("JWT")
        or (
            config["OIDC"]["JWT"].get("PUBLIC_KEY")
            and config["OIDC"]["JWT"].get("PRIVATE_KEY")
        )
    ):
        return

    private_key, public_key = generate_keypair()
    config["OIDC"]["JWT"]["PUBLIC_KEY"] = public_key.decode()
    config["OIDC"]["JWT"]["PRIVATE_KEY"] = private_key.decode()
