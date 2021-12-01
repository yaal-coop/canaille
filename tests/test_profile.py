from canaille.models import User


def test_profile(
    testclient, slapd_server, slapd_connection, logged_user, admin, foo_group, bar_group
):
    res = testclient.get("/profile/user", status=200)
    assert set(res.form["groups"].options) == set(
        [
            ("cn=foo,ou=groups,dc=slapd-test,dc=python-ldap,dc=org", True, "foo"),
            ("cn=bar,ou=groups,dc=slapd-test,dc=python-ldap,dc=org", False, "bar"),
        ]
    )
    assert logged_user.groups == [foo_group]
    assert foo_group.member == [logged_user.dn]
    assert bar_group.member == [admin.dn]
    assert res.form["groups"].attrs["disabled"]
    assert res.form["uid"].attrs["readonly"]

    res.form["uid"] = "toto"
    res.form["givenName"] = "given_name"
    res.form["sn"] = "family_name"
    res.form["mail"] = "email@mydomain.tld"
    res.form["telephoneNumber"] = "555-666-777"
    res.form["employeeNumber"] = 666
    res.form["groups"] = [
        "cn=foo,ou=groups,dc=slapd-test,dc=python-ldap,dc=org",
        "cn=bar,ou=groups,dc=slapd-test,dc=python-ldap,dc=org",
    ]
    res = res.form.submit(name="action", value="edit", status=200)
    assert "Profile updated successfuly." in res, str(res)

    with testclient.app.app_context():
        logged_user = User.get(dn=logged_user.dn, conn=slapd_connection)
    assert ["user"] == logged_user.uid
    assert ["given_name"] == logged_user.givenName
    assert ["family_name"] == logged_user.sn
    assert ["email@mydomain.tld"] == logged_user.mail
    assert ["555-666-777"] == logged_user.telephoneNumber
    assert "666" == logged_user.employeeNumber

    foo_group.reload(slapd_connection)
    bar_group.reload(slapd_connection)
    assert logged_user.groups == [foo_group]
    assert foo_group.member == [logged_user.dn]
    assert bar_group.member == [admin.dn]

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
    testclient, slapd_connection, logged_moderator, foo_group, bar_group
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
        george = User.get("george", conn=slapd_connection)
        assert "George" == george.givenName[0]
        assert george.groups == []
        assert george.check_password("totoyolo")

    assert "george" in testclient.get("/users", status=200).text
    assert "disabled" not in res.form["groups"].attrs

    res.form["givenName"] = "Georgio"
    res.form["groups"] = [
        "cn=foo,ou=groups,dc=slapd-test,dc=python-ldap,dc=org",
        "cn=bar,ou=groups,dc=slapd-test,dc=python-ldap,dc=org",
    ]

    # User have been edited
    res = res.form.submit(name="action", value="edit", status=200)
    with testclient.app.app_context():
        george = User.get("george", conn=slapd_connection)
        assert "Georgio" == george.givenName[0]
        assert george.check_password("totoyolo")

    foo_group.reload(slapd_connection)
    bar_group.reload(slapd_connection)
    assert george.dn in set(foo_group.member)
    assert george.dn in set(bar_group.member)
    assert set(george.groups) == {foo_group, bar_group}
    assert "george" in testclient.get("/users", status=200).text
    assert "george" in testclient.get("/users", status=200).text

    # User have been deleted.
    res = res.form.submit(name="action", value="delete", status=302).follow(status=200)
    with testclient.app.app_context():
        assert User.get("george", conn=slapd_connection) is None
    assert "george" not in res.text


def test_first_login_mail_button(smtpd, testclient, slapd_connection, logged_admin):
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
    assert len(smtpd.messages) == 1

    u.reload(slapd_connection)
    u.userPassword = ["{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz"]
    u.save(slapd_connection)

    res = testclient.get("/profile/temp", status=200)
    assert "This user does not have a password yet" not in res


def test_email_reset_button(smtpd, testclient, slapd_connection, logged_admin):
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
    assert "If the user has forgotten his password" in res, res.text
    assert "Send" in res

    res = res.form.submit(name="action", value="password-reset-mail", status=200)
    assert (
        "A password reset link has been sent at the user email address. It should be received within 10 minutes."
        in res
    )
    assert "Send again" in res
    assert len(smtpd.messages) == 1
