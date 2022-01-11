import os
from contextlib import contextmanager

import ldap.modlist
import ldif
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from .oidc.models import AuthorizationCode
from .oidc.models import Client
from .oidc.models import Consent
from .oidc.models import Token


class InstallationException(Exception):
    pass


def install(config):
    setup_ldap_tree(config)
    setup_keypair(config)
    setup_schemas(config)


@contextmanager
def ldap_connection(config):
    conn = ldap.initialize(config["LDAP"]["URI"])
    if config["LDAP"].get("TIMEOUT"):
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, config["LDAP"]["TIMEOUT"])

    conn.simple_bind_s(config["LDAP"]["BIND_DN"], config["LDAP"]["BIND_PW"])

    try:
        yield conn
    finally:
        conn.unbind_s()


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
    with open("schemas/oauth2-openldap.ldif") as fd:
        parser = ldif.LDIFRecordList(fd)
        parser.parse()

    try:
        with ldap_connection(config) as conn:
            for dn, entry in parser.all_records:
                add_modlist = ldap.modlist.addModlist(entry)
                conn.add_s(dn, add_modlist)

    except ldap.INSUFFICIENT_ACCESS as exc:
        raise InstallationException(
            f"The user '{config['LDAP']['BIND_DN']}' has insufficient permissions to install LDAP schemas."
        ) from exc
