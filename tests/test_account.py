import mock
from canaille.account import profile_hash


def test_login_and_out(testclient, slapd_connection, user):
    with testclient.session_transaction() as session:
        assert session.get("user_dn") is None

    res = testclient.get("/login", status=200)

    res.form["login"] = "John Doe"
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()
    res = res.follow()
    res = res.follow()
    assert 200 == res.status_code

    with testclient.session_transaction() as session:
        assert user.dn == session.get("user_dn")

    res = testclient.get("/logout")
    res = res.follow()
    res = res.follow()
    assert 200 == res.status_code

    with testclient.session_transaction() as session:
        assert session.get("user_dn") is None


def test_login_wrong_password(testclient, slapd_connection, user):
    with testclient.session_transaction() as session:
        assert session.get("user_dn") is None

    res = testclient.get("/login", status=200)

    res.form["login"] = "John Doe"
    res.form["password"] = "incorrect horse"
    res = res.form.submit()
    assert 200 == res.status_code
    assert b"Login failed, please check your information" in res.body


def test_login_no_password(testclient, slapd_connection, user):
    with testclient.session_transaction() as session:
        assert session.get("user_dn") is None

    res = testclient.get("/login", status=200)

    res.form["login"] = "John Doe"
    res.form["password"] = ""
    res = res.form.submit()
    assert 200 == res.status_code
    assert b"Login failed, please check your information" in res.body


def test_login_with_alternate_attribute(testclient, slapd_connection, user):
    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()
    res = res.follow()
    assert 302 == res.status_code
    res = res.follow()
    assert 200 == res.status_code

    with testclient.session_transaction() as session:
        assert user.dn == session.get("user_dn")


@mock.patch("smtplib.SMTP")
def test_password_forgotten(SMTP, testclient, slapd_connection, user):
    res = testclient.get("/reset", status=200)

    res.form["login"] = "user"
    res = res.form.submit()
    assert 200 == res.status_code
    assert "A password reset link has been sent at your email address." in res.text

    SMTP.assert_called_once_with(host="localhost", port=25)


@mock.patch("smtplib.SMTP")
def test_password_forgotten_invalid_form(SMTP, testclient, slapd_connection, user):
    res = testclient.get("/reset", status=200)

    res.form["login"] = ""
    res = res.form.submit()
    assert 200 == res.status_code
    assert "Could not send the password reset link." in res.text

    SMTP.assert_not_called()


@mock.patch("smtplib.SMTP")
def test_password_forgotten_invalid(SMTP, testclient, slapd_connection, user):
    res = testclient.get("/reset", status=200)

    res.form["login"] = "i-dont-really-exist"
    res = res.form.submit()
    assert 200 == res.status_code
    assert "A password reset link has been sent at your email address." in res.text

    SMTP.assert_not_called()


def test_password_reset(testclient, slapd_connection, user):
    user.attr_type_by_name(conn=slapd_connection)
    user.reload(conn=slapd_connection)
    with testclient.app.app_context():
        hash = profile_hash("user", user.userPassword[0])

    res = testclient.get("/reset/user/" + hash, status=200)

    res.form["password"] = "foobarbaz"
    res.form["confirmation"] = "foobarbaz"
    res = res.form.submit()
    assert 302 == res.status_code

    res = res.follow()
    assert 200 == res.status_code

    with testclient.app.app_context():
        assert user.check_password("foobarbaz")
    assert "Your password has been updated successfuly" in res.text
    user.set_password("correct horse battery staple", conn=slapd_connection)

    res = testclient.get("/reset/user/" + hash)
    res = res.follow()
    res = res.follow()
    assert "The password reset link that brought you here was invalid." in res.text


def test_password_reset_bad_link(testclient, slapd_connection, user):
    user.attr_type_by_name(conn=slapd_connection)
    user.reload(conn=slapd_connection)

    res = testclient.get("/reset/user/foobarbaz")
    res = res.follow()
    res = res.follow()
    assert "The password reset link that brought you here was invalid." in res.text


def test_password_reset_bad_password(testclient, slapd_connection, user):
    user.attr_type_by_name(conn=slapd_connection)
    user.reload(conn=slapd_connection)
    with testclient.app.app_context():
        hash = profile_hash("user", user.userPassword[0])

    res = testclient.get("/reset/user/" + hash, status=200)

    res.form["password"] = "foobarbaz"
    res.form["confirmation"] = "typo"
    res = res.form.submit()
    assert 200 == res.status_code

    with testclient.app.app_context():
        assert user.check_password("correct horse battery staple")
