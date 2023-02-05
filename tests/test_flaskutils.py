import os

import ldap
import pytest
import toml
from canaille import create_app
from canaille.flaskutils import set_parameter_in_url_query
from flask import g
from flask_webtest import TestApp


def test_set_parameter_in_url_query():
    assert (
        set_parameter_in_url_query("https://auth.mydomain.tld", foo="bar")
        == "https://auth.mydomain.tld?foo=bar"
    )

    assert (
        set_parameter_in_url_query("https://auth.mydomain.tld?foo=baz", foo="bar")
        == "https://auth.mydomain.tld?foo=bar"
    )

    assert (
        set_parameter_in_url_query("https://auth.mydomain.tld?foo=baz", hello="world")
        == "https://auth.mydomain.tld?foo=baz&hello=world"
    )


def test_environment_configuration(slapd_server, configuration, tmp_path):
    config_path = os.path.join(tmp_path, "config.toml")
    with open(config_path, "w") as fd:
        toml.dump(configuration, fd)

    os.environ["CONFIG"] = config_path
    app = create_app()
    assert app.config["LDAP"]["ROOT_DN"] == slapd_server.suffix

    del os.environ["CONFIG"]
    os.remove(config_path)


def test_no_configuration():
    with pytest.raises(Exception) as exc:
        create_app()

    assert "No configuration file found." in str(exc)


def test_logging_to_file(configuration, tmp_path, smtpd, admin, slapd_server):
    assert len(smtpd.messages) == 0
    log_path = os.path.join(tmp_path, "canaille.log")
    logging_configuration = {
        **configuration,
        "LOGGING": {"LEVEL": "DEBUG", "PATH": log_path},
    }
    app = create_app(logging_configuration)
    app.config["TESTING"] = True

    with app.app_context():
        g.ldap_connection = ldap.ldapobject.SimpleLDAPObject(slapd_server.ldap_uri)
        g.ldap_connection.protocol_version = 3
        g.ldap_connection.simple_bind_s(slapd_server.root_dn, slapd_server.root_pw)

        testclient = TestApp(app)
        with testclient.session_transaction() as sess:
            sess["user_id"] = [admin.id]

        res = testclient.get("/admin/mail")
        res.form["mail"] = "test@test.com"
        res = res.form.submit()

        g.ldap_connection.unbind_s()

    assert len(smtpd.messages) == 1
    assert "Test email from" in smtpd.messages[0].get("Subject")

    with open(log_path) as fd:
        log_content = fd.read()

    assert "Sending a mail to test@test.com: Test email from" in log_content
