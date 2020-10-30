def test_profile(testclient, slapd_connection, logged_user):
    res = testclient.get("/profile", status=200)

    res.form["sub"] = "user"
    res.form["given_name"] = "given_name"
    res.form["family_name"] = "family_name"
    res.form["email"] = "email@mydomain.tld"
    res.form["phone_number"] = "555-666-777"

    res = res.form.submit(status=200)

    logged_user.reload(slapd_connection)

    assert ["user"] == logged_user.uid
    assert ["given_name"] == logged_user.givenName
    assert ["family_name"] == logged_user.sn
    assert ["email@mydomain.tld"] == logged_user.mail
    assert ["555-666-777"] == logged_user.telephoneNumber

    with testclient.app.app_context():
        assert logged_user.check_password("correct horse battery staple")


def test_bad_email(testclient, slapd_connection, logged_user):
    res = testclient.get("/profile", status=200)

    res.form["email"] = "john@doe.com"

    res = res.form.submit(status=200)

    assert ["john@doe.com"] == logged_user.mail

    res = testclient.get("/profile", status=200)

    res.form["email"] = "yolo"

    res = res.form.submit(status=200)

    logged_user.reload(slapd_connection)

    assert ["john@doe.com"] == logged_user.mail


def test_password_change(testclient, slapd_connection, logged_user):
    res = testclient.get("/profile", status=200)

    res.form["password1"] = "new_password"
    res.form["password2"] = "new_password"

    res = res.form.submit(status=200)

    with testclient.app.app_context():
        assert logged_user.check_password("new_password")

    res = testclient.get("/profile", status=200)

    res.form["password1"] = "correct horse battery staple"
    res.form["password2"] = "correct horse battery staple"

    res = res.form.submit(status=200)

    with testclient.app.app_context():
        assert logged_user.check_password("correct horse battery staple")


def test_password_change_fail(testclient, slapd_connection, logged_user):
    res = testclient.get("/profile", status=200)

    res.form["password1"] = "new_password"
    res.form["password2"] = "other_password"

    res = res.form.submit(status=200)

    with testclient.app.app_context():
        assert logged_user.check_password("correct horse battery staple")

    res = testclient.get("/profile", status=200)

    res.form["password1"] = "new_password"
    res.form["password2"] = ""

    res = res.form.submit(status=200)

    with testclient.app.app_context():
        assert logged_user.check_password("correct horse battery staple")
