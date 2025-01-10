import importlib.util
import os
import smtplib
import socket
import sys

from flask import current_app
from pydantic import ValidationError
from pydantic import create_model
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from canaille.core.configuration import CoreSettings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class RootSettings(BaseSettings):
    """The top-level namespace contains the configuration settings unrelated to
    Canaille.

    The configuration parameters from the following libraries can be used:

    - :doc:`Flask <flask:config>`
    - :doc:`Flask-WTF <flask-wtf:config>`
    - :doc:`Flask-Babel <flask-babel:index>`
    - :doc:`Authlib <authlib:flask/2/authorization-server>`

    .. code-block:: toml
        :caption: config.toml

        SECRET_KEY = "very-secret"
        SERVER_NAME = "auth.mydomain.example"
        PREFERRED_URL_SCHEME = false
        DEBUG = false

        [CANAILLE]
        NAME = "My organization"
        ...
    """

    model_config = SettingsConfigDict(
        extra="allow",
        env_nested_delimiter="__",
        case_sensitive=True,
    )

    SECRET_KEY: str
    """The Flask :external:py:data:`SECRET_KEY` configuration setting.

    You MUST change this.
    """

    SERVER_NAME: str | None = None
    """The Flask :external:py:data:`SERVER_NAME` configuration setting.

    This sets domain name on which canaille will be served.
    """

    PREFERRED_URL_SCHEME: str = "https"
    """The Flask :external:py:data:`PREFERRED_URL_SCHEME` configuration
    setting.

    This sets the url scheme by which canaille will be served.
    """

    DEBUG: bool = False
    """The Flask :external:py:data:`DEBUG` configuration setting.

    This enables debug options.

    .. danger::

        This is useful for development but should be absolutely
        avoided in production environments.
    """


def settings_factory(config, env_file=None, env_prefix=""):
    """Pushes the backend specific configuration into CoreSettings, in the
    purpose break dependency against backends libraries like python-ldap or
    sqlalchemy."""
    attributes = {"CANAILLE": (CoreSettings, CoreSettings())}

    if "CANAILLE_SQL" in config or any(
        var.startswith("CANAILLE_SQL__") for var in os.environ
    ):
        from canaille.backends.sql.configuration import SQLSettings

        attributes["CANAILLE_SQL"] = ((SQLSettings | None), None)

    if "CANAILLE_LDAP" in config or any(
        var.startswith("CANAILLE__LDAP__") for var in os.environ
    ):
        from canaille.backends.ldap.configuration import LDAPSettings

        attributes["CANAILLE_LDAP"] = ((LDAPSettings | None), None)

    if "CANAILLE_OIDC" in config or any(
        var.startswith("CANAILLE_OIDC__") for var in os.environ
    ):
        from canaille.oidc.configuration import OIDCSettings

        attributes["CANAILLE_OIDC"] = ((OIDCSettings | None), None)

    if "CANAILLE_SCIM" in config or any(
        var.startswith("CANAILLE_SCIM__") for var in os.environ
    ):
        from canaille.scim.configuration import SCIMSettings

        attributes["CANAILLE_SCIM"] = ((SCIMSettings | None), None)

    Settings = create_model(
        "Settings",
        __base__=RootSettings,
        **attributes,
    )

    return Settings(
        **config,
        _secrets_dir=os.environ.get("SECRETS_DIR"),
        _env_file=env_file,
        _env_prefix=env_prefix,
    )


class ConfigurationException(Exception):
    pass


def toml_content(file_path):
    try:
        if sys.version_info < (3, 11):  # pragma: no cover
            import toml

            return toml.load(file_path)

        import tomllib

        with open(file_path, "rb") as fd:
            return tomllib.load(fd)

    except ImportError as exc:
        raise Exception(
            "toml library not installed. Cannot load configuration."
        ) from exc


def setup_config(app, config=None, test_config=True, env_file=None, env_prefix=""):
    from canaille.oidc.installation import install

    app.config.from_mapping(
        {
            "SESSION_COOKIE_NAME": "canaille",
            "OAUTH2_REFRESH_TOKEN_GENERATOR": True,
            "OAUTH2_ACCESS_TOKEN_GENERATOR": "canaille.oidc.oauth.generate_access_token",
        }
    )
    if not config and "CONFIG" in os.environ:
        config = toml_content(os.environ.get("CONFIG"))

    env_file = env_file or os.getenv("ENV_FILE")
    try:
        config_obj = settings_factory(
            config or {}, env_file=env_file, env_prefix=env_prefix
        )
    except ValidationError as exc:  # pragma: no cover
        app.logger.critical(str(exc))
        return False

    app.config.from_mapping(config_obj.model_dump())

    if app.debug:
        install(app.config, debug=True)

    if test_config:
        validate(app.config)

    return True


