import os

import ldap
from canaille import create_app
from canaille.flaskutils import set_parameter_in_url_query
from canaille.installation import setup_ldap_tree
from canaille.ldap_backend.backend import setup_ldap_models
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


def test_logging_to_file(configuration, tmp_path, smtpd, admin, slapd_server):
    log_path = os.path.join(tmp_path, "canaille.log")
    logging_configuration = {
        **configuration,
        "LOGGING": {"LEVEL": "DEBUG", "PATH": log_path},
    }
    setup_ldap_models(logging_configuration)
    setup_ldap_tree(logging_configuration)
    app = create_app(logging_configuration)
    app.config["TESTING"] = True

    with app.app_context():
        g.ldap = ldap.ldapobject.SimpleLDAPObject(slapd_server.ldap_uri)
        g.ldap.protocol_version = 3
        g.ldap.simple_bind_s(slapd_server.root_dn, slapd_server.root_pw)

        testclient = TestApp(app)
        with testclient.session_transaction() as sess:
            sess["user_dn"] = [admin.dn]

        res = testclient.get("/admin/mail")
        res.form["mail"] = "test@test.com"
        res = res.form.submit()

        g.ldap.unbind_s()

    with open(log_path) as fd:
        log_content = fd.read()

    assert (
        "Sending a mail to test@test.com: You have been invited to create an account on"
        in log_content
    )
