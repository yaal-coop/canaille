import logging
import os
import pathlib
from unittest import mock

import pytest
import tomlkit
from flask_webtest import TestApp
from pydantic import ValidationError

from canaille import create_app
from canaille.app.configuration import CheckResult
from canaille.app.configuration import check_network_config
from canaille.app.configuration import check_smpp_connection
from canaille.app.configuration import check_smtp_connection
from canaille.app.configuration import export_config
from canaille.app.configuration import sanitize_rst_text
from canaille.app.configuration import settings_factory


def test_configuration_secrets_directory(tmp_path, backend, configuration):
    os.environ["SECRETS_DIR"] = str(tmp_path)

    secret_key_path = tmp_path / "SECRET_KEY"
    with open(secret_key_path, "w") as fd:
        fd.write("very-secret")

    del configuration["SECRET_KEY"]

    app = create_app(configuration)
    assert app.config["SECRET_KEY"] == "very-secret"
    del os.environ["SECRETS_DIR"]


@pytest.mark.skip
# Not fully implemented in pydantic-settings yet
# https://github.com/pydantic/pydantic-settings/issues/154
def test_configuration_nestedsecrets_directory(tmp_path, backend, configuration):
    os.environ["SECRETS_DIR"] = str(tmp_path)

    smtp_password_path = tmp_path / "CANAILLE__SMTP__PASSWORD"
    with open(smtp_password_path, "w") as fd:
        fd.write("very-very-secret")

    del configuration["CANAILLE"]["SMTP"]["PASSWORD"]

    app = create_app(configuration)
    assert app.config["CANAILLE"]["SMTP"]["PASSWORD"] == "very-very-secret"
    del os.environ["SECRETS_DIR"]


def test_no_configuration(configuration, tmp_path):
    """Test that no configuration still makes valid Canaille application."""
    os.environ["DEBUG"] = "1"

    app = create_app()
    assert app.config["CANAILLE"]["NAME"] == "Canaille"

    del os.environ["DEBUG"]


def test_environment_configuration(configuration, tmp_path):
    """Test loading the configuration from a toml file passed by the CONFIG environment var."""
    config_path = os.path.join(tmp_path, "config.toml")
    with open(config_path, "w") as fd:
        tomlkit.dump(configuration, fd)

    os.environ["CONFIG"] = config_path
    app = create_app()
    assert app.config["CANAILLE"]["SMTP"]["FROM_ADDR"] == "admin@mydomain.test"

    del os.environ["CONFIG"]
    os.remove(config_path)


def test_local_configuration(configuration, tmp_path):
    """Test loading the configuration from a local config.toml file."""
    cwd = os.getcwd()
    os.chdir(tmp_path)

    config_path = os.path.join(tmp_path, "canaille.toml")
    with open(config_path, "w") as fd:
        tomlkit.dump(configuration, fd)

    app = create_app()
    assert app.config["CANAILLE"]["SMTP"]["FROM_ADDR"] == "admin@mydomain.test"

    os.chdir(cwd)
    os.remove(config_path)


def test_configuration_from_environment_vars(tmp_path):
    """Canaille should read configuration from environment vars."""
    os.environ["SECRET_KEY"] = "very-very-secret"
    os.environ["CANAILLE__SMTP__FROM_ADDR"] = "user@mydomain.test"
    os.environ["CANAILLE_SQL__DATABASE_URI"] = f"sqlite:///{tmp_path}/anything.db"

    conf = settings_factory({"TIMEZONE": "UTC"})
    assert conf.SECRET_KEY == "very-very-secret"
    assert conf.CANAILLE.SMTP.FROM_ADDR == "user@mydomain.test"
    assert conf.CANAILLE_SQL.DATABASE_URI == f"sqlite:///{tmp_path}/anything.db"

    app = create_app({"TIMEZONE": "UTC"})
    assert app.config["SECRET_KEY"] == "very-very-secret"
    assert app.config["CANAILLE"]["SMTP"]["FROM_ADDR"] == "user@mydomain.test"
    assert (
        app.config["CANAILLE_SQL"]["DATABASE_URI"]
        == f"sqlite:///{tmp_path}/anything.db"
    )

    del os.environ["SECRET_KEY"]
    del os.environ["CANAILLE__SMTP__FROM_ADDR"]
    del os.environ["CANAILLE_SQL__DATABASE_URI"]


def test_disable_env_var_loading(tmp_path, configuration):
    """Canaille should not read configuration from environment vars when env_prefix is False."""
    del configuration["SERVER_NAME"]
    os.environ["SERVER_NAME"] = "example.test"
    os.environ["FOOBAR_SERVER_NAME"] = "foobar.example.test"

    app = create_app(configuration, env_prefix="")
    assert app.config["SERVER_NAME"] == "example.test"

    app = create_app(configuration, env_prefix="FOOBAR_")
    assert app.config["SERVER_NAME"] == "foobar.example.test"

    del os.environ["SERVER_NAME"]


