def test_ldap_connection_remote_ldap_unreachable(testclient):
    testclient.app.config["TESTING"] = False

    testclient.app.config["BACKENDS"]["LDAP"]["URI"] = "ldap://invalid-ldap.com"

    testclient.app.config["DEBUG"] = True
    res = testclient.get("/", status=500, expect_errors=True)
    res.mustcontain("Could not connect to the LDAP server")

    testclient.app.config["DEBUG"] = False
    res = testclient.get("/", status=500, expect_errors=True)
    res.mustcontain(no="Could not connect to the LDAP server")


def test_ldap_connection_remote_ldap_wrong_credentials(testclient):
    testclient.app.config["TESTING"] = False

    testclient.app.config["BACKENDS"]["LDAP"]["BIND_PW"] = "invalid-password"

    testclient.app.config["DEBUG"] = True
    res = testclient.get("/", status=500, expect_errors=True)
    res.mustcontain("LDAP authentication failed with user")

    testclient.app.config["DEBUG"] = False
    res = testclient.get("/", status=500, expect_errors=True)
    res.mustcontain(no="LDAP authentication failed with user")
