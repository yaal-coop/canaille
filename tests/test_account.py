def test_login_and_out(testclient, slapd_connection, user, client):
    with testclient.session_transaction() as session:
        assert session.get("user_dn") is None

    res = testclient.get("/login")
    assert 200 == res.status_code

    res.form["login"] = "John Doe"
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()
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


def test_login_wrong_password(testclient, slapd_connection, user, client):
    with testclient.session_transaction() as session:
        assert session.get("user_dn") is None

    res = testclient.get("/login")
    assert 200 == res.status_code

    res.form["login"] = "John Doe"
    res.form["password"] = "incorrect horse"
    res = res.form.submit()
    assert 200 == res.status_code
    assert b"Login failed, please check your information" in res.body


def test_login_no_password(testclient, slapd_connection, user, client):
    with testclient.session_transaction() as session:
        assert session.get("user_dn") is None

    res = testclient.get("/login")
    assert 200 == res.status_code

    res.form["login"] = "John Doe"
    res.form["password"] = ""
    res = res.form.submit()
    assert 200 == res.status_code
    assert b"Login failed, please check your information" in res.body