def test_dotenv_file(tmp_path, configuration):
    """Canaille should read configuration from .env files."""
    os.environ["ENV_FILE"] = ".env"
    oldcwd = os.getcwd()
    os.chdir(tmp_path)
    dotenv = tmp_path / ".env"

    with open(dotenv, "w") as fd:
        fd.write("FOOBAR=custom-value")

    app = create_app(configuration)
    assert app.config["FOOBAR"] == "custom-value"
    os.chdir(oldcwd)
    del os.environ["ENV_FILE"]


def test_custom_dotenv_file(tmp_path, configuration):
    """Canaille should read configuration from custom .env files if they are passed with env_file."""
    dotenv = tmp_path / "custom.env"
    with open(dotenv, "w") as fd:
        fd.write("FOOBAR=other-custom-value")

    app = create_app(configuration, env_file=dotenv)
    assert app.config["FOOBAR"] == "other-custom-value"


def test_disable_dotenv_file(tmp_path, configuration):
    """Canaille should ignore .env files if env_file is None."""
    oldcwd = os.getcwd()
    os.chdir(tmp_path)
    dotenv = tmp_path / ".env"

    with open(dotenv, "w") as fd:
        fd.write("FOOBAR=custom-value")

    app = create_app(configuration, env_file=None)
    assert "FOOBAR" not in app.config
    os.chdir(oldcwd)


def test_smtp_connection_remote_smtp_unreachable(testclient, backend, configuration):
    configuration["CANAILLE"]["SMTP"]["HOST"] = "smtp://invalid-smtp.com"
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()["CANAILLE"]["SMTP"]
    assert check_smtp_connection(config_dict) == CheckResult(
        success=False,
        message=f"Could not connect to the SMTP server 'smtp://invalid-smtp.com' on port '{configuration['CANAILLE']['SMTP']['PORT']}'",
    )


def test_smtp_connection_remote_smtp_wrong_credentials(
    testclient, backend, configuration
):
    configuration["CANAILLE"]["SMTP"]["PASSWORD"] = "invalid-password"
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()["CANAILLE"]["SMTP"]
    assert check_smtp_connection(config_dict) == CheckResult(
        success=False, message="SMTP authentication failed with user 'user'"
    )


def test_smtp_connection_remote_smtp_no_credentials(
    testclient, backend, configuration, mock_smpp
):
    del configuration["CANAILLE"]["SMTP"]["LOGIN"]
    del configuration["CANAILLE"]["SMTP"]["PASSWORD"]
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()["CANAILLE"]["SMTP"]
    assert check_smtp_connection(config_dict) == CheckResult(
        success=True, message="Successful SMTP connection"
    )


def test_smtp_bad_tls(testclient, backend, smtpd, configuration):
    configuration["CANAILLE"]["SMTP"]["TLS"] = False
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()["CANAILLE"]["SMTP"]
    assert check_smtp_connection(config_dict) == CheckResult(
        success=False, message="SMTP AUTH extension not supported by server."
    )


def test_smtp_discovery_success(testclient, backend, configuration, smtpd):
    """If a SMTP server is configured on the default port and is accessible without authentication, it should be used."""
    del configuration["CANAILLE"]["SMTP"]
    with mock.patch("canaille.core.configuration.DEFAULT_SMTP_PORT", smtpd.port):
        config_obj = settings_factory(configuration)
        config_dict = config_obj.model_dump()["CANAILLE"]["SMTP"]
        assert check_smtp_connection(config_dict) == CheckResult(
            success=True, message="Successful SMTP connection"
        )


def test_smtp_discovery_failure(testclient, backend, configuration, smtpd):
    """Test that something goes wrong during the SMTP server discovery."""
    del configuration["CANAILLE"]["SMTP"]
    with mock.patch("canaille.core.configuration.DEFAULT_SMTP_PORT", 99999):
        config_obj = settings_factory(configuration)
        assert config_obj.model_dump()["CANAILLE"]["SMTP"] is None


@pytest.fixture
def themed_testclient(app, configuration, backend):
    root = os.path.dirname(os.path.abspath(__file__))
    test_theme_path = os.path.join(root, "fixtures", "themes", "test")
    configuration["CANAILLE"]["THEME"] = test_theme_path

    app = create_app(configuration)

    return TestApp(app)


def test_theme(testclient, themed_testclient, backend):
    res = testclient.get("/login")
    res.mustcontain(no="TEST_THEME")

    res = themed_testclient.get("/login")
    res.mustcontain("TEST_THEME")


def test_invalid_theme(configuration, backend):
    with pytest.raises(
        ValidationError,
        match=r"Path does not point to a directory",
    ):
        configuration["CANAILLE"]["THEME"] = "invalid"
        settings_factory(configuration)

    with pytest.raises(
        ValidationError,
        match=r"Path does not point to a directory",
    ):
        configuration["CANAILLE"]["THEME"] = "/path/to/invalid"
        settings_factory(configuration)


