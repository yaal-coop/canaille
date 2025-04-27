import os
import smtplib
import socket
from dataclasses import dataclass

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ValidationError
from pydantic import create_model
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from canaille.app.toml import example_settings

DEFAULT_CONFIG_FILE = "canaille.toml"


class BaseModel(PydanticBaseModel):
    model_config = SettingsConfigDict(
        use_attribute_docstrings=True,
    )


class RootSettings(BaseSettings):
    """The top-level namespace contains the configuration settings unrelated to Canaille.

    The configuration parameters from the following libraries can be used:

    - :doc:`Flask <flask:config>`
    - :doc:`Flask-WTF <flask-wtf:config>`
    - :doc:`Flask-Babel <flask-babel:index>`
    - :doc:`Authlib <authlib:flask/2/authorization-server>`

    .. code-block:: toml
        :caption: config.toml

        SECRET_KEY = "very-secret"
        SERVER_NAME = "auth.mydomain.example"
        PREFERRED_URL_SCHEME = "https"
        DEBUG = false

        [CANAILLE]
        NAME = "My organization"
        ...
    """

    model_config = SettingsConfigDict(
        extra="allow",
        env_nested_delimiter="__",
        case_sensitive=True,
        use_attribute_docstrings=True,
    )

    SECRET_KEY: str | None = None
    """The Flask :external:py:data:`SECRET_KEY` configuration setting.

    You MUST set a value before deploying in production.
    """

    SERVER_NAME: str | None = None
    """The Flask :external:py:data:`SERVER_NAME` configuration setting.

    This sets domain name on which canaille will be served.
    """

    TRUSTED_HOSTS: list[str] | None = None
    """The Flask :external:py:data:`TRUSTED_HOSTS` configuration setting.

    This sets trusted values for hosts and validates hosts during requests.
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

    CACHE_TYPE: str = "SimpleCache"
    """The cache type.

    The default ``SimpleCache`` is a lightweight in-memory cache.
    See the :doc:`Flask-Caching documentation <flask-caching:index>` for further details.
    """


def settings_factory(
    config=None,
    env_file=None,
    env_prefix="",
    init_with_examples=False,
):
    """Push the backend specific configuration into CoreSettings.

    In the purpose to break dependency against backends libraries like python-ldap or
    sqlalchemy.
    """
    from canaille.backends.ldap.configuration import LDAPSettings
    from canaille.backends.sql.configuration import SQLSettings
    from canaille.core.configuration import CoreSettings
    from canaille.oidc.configuration import OIDCSettings
    from canaille.scim.configuration import SCIMSettings

    config = config or {}

    default = example_settings(CoreSettings) if init_with_examples else CoreSettings()
    attributes = {"CANAILLE": (CoreSettings, default)}

    additional_settings = {
        "CANAILLE_SQL": (SQLSettings, True),
        "CANAILLE_LDAP": (LDAPSettings, False),
        "CANAILLE_OIDC": (OIDCSettings, True),
        "CANAILLE_SCIM": (SCIMSettings, True),
    }

    for prefix, (setting, enabled_by_default) in additional_settings.items():
        if init_with_examples:
            default_value = example_settings(setting)
            if prefix in config and config[prefix] is None:
                del config[prefix]

        elif enabled_by_default:
            default_value = setting()
        else:
            default_value = None

        attributes[prefix] = ((setting | None), default_value)

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


@dataclass
class CheckResult:
    message: str
    success: bool | None = None


def setup_config(app, config=None, env_file=None, env_prefix=""):
    from canaille.oidc.installation import install

    app.config.from_mapping(
        {
            # https://flask.palletsprojects.com/en/stable/config/#SESSION_COOKIE_NAME
            "SESSION_COOKIE_NAME": "canaille",
        }
    )
    if app.features.has_toml_conf and not config:
        import tomlkit

        if "CONFIG" in os.environ:
            with open(os.environ.get("CONFIG")) as fd:
                config = tomlkit.load(fd)
            app.logger.info(f"Loading configuration from {os.environ['CONFIG']}")

        elif os.path.exists(DEFAULT_CONFIG_FILE):
            with open(DEFAULT_CONFIG_FILE) as fd:
                config = tomlkit.load(fd)
            app.logger.info(f"Loading configuration from {DEFAULT_CONFIG_FILE}")

    env_file = env_file or os.getenv("ENV_FILE")
    try:
        config_obj = settings_factory(
            config or {}, env_file=env_file, env_prefix=env_prefix
        )
    except ValidationError as exc:  # pragma: no cover
        app.logger.critical(str(exc))
        return False

    config_dict = config_obj.model_dump()
    app.no_secret_key = config_dict["SECRET_KEY"] is None
    app.config.from_mapping(config_dict)

    if app.debug:
        install(app.config, debug=True)

    return True


def check_network_config(config):
    """Perform various network connection to services described in the configuration file."""
    from canaille.backends import Backend

    results = [Backend.instance.check_network_config(config)]

    if smtp_config := config["CANAILLE"]["SMTP"]:
        results.append(check_smtp_connection(smtp_config))
    else:
        results.append(CheckResult(message="No SMTP server configured"))

    if smpp_config := config["CANAILLE"]["SMPP"]:
        results.append(check_smpp_connection(smpp_config))
    else:
        results.append(CheckResult(message="No SMPP server configured"))

    return results


def check_smtp_connection(config) -> CheckResult:
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
    except (socket.gaierror, ConnectionRefusedError):
        return CheckResult(
            message=f"Could not connect to the SMTP server '{host}' on port '{port}'",
            success=False,
        )

    except smtplib.SMTPAuthenticationError:
        return CheckResult(
            message=f"SMTP authentication failed with user '{config['LOGIN']}'",
            success=False,
        )

    except smtplib.SMTPNotSupportedError as exc:
        return CheckResult(
            message=str(exc),
            success=False,
        )

    return CheckResult(
        message="Successful SMTP connection",
        success=True,
    )


def check_smpp_connection(config):
    import smpplib

    host = config["HOST"]
    port = config["PORT"]
    try:
        with smpplib.client.Client(host, port, allow_unknown_opt_params=True) as client:
            client.connect()
            if config["LOGIN"]:
                client.bind_transmitter(
                    system_id=config["LOGIN"], password=config["PASSWORD"]
                )
    except smpplib.exceptions.ConnectionError:
        return CheckResult(
            success=False,
            message=f"Could not connect to the SMPP server '{host}' on port '{port}'",
        )
    except smpplib.exceptions.UnknownCommandError as exc:  # pragma: no cover
        return CheckResult(
            message=str(exc),
            success=False,
        )

    return CheckResult(
        message="Successful SMPP connection",
        success=True,
    )
