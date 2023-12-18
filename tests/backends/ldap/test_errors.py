import pytest
from flask_webtest import TestApp

from canaille import create_app


@pytest.fixture
def configuration(slapd_server, ldap_configuration):
    yield ldap_configuration


def test_ldap_connection_remote_ldap_unreachable(configuration):
    app = create_app(configuration)
    testclient = TestApp(app)

    app.config["CANAILLE_LDAP"]["URI"] = "ldap://invalid-ldap.com"

    app.config["DEBUG"] = False
    res = testclient.get("/", status=500, expect_errors=True)
    res.mustcontain(no="Could not connect to the LDAP server")


def test_ldap_connection_remote_ldap_wrong_credentials(configuration):
    app = create_app(configuration)
    testclient = TestApp(app)

    app.config["CANAILLE_LDAP"]["BIND_PW"] = "invalid-password"

    app.config["DEBUG"] = False
    res = testclient.get("/", status=500, expect_errors=True)
    res.mustcontain(no="LDAP authentication failed with user")