def test_enable_password_compromission_check_with_and_without_admin_email(
    configuration, backend
):
    configuration["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = False
    configuration["CANAILLE"]["ADMIN_EMAIL"] = None
    settings_factory(configuration)

    configuration["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = True
    configuration["CANAILLE"]["ADMIN_EMAIL"] = "admin_default_mail@mydomain.test"
    settings_factory(configuration)

    with pytest.raises(
        ValidationError,
        match=r"You must set an administration email if you want to check if users' passwords are compromised.",
    ):
        configuration["CANAILLE"]["ENABLE_PASSWORD_COMPROMISSION_CHECK"] = True
        configuration["CANAILLE"]["ADMIN_EMAIL"] = None
        settings_factory(configuration)


def test_invalid_otp_option(configuration, backend):
    with pytest.raises(
        ValidationError,
        match=r"Input should be 'TOTP' or 'HOTP'",
    ):
        configuration["CANAILLE"]["OTP_METHOD"] = "invalid"
        settings_factory(configuration)


def test_email_otp_without_smtp(configuration, backend):
    with pytest.raises(
        ValidationError,
        match=r"Cannot activate email one-time password authentication without SMTP",
    ):
        configuration["CANAILLE"]["SMTP"] = None
        configuration["CANAILLE"]["EMAIL_OTP"] = True
        settings_factory(configuration)


def test_sms_otp_without_smpp(configuration, backend):
    with pytest.raises(
        ValidationError,
        match=r"Cannot activate sms one-time password authentication without SMPP",
    ):
        configuration["CANAILLE"]["SMPP"] = None
        configuration["CANAILLE"]["SMS_OTP"] = True
        settings_factory(configuration)


def test_smpp_connection_remote_smpp_unreachable(testclient, backend, configuration):
    configuration["CANAILLE"]["SMPP"] = {
        "HOST": "invalid-smpp.com",
        "PORT": 2775,
        "LOGIN": "user",
        "PASSWORD": "user",
    }
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()["CANAILLE"]["SMPP"]
    assert check_smpp_connection(config_dict) == CheckResult(
        success=False,
        message="Could not connect to the SMPP server 'invalid-smpp.com' on port '2775'",
    )


def test_check_network_config_without_smpp(configuration, backend, mock_smpp):
    configuration["CANAILLE"]["SMPP"] = None
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()

    assert CheckResult(
        success=None, message="No SMPP server configured"
    ) in check_network_config(config_dict)


def test_smpp_connection_remote_smpp_no_credentials(
    testclient, backend, configuration, mock_smpp
):
    del configuration["CANAILLE"]["SMPP"]["LOGIN"]
    del configuration["CANAILLE"]["SMPP"]["PASSWORD"]
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()["CANAILLE"]["SMPP"]
    assert check_smpp_connection(config_dict) == CheckResult(
        success=True, message="Successful SMPP connection"
    )


def test_no_secret_key(configuration, caplog):
    del configuration["SECRET_KEY"]

    os.environ["DEBUG"] = "1"
    from canaille.app.server import app

    assert (
        "canaille",
        logging.WARNING,
        "Missing 'SECRET_KEY' configuration parameter.",
    ) in caplog.record_tuples

    testclient = TestApp(app)
    res = testclient.get("/login")
    res.mustcontain(
        "Your Canaille instance is not fully configured and not ready for production."
    )
    del os.environ["DEBUG"]


def test_sanitize_rst():
    assert sanitize_rst_text("``somevar``") == "somevar"
    assert sanitize_rst_text(":class:`~canaille.core.models.User`") == "User"
    assert sanitize_rst_text(":data:`None`") == "None"
    assert sanitize_rst_text(":py:data:`None`") == "None"
    assert (
        sanitize_rst_text("`Yaal Coop <https://yaal.coop>`_")
        == "Yaal Coop (https://yaal.coop)"
    )

    assert (
        sanitize_rst_text(""".. code-block:: python

    var = "value"
""")
        == '    var = "value"\n'
    )
    assert (
        sanitize_rst_text(""".. danger::

    foobar
""")
        == "    foobar\n"
    )


def test_export_current_config(backend, configuration, tmp_path):
    """Check the configuration TOML export with the current app configuration."""
    if "memory" not in backend.__class__.__module__:
        pytest.skip()

    toml_export = tmp_path / "config.toml"

    configuration["SECRET_KEY"] = "very-secret"
    configuration["CANAILLE"]["SMTP"]["PORT"] = 25

    config_obj = settings_factory(configuration, init_with_examples=True)
    export_config(config_obj, toml_export)

    toml_expected = (
        pathlib.Path(__file__).parent / "fixtures" / "current-app-config.toml"
    )

    with open(toml_export) as fd:
        actual_content = fd.read()

    with open(toml_expected) as fd:
        expected_content = fd.read()

    assert actual_content == expected_content


def test_export_default_config(tmp_path, backend):
    """Check the configuration TOML export with the default configuration."""
    toml_export = tmp_path / "config.toml"

    config_obj = settings_factory(init_with_examples=True)
    export_config(config_obj, toml_export)

    toml_expected = pathlib.Path(__file__).parent / "fixtures" / "default-config.toml"

    with open(toml_export) as fd:
        actual_content = fd.read()

    with open(toml_expected) as fd:
        expected_content = fd.read()

    assert actual_content == expected_content
