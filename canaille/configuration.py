import ldap
import os
import smtplib
import socket
import uuid

ROOT = os.path.dirname(os.path.abspath(__file__))


class ConfigurationException(Exception):
    pass


def validate(config, validate_remote=False):
    validate_keypair(config)
    validate_theme(config)

    if not validate_remote:
        return

    validate_ldap_configuration(config)
    validate_smtp_configuration(config)


def validate_keypair(config):
    if not os.path.exists(config["JWT"]["PUBLIC_KEY"]):
        raise ConfigurationException(
            f'Public key does not exist {config["JWT"]["PUBLIC_KEY"]}'
        )

    if not os.path.exists(config["JWT"]["PRIVATE_KEY"]):
        raise ConfigurationException(
            f'Private key does not exist {config["JWT"]["PRIVATE_KEY"]}'
        )


def validate_ldap_configuration(config):
    from canaille.models import User, Group

    try:
        conn = ldap.initialize(config["LDAP"]["URI"])
        if config["LDAP"].get("TIMEOUT"):
            conn.set_option(ldap.OPT_NETWORK_TIMEOUT, config["LDAP"]["TIMEOUT"])
        conn.simple_bind_s(config["LDAP"]["BIND_DN"], config["LDAP"]["BIND_PW"])

    except ldap.SERVER_DOWN as exc:
        raise ConfigurationException(
            f'Could not connect to the LDAP server \'{config["LDAP"]["URI"]}\''
        ) from exc

    except ldap.INVALID_CREDENTIALS as exc:
        raise ConfigurationException(
            f'LDAP authentication failed with user \'{config["LDAP"]["BIND_DN"]}\''
        ) from exc

    try:
        User.ocs_by_name(conn)
        user = User(
            objectClass=["inetOrgPerson"],
            cn=f"canaille_{uuid.uuid4()}",
            sn=f"canaille_{uuid.uuid4()}",
            uid=f"canaille_{uuid.uuid4()}",
            mail=f"canaille_{uuid.uuid4()}@mydomain.tld",
            userPassword="{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz",
        )
        user.save(conn)
        user.delete(conn)

    except ldap.INSUFFICIENT_ACCESS as exc:
        raise ConfigurationException(
            f'LDAP user \'{config["LDAP"]["BIND_DN"]}\' cannot create '
            f'users at \'{config["LDAP"]["USER_BASE"]}\''
        ) from exc

    try:
        Group.ocs_by_name(conn)

        user = User(
            objectClass=["inetOrgPerson"],
            cn=f"canaille_{uuid.uuid4()}",
            sn=f"canaille_{uuid.uuid4()}",
            uid=f"canaille_{uuid.uuid4()}",
            mail=f"canaille_{uuid.uuid4()}@mydomain.tld",
            userPassword="{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz",
        )
        user.save(conn)

        group = Group(
            objectClass=["groupOfNames"],
            cn=f"canaille_{uuid.uuid4()}",
            member=[user.dn],
        )
        group.save(conn)
        group.delete(conn)

    except ldap.INSUFFICIENT_ACCESS as exc:
        raise ConfigurationException(
            f'LDAP user \'{config["LDAP"]["BIND_DN"]}\' cannot create '
            f'groups at \'{config["LDAP"]["GROUP_BASE"]}\''
        ) from exc

    finally:
        user.delete(conn)

    conn.unbind_s()


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


def validate_theme(config):
    if not config.get("THEME"):
        return

    if not os.path.exists(config["THEME"]) and not os.path.exists(
        os.path.join(ROOT, "themes", config["THEME"])
    ):
        raise ConfigurationException(f'Cannot find theme \'{config["THEME"]}\'')
