from canaille.account import profile_hash


def test_password_reset(testclient, user):
    user.ldap_object_attributes()
    user.reload()
    hash = profile_hash("user", user.mail[0], user.userPassword[0])

    res = testclient.get("/reset/user/" + hash, status=200)

    res.form["password"] = "foobarbaz"
    res.form["confirmation"] = "foobarbaz"
    res = res.form.submit(status=302)

    res = res.follow(status=200)

    assert user.check_password("foobarbaz")
    assert "Your password has been updated successfuly" in res.text
    user.set_password("correct horse battery staple")

    res = testclient.get("/reset/user/" + hash)
    res = res.follow()
    res = res.follow()
    assert "The password reset link that brought you here was invalid." in res.text


def test_password_reset_bad_link(testclient, user):
    user.ldap_object_attributes()
    user.reload()

    res = testclient.get("/reset/user/foobarbaz")
    res = res.follow()
    res = res.follow()
    assert "The password reset link that brought you here was invalid." in res.text


def test_password_reset_bad_password(testclient, user):
    user.ldap_object_attributes()
    user.reload()
    hash = profile_hash("user", user.mail[0], user.userPassword[0])

    res = testclient.get("/reset/user/" + hash, status=200)

    res.form["password"] = "foobarbaz"
    res.form["confirmation"] = "typo"
    res = res.form.submit(status=200)

    assert user.check_password("correct horse battery staple")


def test_unavailable_if_no_smtp(testclient, user):
    res = testclient.get("/login")
    assert "Forgotten password" in res.text

    res.form["login"] = "John (johnny) Doe"
    res = res.form.submit()
    res = res.follow()
    assert "Forgotten password" in res.text

    testclient.get("/reset", status=200)

    del testclient.app.config["SMTP"]

    res = testclient.get("/login")
    assert "Forgotten password" not in res.text

    res.form["login"] = "John (johnny) Doe"
    res = res.form.submit()
    res = res.follow()
    assert "Forgotten password" not in res.text

    testclient.get("/reset", status=500, expect_errors=True)
