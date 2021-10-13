import pytest
from canaille.commands import cli
from canaille.configuration import validate, ConfigurationException


def test_ldap_connection_no_remote(configuration):
    validate(configuration)


def test_no_private_key(configuration):
    configuration["JWT"]["PRIVATE_KEY"] = "invalid-path"
    with pytest.raises(
        ConfigurationException,
        match=r"Private key does not exist",
    ):
        validate(configuration)


def test_no_public_key(configuration):
    configuration["JWT"]["PUBLIC_KEY"] = "invalid-path"
    with pytest.raises(
        ConfigurationException,
        match=r"Public key does not exist",
    ):
        validate(configuration)


def test_ldap_connection_remote(configuration):
    validate(configuration, validate_remote=True)


def test_ldap_connection_remote_ldap_unreachable(configuration):
    configuration["LDAP"]["URI"] = "ldap://invalid-ldap.com"
    with pytest.raises(
        ConfigurationException,
        match=r"Could not connect to the LDAP server",
    ):
        validate(configuration, validate_remote=True)


def test_ldap_connection_remote_ldap_wrong_credentials(configuration):
    configuration["LDAP"]["BIND_PW"] = "invalid-password"
    with pytest.raises(
        ConfigurationException,
        match=r"LDAP authentication failed with user",
    ):
        validate(configuration, validate_remote=True)


def test_smtp_connection_remote_smtp_unreachable(configuration):
    configuration["SMTP"]["HOST"] = "smtp://invalid-smtp.com"
    with pytest.raises(
        ConfigurationException,
        match=r"Could not connect to the SMTP server",
    ):
        validate(configuration, validate_remote=True)


def test_smtp_connection_remote_smtp_wrong_credentials(configuration):
    configuration["SMTP"]["PASSWORD"] = "invalid-password"
    with pytest.raises(
        ConfigurationException,
        match=r"SMTP authentication failed with user",
    ):
        validate(configuration, validate_remote=True)


def test_check_command(testclient):
    runner = testclient.app.test_cli_runner()
    runner.invoke(cli, ["check"])


def test_check_command_fail(testclient):
    testclient.app.config["LDAP"]["URI"] = "ldap://invalid-ldap.com"
    runner = testclient.app.test_cli_runner()
    runner.invoke(cli, ["check"])
