from unittest import mock

from canaille.ldap_backend.ldapobject import LDAPObject
from canaille.models import User


def test_index(testclient, user):
    res = testclient.get("/", status=302)
    assert res.location == "/login"

    with testclient.session_transaction() as sess:
        sess["user_id"] = [user.dn]
    res = testclient.get("/", status=302)
    assert res.location == "/profile/user"

    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = ["use_oidc"]
    res = testclient.get("/", status=302)
    assert res.location == "/consent/"

    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    res = testclient.get("/", status=302)
    assert res.location == "/about"


def test_signin_and_out(testclient, user):
    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/login", status=200)

    res.form["login"] = "John (johnny) Doe"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert "John (johnny) Doe" == session.get("attempt_login")

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()
    res = res.follow(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert [user.dn] == session.get("user_id")
        assert "attempt_login" not in session

    res = testclient.get("/login", status=302)

    res = testclient.get("/logout")
    res = res.follow(status=302)
    res = res.follow(status=200)
    assert "You have been disconnected. See you next time John (johnny) Doe" in res


def test_visitor_logout(testclient, user):
    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/logout")
    res = res.follow(status=302)
    res = res.follow(status=200)
    assert "You have been disconnected. See you next time user" not in res

    with testclient.session_transaction() as session:
        assert not session.get("user_id")


def test_signin_wrong_password(testclient, user):
    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/login", status=200)

    res.form["login"] = "John (johnny) Doe"
    res = res.form.submit(status=302)
    res = res.follow(status=200)
    res.form["password"] = "incorrect horse"
    res = res.form.submit(status=200)
    assert "Login failed, please check your information" in res.text


def test_signin_with_alternate_attribute(testclient, user):
    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()
    res = res.follow(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert [user.dn] == session.get("user_id")


def test_password_page_without_signin_in_redirects_to_login_page(testclient, user):
    res = testclient.get("/password", status=302)
    assert res.location == "/login"


def test_user_without_password_first_login(testclient, slapd_connection, smtpd):
    assert len(smtpd.messages) == 0
    User.ldap_object_classes(slapd_connection)
    u = User(
        cn="Temp User",
        sn="Temp",
        uid="temp",
        mail="john@doe.com",
    )
    u.save()

    res = testclient.get("/login", status=200)
    res.form["login"] = "Temp User"
    res = res.form.submit(status=302)

    assert res.location == "/firstlogin/temp"
    res = res.follow(status=200)
    assert "First login" in res

    res = res.form.submit(name="action", value="sendmail")
    assert (
        "A password initialization link has been sent at your email address. "
        "You should receive it within a few minutes."
    ) in res
    assert len(smtpd.messages) == 1
    assert "Password initialization" in smtpd.messages[0].get("Subject")
    u.delete()


@mock.patch("smtplib.SMTP")
def test_first_login_account_initialization_mail_sending_failed(
    SMTP, testclient, slapd_connection, smtpd
):
    SMTP.side_effect = mock.Mock(side_effect=OSError("unit test mail error"))
    assert len(smtpd.messages) == 0

    User.ldap_object_classes(slapd_connection)
    u = User(
        cn="Temp User",
        sn="Temp",
        uid="temp",
        mail="john@doe.com",
    )
    u.save()

    res = testclient.get("/firstlogin/temp")
    res = res.form.submit(name="action", value="sendmail", expect_errors=True)
    assert (
        "A password initialization link has been sent at your email address. "
        "You should receive it within a few minutes."
    ) not in res
    assert "Could not send the password initialization email" in res
    assert len(smtpd.messages) == 0
    u.delete()


def test_first_login_form_error(testclient, slapd_connection, smtpd):
    assert len(smtpd.messages) == 0
    User.ldap_object_classes(slapd_connection)
    u = User(
        cn="Temp User",
        sn="Temp",
        uid="temp",
        mail="john@doe.com",
    )
    u.save()

    res = testclient.get("/firstlogin/temp", status=200)
    res.form["csrf_token"] = "invalid"
    res = res.form.submit(name="action", value="sendmail")
    assert ("Could not send the password initialization link.") in res
    assert len(smtpd.messages) == 0
    u.delete()


def test_first_login_page_unavailable_for_users_with_password(
    testclient, slapd_connection, user
):
    testclient.get("/firstlogin/user", status=404)


def test_user_password_deleted_during_login(testclient, slapd_connection):
    User.ldap_object_classes(slapd_connection)
    u = User(
        cn="Temp User",
        sn="Temp",
        uid="temp",
        mail="john@doe.com",
        userPassword="{SSHA}Yr1ZxSljRsKyaTB30suY2iZ1KRTStF1X",
    )
    u.save()

    res = testclient.get("/login")
    res.form["login"] = "Temp User"
    res = res.form.submit().follow()
    res.form["password"] = "correct horse battery staple"

    u.userPassword = None
    u.save()

    res = res.form.submit(status=302)
    assert res.location == "/firstlogin/temp"

    u.delete()


def test_user_deleted_in_session(testclient, slapd_connection):
    User.ldap_object_classes(slapd_connection)
    u = User(
        cn="Jake Doe",
        sn="Jake",
        uid="jake",
        mail="jake@doe.com",
        userPassword="{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz",
    )
    u.save()
    testclient.get("/profile/jake", status=403)

    with testclient.session_transaction() as session:
        session["user_id"] = [u.dn]

    testclient.get("/profile/jake", status=200)
    u.delete()

    testclient.get("/profile/jake", status=403)
    with testclient.session_transaction() as session:
        assert not session.get("user_id")


def test_impersonate(testclient, logged_admin, user):
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


def test_wrong_login(testclient, user):
    testclient.app.config["HIDE_INVALID_LOGINS"] = True

    res = testclient.get("/login", status=200)
    res.form["login"] = "invalid"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = "incorrect horse"
    res = res.form.submit(status=200)
    assert "The login 'invalid' does not exist" not in res.text

    testclient.app.config["HIDE_INVALID_LOGINS"] = False

    res = testclient.get("/login", status=200)
    res.form["login"] = "invalid"
    res = res.form.submit(status=200)
    assert "The login &#39;invalid&#39; does not exist" in res.text


def test_admin_self_deletion(testclient, slapd_connection):
    LDAPObject.ldap_object_classes(slapd_connection)
    LDAPObject.ldap_object_attributes(slapd_connection)

    admin = User(
        cn="Temp admin",
        sn="admin",
        uid="temp",
        mail="temp@temp.com",
        userPassword="{SSHA}Vmgh2jkD0idX3eZHf8RzGos31oerjGiU",
    )
    admin.save()
    with testclient.session_transaction() as sess:
        sess["user_id"] = [admin.dn]

    res = testclient.get("/profile/temp")
    res = (
        res.form.submit(name="action", value="delete", status=302)
        .follow(status=302)
        .follow(status=200)
    )

    assert User.get("temp") is None

    with testclient.session_transaction() as sess:
        assert not sess.get("user_id")


def test_user_self_deletion(testclient, slapd_connection):
    LDAPObject.ldap_object_classes(slapd_connection)
    LDAPObject.ldap_object_attributes(slapd_connection)

    user = User(
        cn="Temp user",
        sn="user",
        uid="temp",
        mail="temp@temp.com",
        userPassword="{SSHA}Vmgh2jkD0idX3eZHf8RzGos31oerjGiU",
    )
    user.save()
    with testclient.session_transaction() as sess:
        sess["user_id"] = [user.dn]

    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = ["edit_self"]
    res = testclient.get("/profile/temp")
    assert "Delete my account" not in res

    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = [
        "edit_self",
        "delete_account",
    ]
    res = testclient.get("/profile/temp")
    assert "Delete my account" in res
    res = (
        res.form.submit(name="action", value="delete", status=302)
        .follow(status=302)
        .follow(status=200)
    )

    assert User.get("temp") is None

    with testclient.session_transaction() as sess:
        assert not sess.get("user_id")

    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = []


def test_login_placeholder(testclient):
    testclient.app.config["LDAP"]["USER_FILTER"] = "(uid={login})"
    placeholder = testclient.get("/login").form["login"].attrs["placeholder"]
    assert placeholder == "jdoe"

    testclient.app.config["LDAP"]["USER_FILTER"] = "(cn={login})"
    placeholder = testclient.get("/login").form["login"].attrs["placeholder"]
    assert placeholder == "John Doe"

    testclient.app.config["LDAP"]["USER_FILTER"] = "(mail={login})"
    placeholder = testclient.get("/login").form["login"].attrs["placeholder"]
    assert placeholder == "john@doe.com"

    testclient.app.config["LDAP"]["USER_FILTER"] = "(|(uid={login})(email={login}))"
    placeholder = testclient.get("/login").form["login"].attrs["placeholder"]
    assert placeholder == "jdoe or john@doe.com"


def test_photo(testclient, user, jpeg_photo):
    user.jpegPhoto = [jpeg_photo]
    user.save()
    res = testclient.get("/profile/user/jpegPhoto")
    assert res.body == jpeg_photo


def test_photo_invalid_user(testclient, user):
    res = testclient.get("/profile/invalid/jpegPhoto", status=404)


def test_photo_absent(testclient, user):
    assert not user.jpegPhoto
    res = testclient.get("/profile/user/jpegPhoto", status=404)


def test_photo_invalid_path(testclient, user):
    testclient.get("/profile/user/invalid", status=404)
