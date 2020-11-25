from canaille.models import User


def test_profile(testclient, slapd_connection, logged_user):
    res = testclient.get("/profile/user", status=200)

    res.form["sub"] = "user"
    res.form["given_name"] = "given_name"
    res.form["family_name"] = "family_name"
    res.form["email"] = "email@mydomain.tld"
    res.form["phone_number"] = "555-666-777"

    res = res.form.submit(name="action", value="edit", status=200)

    logged_user.reload(slapd_connection)

    assert ["user"] == logged_user.uid
    assert ["given_name"] == logged_user.givenName
    assert ["family_name"] == logged_user.sn
    assert ["email@mydomain.tld"] == logged_user.mail
    assert ["555-666-777"] == logged_user.telephoneNumber

    with testclient.app.app_context():
        assert logged_user.check_password("correct horse battery staple")


def test_bad_email(testclient, slapd_connection, logged_user):
    res = testclient.get("/profile/user", status=200)

    res.form["email"] = "john@doe.com"

    res = res.form.submit(name="action", value="edit", status=200)

    assert ["john@doe.com"] == logged_user.mail

    res = testclient.get("/profile/user", status=200)

    res.form["email"] = "yolo"

    res = res.form.submit(name="action", value="edit", status=200)

    logged_user.reload(slapd_connection)

    assert ["john@doe.com"] == logged_user.mail


def test_password_change(testclient, slapd_connection, logged_user):
    res = testclient.get("/profile/user", status=200)

    res.form["password1"] = "new_password"
    res.form["password2"] = "new_password"

    res = res.form.submit(name="action", value="edit", status=200)

    with testclient.app.app_context():
        assert logged_user.check_password("new_password")

    res = testclient.get("/profile/user", status=200)

    res.form["password1"] = "correct horse battery staple"
    res.form["password2"] = "correct horse battery staple"

    res = res.form.submit(name="action", value="edit", status=200)
    assert "Profile updated successfuly" in res

    with testclient.app.app_context():
        assert logged_user.check_password("correct horse battery staple")


def test_password_change_fail(testclient, slapd_connection, logged_user):
    res = testclient.get("/profile/user", status=200)

    res.form["password1"] = "new_password"
    res.form["password2"] = "other_password"

    res = res.form.submit(name="action", value="edit", status=200)

    with testclient.app.app_context():
        assert logged_user.check_password("correct horse battery staple")

    res = testclient.get("/profile/user", status=200)

    res.form["password1"] = "new_password"
    res.form["password2"] = ""

    res = res.form.submit(name="action", value="edit", status=200)

    with testclient.app.app_context():
        assert logged_user.check_password("correct horse battery staple")


def test_simple_user_cannot_edit_other(testclient, logged_user):
    testclient.get("/profile/user", status=200)
    testclient.get("/profile/admin", status=403)
    testclient.post("/profile/admin", {"action": "edit"}, status=403)
    testclient.post("/profile/admin", {"action": "delete"}, status=403)
    testclient.get("/users", status=403)


def test_admin_bad_request(testclient, logged_moderator):
    testclient.post("/profile/admin", {"action": "foobar"}, status=400)
    testclient.get("/profile/foobar", status=404)


def test_user_creation_edition_and_deletion(
    testclient, slapd_connection, logged_moderator
):
    # The user does not exist.
    res = testclient.get("/users", status=200)
    with testclient.app.app_context():
        assert User.get("george", conn=slapd_connection) is None
    assert "george" not in res.text

    # Fill the profile for a new user.
    res = testclient.get("/profile", status=200)
    res.form["sub"] = "george"
    res.form["given_name"] = "George"
    res.form["family_name"] = "Abitbol"
    res.form["email"] = "george@abitbol.com"
    res.form["phone_number"] = "555-666-888"
    res.form["password1"] = "totoyolo"
    res.form["password2"] = "totoyolo"

    # User have been created
    res = res.form.submit(name="action", value="edit", status=302).follow(status=200)
    with testclient.app.app_context():
        assert "George" == User.get("george", conn=slapd_connection).givenName[0]
    assert "george" in testclient.get("/users", status=200).text
    res.form["given_name"] = "Georgio"

    # User have been edited
    res = res.form.submit(name="action", value="edit", status=200)
    with testclient.app.app_context():
        assert "Georgio" == User.get("george", conn=slapd_connection).givenName[0]
    assert "george" in testclient.get("/users", status=200).text

    # User have been deleted.
    res = res.form.submit(name="action", value="delete", status=302).follow(status=200)
    with testclient.app.app_context():
        assert User.get("george", conn=slapd_connection) is None
    assert "george" not in res.text


def test_admin_self_deletion(testclient, slapd_connection):
    User.ocs_by_name(slapd_connection)
    admin = User(
        objectClass=["inetOrgPerson"],
        cn="Temp admin",
        sn="admin",
        uid="temp",
        mail="temp@temp.com",
        userPassword="{SSHA}Vmgh2jkD0idX3eZHf8RzGos31oerjGiU",
    )
    admin.save(slapd_connection)
    with testclient.session_transaction() as sess:
        sess["user_dn"] = admin.dn

    res = testclient.get("/profile/temp")
    res = (
        res.form.submit(name="action", value="delete", status=302)
        .follow(status=302)
        .follow(status=200)
    )

    with testclient.app.app_context():
        assert User.get("temp", conn=slapd_connection) is None

    with testclient.session_transaction() as sess:
        "user_dn" not in sess
