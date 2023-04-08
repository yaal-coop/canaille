import os

import pytest
from canaille import create_app
from canaille.app.configuration import ConfigurationException
from canaille.app.configuration import validate
from flask_webtest import TestApp


def test_smtp_connection_remote_smtp_unreachable(
    testclient, slapd_connection, configuration
):
    configuration["SMTP"]["HOST"] = "smtp://invalid-smtp.com"
    with pytest.raises(
        ConfigurationException,
        match=r"Could not connect to the SMTP server",
    ):
        validate(configuration, validate_remote=True)


def test_smtp_connection_remote_smtp_wrong_credentials(
    testclient, slapd_connection, configuration
):
    configuration["SMTP"]["PASSWORD"] = "invalid-password"
    with pytest.raises(
        ConfigurationException,
        match=r"SMTP authentication failed with user",
    ):
        validate(configuration, validate_remote=True)


def test_smtp_connection_remote_smtp_no_credentials(
    testclient, slapd_connection, configuration
):
    del configuration["SMTP"]["LOGIN"]
    del configuration["SMTP"]["PASSWORD"]
    validate(configuration, validate_remote=True)


def test_smtp_bad_tls(testclient, slapd_connection, smtpd, configuration):
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
    slapd_connection,
):
    configuration["TESTING"] = True

    root = os.path.dirname(os.path.abspath(__file__))
    test_theme_path = os.path.join(root, "fixtures", "themes", "test")
    configuration["THEME"] = test_theme_path

    app = create_app(configuration)

    return TestApp(app)


def test_theme(testclient, themed_testclient, slapd_connection):
    res = testclient.get("/login")
    res.mustcontain(no="TEST_THEME")

    res = themed_testclient.get("/login")
    res.mustcontain("TEST_THEME")


def test_invalid_theme(configuration, slapd_connection):
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
