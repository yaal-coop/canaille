import os
import re
import smtplib
import socket
import textwrap
from dataclasses import dataclass

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ValidationError
from pydantic import create_model
from pydantic_core import PydanticUndefined
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

try:
    import tomlkit

    HAS_TOMLKIT = True
except ImportError:
    HAS_TOMLKIT = False

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
    if HAS_TOMLKIT and not config:
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


def sanitize_rst_text(text: str) -> str:
    """Remove inline RST syntax."""
    # Replace :foo:`~bar.Baz` with Baz
    text = re.sub(r":[\w:-]+:`~[\w\.]+\.(\w+)`", r"\1", text)

    # Replace :foo:`bar` and :foo:`bar <anything> with bar`
    text = re.sub(r":[\w:-]+:`([^`<]+)(?: <[^`>]+>)?`", r"\1", text)

    # Replace `label <URL>`_ with label (URL)
    text = re.sub(r"`([^`<]+) <([^`>]+)>`_", r"\1 (\2)", text)

    # Replace ``foo`` with `foo`
    text = re.sub(r"``([^`]+)``", r"\1", text)

    # Remove RST directives
    text = re.sub(r"\.\. [\w-]+::( \w+)?\n\n", "", text)

    return text


def sanitize_comments(text: str, line_length: int) -> str:
    """Remove RST syntax and wrap the docstring so it displays well as TOML comments."""

    def is_code_block(text: str) -> bool:
        return all(line.startswith("    ") for line in text.splitlines())

    def is_list(text: str) -> bool:
        return all(
            line.startswith("-") or line.startswith("  ") for line in text.splitlines()
        )

    text = sanitize_rst_text(text)
    paragraphs = text.split("\n\n")
    paragraphs = [
        textwrap.fill(paragraph, width=line_length)
        if not is_code_block(paragraph) and not is_list(paragraph)
        else paragraph
        for paragraph in paragraphs
    ]
    text = "\n\n".join(paragraphs)
    return text


def export_object_to_toml(
    obj,
    with_comments: bool = True,
    with_defaults: bool = True,
    line_length: int = 80,
):
    """Create a tomlkit document from an object."""

    def is_complex(obj) -> bool:
        return isinstance(obj, list | dict | BaseModel | BaseSettings)

    if isinstance(obj, BaseModel | BaseSettings):
        doc = tomlkit.document() if isinstance(obj, BaseSettings) else tomlkit.table()
        for field_name, field_info in obj.__class__.model_fields.items():
            field_value = getattr(obj, field_name)
            display_value = field_value is not None and (
                isinstance(field_value, BaseModel | BaseSettings)
                or field_value != field_info.default
            )
            display_comments = with_comments and field_info.description
            display_default_value = (
                with_defaults
                and not is_complex(field_info.default)
                and not is_complex(field_value)
            )

            if display_comments and (display_default_value or display_value):
                sanitized = sanitize_comments(field_info.description, line_length)
                for line in sanitized.splitlines():
                    doc.add(tomlkit.comment(line))

            if display_default_value:
                parsed = (
                    tomlkit.item(field_info.default).as_string()
                    if field_info.default is not None
                    and field_info.default is not PydanticUndefined
                    else ""
                )
                doc.add(tomlkit.comment(f"{field_name} = {parsed}".strip()))

            sub_value = export_object_to_toml(field_value)
            if display_value:
                doc.add(field_name, sub_value)
            doc.add(tomlkit.nl())
        return doc

    elif isinstance(obj, list):
        max_inline_items = 4
        is_multiline = len(obj) > max_inline_items or all(
            is_complex(item) for item in obj
        )
        doc = tomlkit.array().multiline(is_multiline)

        for item in obj:
            sub_value = export_object_to_toml(item)
            doc.append(sub_value)
        return doc

    elif isinstance(obj, dict):
        inline = all(not is_complex(item) for item in obj.values())
        doc = tomlkit.inline_table() if inline else tomlkit.table()
        for key, value in obj.items():
            sub_value = export_object_to_toml(value)
            doc.add(key, sub_value)
        return doc

    else:
        return obj


def export_config(model: BaseSettings, filename: str):
    doc = export_object_to_toml(model)
    content = tomlkit.dumps(doc)

    # Remove end-of-line spaces
    content = re.sub(r" +\n", "\n", content)

    # Remove multiple new-lines
    content = re.sub(r"\n\n+", "\n\n", content)

    # Remove end-of-file new-line
    content = re.sub(r"\n+\Z", "\n", content)

    with open(filename, "w") as fd:
        fd.write(content)


def example_settings(model: type[BaseModel]) -> BaseModel:
    """Init a pydantic BaseModel with values passed as Field 'examples'."""
    data = {
        field_name: field_info.examples[0]
        for field_name, field_info in model.model_fields.items()
        if field_info.examples
    }
    return model.model_validate(data)
