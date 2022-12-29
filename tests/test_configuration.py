import os
from unittest import mock

import ldap
import pytest
from canaille import create_app
from canaille.configuration import ConfigurationException
from canaille.configuration import validate
from flask_webtest import TestApp


def test_ldap_connection_no_remote(testclient, configuration):
    validate(configuration)


def test_ldap_connection_remote(testclient, configuration, slapd_connection):
    validate(configuration, validate_remote=True)


def test_ldap_connection_remote_ldap_unreachable(testclient, configuration):
    configuration["LDAP"]["URI"] = "ldap://invalid-ldap.com"
    with pytest.raises(
        ConfigurationException,
        match=r"Could not connect to the LDAP server",
    ):
        validate(configuration, validate_remote=True)


def test_ldap_connection_remote_ldap_wrong_credentials(testclient, configuration):
    configuration["LDAP"]["BIND_PW"] = "invalid-password"
    with pytest.raises(
        ConfigurationException,
        match=r"LDAP authentication failed with user",
    ):
        validate(configuration, validate_remote=True)


def test_ldap_cannot_create_users(testclient, configuration, slapd_connection):
    from canaille.models import User

    def fake_init(*args, **kwarg):
        raise ldap.INSUFFICIENT_ACCESS

    with mock.patch.object(User, "__init__", fake_init):
        with pytest.raises(
            ConfigurationException,
            match=r"cannot create users at",
        ):
            validate(configuration, validate_remote=True)


def test_ldap_cannot_create_groups(testclient, configuration, slapd_connection):
    from canaille.models import Group

    def fake_init(*args, **kwarg):
        raise ldap.INSUFFICIENT_ACCESS

    with mock.patch.object(Group, "__init__", fake_init):
        with pytest.raises(
            ConfigurationException,
            match=r"cannot create groups at",
        ):
            validate(configuration, validate_remote=True)


def test_smtp_connection_remote_smtp_unreachable(testclient, configuration):
    configuration["SMTP"]["HOST"] = "smtp://invalid-smtp.com"
    with pytest.raises(
        ConfigurationException,
        match=r"Could not connect to the SMTP server",
    ):
        validate(configuration, validate_remote=True)


def test_smtp_connection_remote_smtp_wrong_credentials(testclient, configuration):
    configuration["SMTP"]["PASSWORD"] = "invalid-password"
    with pytest.raises(
        ConfigurationException,
        match=r"SMTP authentication failed with user",
    ):
        validate(configuration, validate_remote=True)


def test_smtp_connection_remote_smtp_no_credentials(testclient, configuration):
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
def themed_testclient(app, configuration):
    configuration["TESTING"] = True

    root = os.path.dirname(os.path.abspath(__file__))
    test_theme_path = os.path.join(root, "fixtures", "themes", "test")
    configuration["THEME"] = test_theme_path

    app = create_app(configuration)

    return TestApp(app)


def test_theme(testclient, themed_testclient):
    res = testclient.get("/login")
    assert "TEST_THEME" not in res

    res = themed_testclient.get("/login")
    assert "TEST_THEME" in res


def test_invalid_theme(configuration):
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
