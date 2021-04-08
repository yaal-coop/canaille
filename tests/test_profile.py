import mock
from canaille.models import User


def test_profile(testclient, slapd_connection, logged_user, foo_group):
    res = testclient.get("/profile/user", status=200)
    assert res.form["groups"].options == [('foo', False, 'foo')]

    res.form["uid"] = "user"
    res.form["givenName"] = "given_name"
    res.form["sn"] = "family_name"
    res.form["mail"] = "email@mydomain.tld"
    res.form["telephoneNumber"] = "555-666-777"
    res.form["employeeNumber"] = 666
    res.form["groups"] = ["foo", "bar"]
    res = res.form.submit(name="action", value="edit", status=200)
    assert "Profile updated successfuly." in res, str(res)

    logged_user.reload(slapd_connection)

    assert ["user"] == logged_user.uid
    assert ["given_name"] == logged_user.givenName
    assert ["family_name"] == logged_user.sn
    assert ["email@mydomain.tld"] == logged_user.mail
    assert ["555-666-777"] == logged_user.telephoneNumber
    assert "666" == logged_user.employeeNumber
    assert ["foo", "bar"] == logged_user.groups

    with testclient.app.app_context():
        assert logged_user.check_password("correct horse battery staple")


def test_bad_email(testclient, slapd_connection, logged_user):
    res = testclient.get("/profile/user", status=200)

    res.form["mail"] = "john@doe.com"

    res = res.form.submit(name="action", value="edit", status=200)

    assert ["john@doe.com"] == logged_user.mail

    res = testclient.get("/profile/user", status=200)

    res.form["mail"] = "yolo"

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
    res.form["uid"] = "george"
    res.form["givenName"] = "George"
    res.form["sn"] = "Abitbol"
    res.form["mail"] = "george@abitbol.com"
    res.form["telephoneNumber"] = "555-666-888"
    res.form["password1"] = "totoyolo"
    res.form["password2"] = "totoyolo"

    # User have been created
    res = res.form.submit(name="action", value="edit", status=302).follow(status=200)
    with testclient.app.app_context():
        assert "George" == User.get("george", conn=slapd_connection).givenName[0]
    assert "george" in testclient.get("/users", status=200).text
    res.form["givenName"] = "Georgio"

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


@mock.patch("smtplib.SMTP")
def test_first_login_mail_button(SMTP, testclient, slapd_connection, logged_admin):
    User.ocs_by_name(slapd_connection)
    u = User(
        objectClass=["inetOrgPerson"],
        cn="Temp User",
        sn="Temp",
        uid="temp",
        mail="john@doe.com",
    )
    u.save(slapd_connection)

    res = testclient.get("/profile/temp", status=200)
    assert "This user does not have a password yet" in res
    assert "Send" in res

    res = res.form.submit(
        name="action", value="password-initialization-mail", status=200
    )
    assert (
        "A password initialization link has been sent at the user email address. It should be received within 10 minutes."
        in res
    )
    assert "Send again" in res
    SMTP.assert_called_once_with(host="localhost", port=25)

    u.reload(slapd_connection)
    u.userPassword = ["{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz"]
    u.save(slapd_connection)

    res = testclient.get("/profile/temp", status=200)
    assert "This user does not have a password yet" not in res


@mock.patch("smtplib.SMTP")
def test_email_reset_button(SMTP, testclient, slapd_connection, logged_admin):
    User.ocs_by_name(slapd_connection)
    u = User(
        objectClass=["inetOrgPerson"],
        cn="Temp User",
        sn="Temp",
        uid="temp",
        mail="john@doe.com",
        userPassword=["{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz"],
    )
    u.save(slapd_connection)

    res = testclient.get("/profile/temp", status=200)
    assert "If the user has forgotten his password" in res
    assert "Send" in res

    res = res.form.submit(name="action", value="password-reset-mail", status=200)
    assert (
        "A password reset link has been sent at the user email address. It should be received within 10 minutes."
        in res
    )
    assert "Send again" in res
    SMTP.assert_called_once_with(host="localhost", port=25)
