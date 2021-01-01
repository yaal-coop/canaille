from canaille.models import User


def test_signin_and_out(testclient, slapd_connection, user):
    with testclient.session_transaction() as session:
        assert not session.get("user_dn")

    res = testclient.get("/login", status=200)

    res.form["login"] = "John Doe"
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()
    res = res.follow(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert [user.dn] == session.get("user_dn")

    res = testclient.get("/logout")
    res = res.follow(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert not session.get("user_dn")


def test_signin_wrong_password(testclient, slapd_connection, user):
    with testclient.session_transaction() as session:
        assert not session.get("user_dn")

    res = testclient.get("/login", status=200)

    res.form["login"] = "John Doe"
    res.form["password"] = "incorrect horse"
    res = res.form.submit(status=200)
    assert "Login failed, please check your information" in res.text


def test_signin_no_password(testclient, slapd_connection, user):
    with testclient.session_transaction() as session:
        assert not session.get("user_dn")

    res = testclient.get("/login", status=200)

    res.form["login"] = "John Doe"
    res.form["password"] = ""
    res = res.form.submit(status=200)
    assert "Login failed, please check your information" in res.text


def test_signin_with_alternate_attribute(testclient, slapd_connection, user):
    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()
    res = res.follow(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert [user.dn] == session.get("user_dn")


def test_user_without_password_first_login(testclient, slapd_connection):
    User.ocs_by_name(slapd_connection)
    u = User(
        objectClass=["inetOrgPerson"],
        cn="Temp User",
        sn="Temp",
        uid="temp",
        mail="john@doe.com",
    )
    u.save(slapd_connection)

    res = testclient.get("/login", status=200)
    res.form["login"] = "Temp User"
    res.form["password"] = "anything"
    res = res.form.submit(status=302).follow(status=200)

    assert "First login" in res
    u.delete(conn=slapd_connection)


def test_user_deleted_in_session(testclient, slapd_connection):
    User.ocs_by_name(slapd_connection)
    u = User(
        objectClass=["inetOrgPerson"],
        cn="Jake Doe",
        sn="Jake",
        uid="jake",
        mail="jake@doe.com",
        userPassword="{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz",
    )
    u.save(slapd_connection)
    testclient.get("/profile/jake", status=403)

    with testclient.session_transaction() as session:
        session["user_dn"] = [u.dn]

    testclient.get("/profile/jake", status=200)
    u.delete(conn=slapd_connection)

    testclient.get("/profile/jake", status=403)
    with testclient.session_transaction() as session:
        assert not session.get("user_dn")


def test_impersonate(testclient, slapd_connection, logged_admin, user):
    res = testclient.get("/", status=302).follow(status=200)
    assert "admin" == res.form["uid"].value

    res = (
        testclient.get("/impersonate/user", status=302)
        .follow(status=302)
        .follow(status=200)
    )
    assert "user" == res.form["uid"].value

    testclient.get("/logout", status=302).follow(status=302).follow(status=200)

    res = testclient.get("/", status=302).follow(status=200)
    assert "admin" == res.form["uid"].value


def test_wrong_login(testclient, slapd_connection, user):
    testclient.app.config["HIDE_INVALID_LOGINS"] = False

    res = testclient.get("/login", status=200)
    res.form["login"] = "invalid"
    res.form["password"] = "incorrect horse"
    res = res.form.submit(status=200)
    assert "The login 'invalid' does not exist" not in res.text

    testclient.app.config["HIDE_INVALID_LOGINS"] = True

    res = testclient.get("/login", status=200)
    res.form["login"] = "invalid"
    res.form["password"] = "incorrect horse"
    res = res.form.submit(status=200)
    assert "The login 'invalid' does not exist" in res.text
