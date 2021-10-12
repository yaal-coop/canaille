import ldap
import pytest
import smtplib
import socket
from canaille.configuration import validate


def test_ldap_connection_no_remote(configuration):
    validate(configuration)


def test_ldap_connection_remote(configuration):
    validate(configuration, validate_remote=True)


def test_ldap_connection_remote_ldap_unreachable(configuration):
    configuration["LDAP"]["URI"] = "ldap://invalid-ldap.com"
    with pytest.raises(ldap.SERVER_DOWN):
        validate(configuration, validate_remote=True)


def test_ldap_connection_remote_ldap_wrong_credentials(configuration):
    configuration["LDAP"]["BIND_PW"] = "invalid-password"
    with pytest.raises(ldap.INVALID_CREDENTIALS):
        validate(configuration, validate_remote=True)


def test_smtp_connection_remote_smtp_unreachable(configuration):
    configuration["SMTP"]["HOST"] = "smtp://invalid-smtp.com"
    with pytest.raises(socket.gaierror):
        validate(configuration, validate_remote=True)


def test_smtp_connection_remote_smtp_wrong_credentials(configuration):
    configuration["SMTP"]["PASSWORD"] = "invalid-password"
    with pytest.raises(smtplib.SMTPAuthenticationError):
        validate(configuration, validate_remote=True)
