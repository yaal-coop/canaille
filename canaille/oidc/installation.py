import os

import ldap.modlist
import ldif
from canaille.ldap_backend.installation import install_schema
from canaille.ldap_backend.installation import ldap_connection
from canaille.oidc.models import AuthorizationCode
from canaille.oidc.models import Client
from canaille.oidc.models import Consent
from canaille.oidc.models import Token
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def install(config):
    setup_ldap_tree(config)
    setup_keypair(config)
    setup_schemas(config)


def setup_ldap_tree(config):
    with ldap_connection(config) as conn:
        Token.initialize(conn)
        AuthorizationCode.initialize(conn)
        Client.initialize(conn)
        Consent.initialize(conn)


def setup_keypair(config):
    if os.path.exists(config["JWT"]["PUBLIC_KEY"]) or os.path.exists(
        config["JWT"]["PRIVATE_KEY"]
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

    with open(config["JWT"]["PUBLIC_KEY"], "wb") as fd:
        fd.write(public_key)

    with open(config["JWT"]["PRIVATE_KEY"], "wb") as fd:
        fd.write(private_key)


def setup_schemas(config):
    install_schema(
        config,
        os.path.dirname(os.path.dirname(__file__))
        + "/ldap_backend/schemas/oauth2-openldap.ldif",
    )
