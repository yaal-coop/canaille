from canaille import create_app
from flask_webtest import TestApp


def test_ldap_connection_remote_ldap_unreachable(configuration):
    app = create_app(configuration)
    testclient = TestApp(app)

    app.config["BACKENDS"]["LDAP"]["URI"] = "ldap://invalid-ldap.com"

    app.config["DEBUG"] = True
    res = testclient.get("/", status=500, expect_errors=True)
    res.mustcontain("Could not connect to the LDAP server")

    app.config["DEBUG"] = False
    res = testclient.get("/", status=500, expect_errors=True)
    res.mustcontain(no="Could not connect to the LDAP server")


def test_ldap_connection_remote_ldap_wrong_credentials(configuration):
    app = create_app(configuration)
    testclient = TestApp(app)

    app.config["BACKENDS"]["LDAP"]["BIND_PW"] = "invalid-password"

    app.config["DEBUG"] = True
    res = testclient.get("/", status=500, expect_errors=True)
    res.mustcontain("LDAP authentication failed with user")

    app.config["DEBUG"] = False
    res = testclient.get("/", status=500, expect_errors=True)
    res.mustcontain(no="LDAP authentication failed with user")
