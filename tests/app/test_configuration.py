import os

import pytest
from flask_webtest import TestApp

from canaille import create_app
from canaille.app.configuration import ConfigurationException
from canaille.app.configuration import validate


def test_configuration_file_suffix(tmp_path, backend, configuration):
    file_path = os.path.join(tmp_path, "secret.txt")
    with open(file_path, "w") as fd:
        fd.write("very-secret")

    del configuration["SECRET_KEY"]
    configuration["SECRET_KEY_FILE"] = file_path

    app = create_app(configuration)
    assert "SECRET_KEY_FILE" not in app.config
    assert app.config["SECRET_KEY"] == "very-secret"


def test_smtp_connection_remote_smtp_unreachable(testclient, backend, configuration):
    configuration["SMTP"]["HOST"] = "smtp://invalid-smtp.com"
    with pytest.raises(
        ConfigurationException,
        match=r"Could not connect to the SMTP server",
    ):
        validate(configuration, validate_remote=True)


def test_smtp_connection_remote_smtp_wrong_credentials(
    testclient, backend, configuration
):
    configuration["SMTP"]["PASSWORD"] = "invalid-password"
    with pytest.raises(
        ConfigurationException,
        match=r"SMTP authentication failed with user",
    ):
        validate(configuration, validate_remote=True)


def test_smtp_connection_remote_smtp_no_credentials(testclient, backend, configuration):
    del configuration["SMTP"]["LOGIN"]
    del configuration["SMTP"]["PASSWORD"]
    validate(configuration, validate_remote=True)


def test_smtp_bad_tls(testclient, backend, smtpd, configuration):
    configuration["SMTP"]["TLS"] = False
    with pytest.raises(
        ConfigurationException,
        match=r"SMTP AUTH extension not supported by server",
    ):
        validate(configuration, validate_remote=True)


@pytest.fixture
def themed_testclient(
    app,
    configuration,
    backend,
):
    configuration["TESTING"] = True

    root = os.path.dirname(os.path.abspath(__file__))
    test_theme_path = os.path.join(root, "fixtures", "themes", "test")
    configuration["THEME"] = test_theme_path

    app = create_app(configuration)

    return TestApp(app)


def test_theme(testclient, themed_testclient, backend):
    res = testclient.get("/login")
    res.mustcontain(no="TEST_THEME")

    res = themed_testclient.get("/login")
    res.mustcontain("TEST_THEME")


def test_invalid_theme(configuration, backend):
    validate(configuration, validate_remote=False)

    with pytest.raises(
        ConfigurationException,
        match=r"Cannot find theme",
    ):
        configuration["THEME"] = "invalid"
        validate(configuration, validate_remote=False)

    with pytest.raises(
        ConfigurationException,
        match=r"Cannot find theme",
    ):
        configuration["THEME"] = "/path/to/invalid"
        validate(configuration, validate_remote=False)