def validate(config, validate_remote=False):
    validate_keypair(config.get("CANAILLE_OIDC"))
    validate_theme(config["CANAILLE"])
    validate_admin_email(config["CANAILLE"])
    validate_otp_config(config["CANAILLE"])
    if not validate_remote:
        return

    from canaille.backends import Backend

    Backend.instance.validate(config)
    if smtp_config := config["CANAILLE"]["SMTP"]:
        validate_smtp_configuration(smtp_config)
    if smpp_config := config["CANAILLE"]["SMPP"]:
        validate_smpp_configuration(smpp_config)


def validate_keypair(config):
    if (
        config
        and config["JWT"]
        and not config["JWT"]["PUBLIC_KEY"]
        and not current_app.debug
    ):
        raise ConfigurationException("No public key has been set")

    if (
        config
        and config["JWT"]
        and not config["JWT"]["PRIVATE_KEY"]
        and not current_app.debug
    ):
        raise ConfigurationException("No private key has been set")


def validate_smtp_configuration(config):
    host = config["HOST"]
    port = config["PORT"]
    try:
        with smtplib.SMTP(host=host, port=port) as smtp:
            if config["TLS"]:
                smtp.starttls()

            if config["LOGIN"]:
                smtp.login(
                    user=config["LOGIN"],
                    password=config["PASSWORD"],
                )
    except (socket.gaierror, ConnectionRefusedError) as exc:
        raise ConfigurationException(
            f"Could not connect to the SMTP server '{host}' on port '{port}'"
        ) from exc

    except smtplib.SMTPAuthenticationError as exc:
        raise ConfigurationException(
            f"SMTP authentication failed with user '{config['LOGIN']}'"
        ) from exc

    except smtplib.SMTPNotSupportedError as exc:
        raise ConfigurationException(exc) from exc


def validate_smpp_configuration(config):
    try:
        import smpplib
    except ImportError as exc:
        raise ConfigurationException(
            "You have configured a SMPP server but the 'sms' extra is not installed."
        ) from exc

    host = config["HOST"]
    port = config["PORT"]
    try:
        with smpplib.client.Client(host, port, allow_unknown_opt_params=True) as client:
            client.connect()
            if config["LOGIN"]:
                client.bind_transmitter(
                    system_id=config["LOGIN"], password=config["PASSWORD"]
                )
    except smpplib.exceptions.ConnectionError as exc:
        raise ConfigurationException(
            f"Could not connect to the SMPP server '{host}' on port '{port}'"
        ) from exc
    except smpplib.exceptions.UnknownCommandError as exc:  # pragma: no cover
        raise ConfigurationException(exc) from exc


def validate_theme(config):
    if not os.path.exists(config["THEME"]) and not os.path.exists(
        os.path.join(ROOT, "themes", config["THEME"])
    ):
        raise ConfigurationException(f"Cannot find theme '{config['THEME']}'")


def validate_admin_email(config):
    if config["ENABLE_PASSWORD_COMPROMISSION_CHECK"] and config["ADMIN_EMAIL"] is None:
        raise ConfigurationException(
            "You must set an administration email if you want to check if users' passwords are compromised."
        )


def validate_otp_config(config):
    if (
        config["OTP_METHOD"] or config["EMAIL_OTP"] or config["SMS_OTP"]
    ) and not importlib.util.find_spec("otpauth"):  # pragma: no cover
        raise ConfigurationException(
            "You are trying to use OTP but the 'otp' extra is not installed."
        )

    if config["OTP_METHOD"] not in [None, "TOTP", "HOTP"]:
        raise ConfigurationException("Invalid OTP method")

    if config["EMAIL_OTP"] and not config["SMTP"]:
        raise ConfigurationException(
            "Cannot activate email one-time password authentication without SMTP"
        )

    if config["SMS_OTP"] and not config["SMPP"]:
        raise ConfigurationException(
            "Cannot activate sms one-time password authentication without SMPP"
        )
