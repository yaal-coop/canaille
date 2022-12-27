import os
import smtplib
import socket

ROOT = os.path.dirname(os.path.abspath(__file__))


class ConfigurationException(Exception):
    pass


def validate(config, validate_remote=False):
    validate_keypair(config)
    validate_theme(config)

    if not validate_remote:
        return

    from .ldap_backend.backend import validate_configuration

    validate_configuration(config)
    validate_smtp_configuration(config)


def validate_keypair(config):
    if "JWT" in config and not os.path.exists(config["JWT"]["PUBLIC_KEY"]):
        raise ConfigurationException(
            f'Public key does not exist {config["JWT"]["PUBLIC_KEY"]}'
        )

    if "JWT" in config and not os.path.exists(config["JWT"]["PRIVATE_KEY"]):
        raise ConfigurationException(
            f'Private key does not exist {config["JWT"]["PRIVATE_KEY"]}'
        )


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

    except smtplib.SMTPNotSupportedError as exc:
        raise ConfigurationException(exc) from exc


def validate_theme(config):
    if not config.get("THEME"):
        return

    if not os.path.exists(config["THEME"]) and not os.path.exists(
        os.path.join(ROOT, "themes", config["THEME"])
    ):
        raise ConfigurationException(f'Cannot find theme \'{config["THEME"]}\'')
