import os
import smtplib
import socket
import sys
from collections.abc import Mapping

from flask import current_app

from canaille.app.mails import DEFAULT_SMTP_HOST
from canaille.app.mails import DEFAULT_SMTP_PORT

ROOT = os.path.dirname(os.path.abspath(__file__))


class ConfigurationException(Exception):
    pass


def parse_file_keys(config):
    """Replaces configuration entries with the '_FILE' suffix with the matching
    file content."""

    SUFFIX = "_FILE"
    new_config = {}
    for key, value in config.items():
        if isinstance(value, Mapping):
            new_config[key] = parse_file_keys(value)

        elif isinstance(key, str) and key.endswith(SUFFIX) and isinstance(value, str):
            with open(value) as f:
                value = f.read().rstrip("\n")

            root_key = key[: -len(SUFFIX)]
            new_config[root_key] = value

        else:
            new_config[key] = value

    return new_config


def toml_content(file_path):
    try:
        if sys.version_info < (3, 11):  # pragma: no cover
            import toml

            return toml.load(file_path)

        import tomllib

        with open(file_path, "rb") as fd:
            return tomllib.load(fd)

    except ImportError:
        raise Exception("toml library not installed. Cannot load configuration.")


def setup_config(app, config=None, validate_config=True):
    from canaille.oidc.installation import install

    app.config.from_mapping(
        {
            "SESSION_COOKIE_NAME": "canaille",
            "OAUTH2_REFRESH_TOKEN_GENERATOR": True,
            "OAUTH2_ACCESS_TOKEN_GENERATOR": "canaille.oidc.oauth.generate_access_token",
        }
    )

    if config:
        app.config.from_mapping(parse_file_keys(config))

    elif "CONFIG" in os.environ:
        app.config.from_mapping(parse_file_keys(toml_content(os.environ["CONFIG"])))

    else:
        raise Exception(
            "No configuration file found. "
            "Either create conf/config.toml or set the 'CONFIG' variable environment."
        )

    if app.debug:
        install(app.config, debug=True)

    if validate_config:
        validate(app.config)


def validate(config, validate_remote=False):
    validate_keypair(config)
    validate_theme(config)

    if not validate_remote:
        return

    from canaille.backends import BaseBackend

    BaseBackend.get().validate(config)
    validate_smtp_configuration(config)


def validate_keypair(config):
    if (
        config.get("OIDC")
        and config["OIDC"].get("JWT")
        and not config["OIDC"]["JWT"].get("PUBLIC_KEY")
        and not current_app.debug
    ):
        raise ConfigurationException("No public key has been set")

    if (
        config.get("OIDC")
        and config["OIDC"].get("JWT")
        and not config["OIDC"]["JWT"].get("PRIVATE_KEY")
        and not current_app.debug
    ):
        raise ConfigurationException("No private key has been set")


def validate_smtp_configuration(config):
    host = config["SMTP"].get("HOST", DEFAULT_SMTP_HOST)
    port = config["SMTP"].get("PORT", DEFAULT_SMTP_PORT)
    try:
        with smtplib.SMTP(host=host, port=port) as smtp:
            if config["SMTP"].get("TLS"):
                smtp.starttls()

            if config["SMTP"].get("LOGIN"):
                smtp.login(
                    user=config["SMTP"]["LOGIN"],
                    password=config["SMTP"].get("PASSWORD"),
                )
    except (socket.gaierror, ConnectionRefusedError) as exc:
        raise ConfigurationException(
            f"Could not connect to the SMTP server '{host}' on port '{port}'"
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
