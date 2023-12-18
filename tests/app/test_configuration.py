import os

import pytest
from flask_webtest import TestApp

from canaille import create_app
from canaille.app.configuration import ConfigurationException
from canaille.app.configuration import settings_factory
from canaille.app.configuration import validate


def test_configuration_file_suffix(tmp_path, backend, configuration):
    os.environ["SECRETS_DIR"] = str(tmp_path)
    file_path = os.path.join(tmp_path, "SECRET_KEY")
    with open(file_path, "w") as fd:
        fd.write("very-secret")

    del configuration["SECRET_KEY"]

    app = create_app(configuration)
    assert app.config["SECRET_KEY"] == "very-secret"
    del os.environ["SECRETS_DIR"]


def test_configuration_from_environment_vars():
    os.environ["SECRET_KEY"] = "very-very-secret"
    os.environ["CANAILLE__SMTP__FROM_ADDR"] = "user@mydomain.tld"
    os.environ["CANAILLE_OIDC__REQUIRE_NONCE"] = "false"
    os.environ["CANAILLE_SQL__DATABASE_URI"] = "sqlite:///anything.db"

    conf = settings_factory({"TIMEZONE": "UTC"})
    assert conf.SECRET_KEY == "very-very-secret"
    assert conf.CANAILLE.SMTP.FROM_ADDR == "user@mydomain.tld"
    assert conf.CANAILLE_OIDC.REQUIRE_NONCE is False
    assert conf.CANAILLE_SQL.DATABASE_URI == "sqlite:///anything.db"

    app = create_app({"TIMEZONE": "UTC"})
    assert app.config["SECRET_KEY"] == "very-very-secret"
    assert app.config["CANAILLE"]["SMTP"]["FROM_ADDR"] == "user@mydomain.tld"
    assert app.config["CANAILLE_OIDC"]["REQUIRE_NONCE"] is False
    assert app.config["CANAILLE_SQL"]["DATABASE_URI"] == "sqlite:///anything.db"

    del os.environ["SECRET_KEY"]
    del os.environ["CANAILLE__SMTP__FROM_ADDR"]
    del os.environ["CANAILLE_OIDC__REQUIRE_NONCE"]
    del os.environ["CANAILLE_SQL__DATABASE_URI"]


def test_smtp_connection_remote_smtp_unreachable(testclient, backend, configuration):
    configuration["CANAILLE"]["SMTP"]["HOST"] = "smtp://invalid-smtp.com"
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()
    with pytest.raises(
        ConfigurationException,
        match=r"Could not connect to the SMTP server",
    ):
        validate(config_dict, validate_remote=True)


def test_smtp_connection_remote_smtp_wrong_credentials(
    testclient, backend, configuration
):
    configuration["CANAILLE"]["SMTP"]["PASSWORD"] = "invalid-password"
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()
    with pytest.raises(
        ConfigurationException,
        match=r"SMTP authentication failed with user",
    ):
        validate(config_dict, validate_remote=True)


def test_smtp_connection_remote_smtp_no_credentials(testclient, backend, configuration):
    del configuration["CANAILLE"]["SMTP"]["LOGIN"]
    del configuration["CANAILLE"]["SMTP"]["PASSWORD"]
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()
    validate(config_dict, validate_remote=True)


def test_smtp_bad_tls(testclient, backend, smtpd, configuration):
    configuration["CANAILLE"]["SMTP"]["TLS"] = False
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()
    with pytest.raises(
        ConfigurationException,
        match=r"SMTP AUTH extension not supported by server",
    ):
        validate(config_dict, validate_remote=True)


@pytest.fixture
def themed_testclient(app, configuration, backend):
    configuration["TESTING"] = True

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
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()

    validate(config_dict, validate_remote=False)

    with pytest.raises(
        ConfigurationException,
        match=r"Cannot find theme",
    ):
        configuration["CANAILLE"]["THEME"] = "invalid"
        config_obj = settings_factory(configuration)
        config_dict = config_obj.model_dump()
        validate(config_dict, validate_remote=False)

    with pytest.raises(
        ConfigurationException,
        match=r"Cannot find theme",
    ):
        configuration["CANAILLE"]["THEME"] = "/path/to/invalid"
        config_obj = settings_factory(configuration)
        config_dict = config_obj.model_dump()
        validate(config_dict, validate_remote=False)
