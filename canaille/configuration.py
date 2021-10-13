import ldap
import os
import smtplib
import socket

from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend


class ConfigurationException(Exception):
    pass


def validate(config, validate_remote=False):
    if not os.path.exists(config["JWT"]["PUBLIC_KEY"]):
        raise ConfigurationException(
            f'Public key does not exist {config["JWT"]["PUBLIC_KEY"]}'
        )

    if not os.path.exists(config["JWT"]["PRIVATE_KEY"]):
        raise ConfigurationException(
            f'Private key does not exist {config["JWT"]["PRIVATE_KEY"]}'
        )

    if not validate_remote:
        return

    validate_ldap_configuration(config)
    validate_smtp_configuration(config)


def validate_ldap_configuration(config):
    try:
        conn = ldap.initialize(config["LDAP"]["URI"])
        if config["LDAP"].get("TIMEOUT"):
            conn.set_option(ldap.OPT_NETWORK_TIMEOUT, config["LDAP"]["TIMEOUT"])
        conn.simple_bind_s(config["LDAP"]["BIND_DN"], config["LDAP"]["BIND_PW"])
        conn.unbind_s()

    except ldap.SERVER_DOWN as exc:
        raise ConfigurationException(
            f'Could not connect to the LDAP server \'{config["LDAP"]["URI"]}\''
        ) from exc

    except ldap.INVALID_CREDENTIALS as exc:
        raise ConfigurationException(
            f'LDAP authentication failed with user \'{config["LDAP"]["BIND_DN"]}\''
        ) from exc


def validate_smtp_configuration(config):
    try:
        with smtplib.SMTP(
            host=config["SMTP"]["HOST"],
            port=config["SMTP"]["PORT"],
        ) as smtp:
            if config["SMTP"].get("TLS"):
                smtp.starttls()

            if config["SMTP"].get("LOGIN"):
                smtp.login(
                    user=config["SMTP"]["LOGIN"],
                    password=config["SMTP"].get("PASSWORD"),
                )
    except (socket.gaierror, ConnectionRefusedError) as exc:
        raise ConfigurationException(
            f'Could not connect to the SMTP server \'{config["SMTP"]["HOST"]}\''
        ) from exc

    except smtplib.SMTPAuthenticationError as exc:
        raise ConfigurationException(
            f'SMTP authentication failed with user \'{config["SMTP"]["LOGIN"]}\''
        ) from exc


def setup_dev_keypair(config):
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
