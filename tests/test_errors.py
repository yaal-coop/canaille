def test_ldap_connection_remote_ldap_unreachable(testclient):
    testclient.app.config["LDAP"]["URI"] = "ldap://invalid-ldap.com"

    testclient.app.config["DEBUG"] = True
    res = testclient.get("/", status=500, expect_errors=True)
    assert "Could not connect to the LDAP server" in res.text

    testclient.app.config["DEBUG"] = False
    res = testclient.get("/", status=500, expect_errors=True)
    assert "Could not connect to the LDAP server" not in res.text


def test_ldap_connection_remote_ldap_wrong_credentials(testclient):
    testclient.app.config["LDAP"]["BIND_PW"] = "invalid-password"

    testclient.app.config["DEBUG"] = True
    res = testclient.get("/", status=500, expect_errors=True)
    assert "LDAP authentication failed with user" in res.text

    testclient.app.config["DEBUG"] = False
    res = testclient.get("/", status=500, expect_errors=True)
    assert "LDAP authentication failed with user" not in res.text
