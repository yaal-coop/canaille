def test_profile(testclient, slapd_connection, logged_user):
    res = testclient.get("/profile")
    assert 200 == res.status_code

    res.form["sub"] = "user"
    res.form["given_name"] = "given_name"
    res.form["family_name"] = "family_name"
    res.form["email"] = "email@mydomain.tld"
    res.form["phone_number"] = "555-666-777"

    res = res.form.submit()
    assert 200 == res.status_code

    logged_user.reload(slapd_connection)

    assert ["user"] == logged_user.uid
    assert ["given_name"] == logged_user.givenName
    assert ["family_name"] == logged_user.sn
    assert ["email@mydomain.tld"] == logged_user.mail
    assert ["555-666-777"] == logged_user.telephoneNumber
