import datetime
from unittest import mock

from flask import g

from canaille.app import models


def test_index(testclient, user):
    res = testclient.get("/", status=302)
    assert res.location == "/login"

    g.user = user
    res = testclient.get("/", status=302)
    assert res.location == "/profile/user"

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    g.user.reload()
    res = testclient.get("/", status=302)
    assert res.location == "/about"


def test_signin_and_out(testclient, user):
    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert "user" == session.get("attempt_login")

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()

    assert (
        "success",
        "Connection successful. Welcome John (johnny) Doe",
    ) in res.flashes
    res = res.follow(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert [user.id] == session.get("user_id")
        assert "attempt_login" not in session

    res = testclient.get("/login", status=302)

    res = testclient.get("/logout")
    assert (
        "success",
        "You have been disconnected. See you next time John (johnny) Doe",
    ) in res.flashes
    res = res.follow(status=302)
    res = res.follow(status=200)


def test_visitor_logout(testclient, user):
    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/logout")
    res = res.follow(status=302)
    res = res.follow(status=200)
    assert (
        "success",
        "You have been disconnected. See you next time user",
    ) not in res.flashes

    with testclient.session_transaction() as session:
        assert not session.get("user_id")


def test_signin_wrong_password(testclient, user):
    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)
    res.form["password"] = "incorrect horse"
    res = res.form.submit(status=200)
    assert ("error", "Login failed, please check your information") in res.flashes


def test_signin_password_substring(testclient, user):
    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)
    res.form["password"] = "c"
    res = res.form.submit(status=200)
    assert ("error", "Login failed, please check your information") in res.flashes


def test_signin_bad_csrf(testclient, user):
    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/login", status=200)

    res.form["login"] = "John (johnny) Doe"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = ""
    res = res.form.submit(status=200)
    assert ("error", "Login failed, please check your information") in res.flashes


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
        assert [user.id] == session.get("user_id")


def test_password_page_without_signin_in_redirects_to_login_page(testclient, user):
    res = testclient.get("/password", status=302)
    assert res.location == "/login"


def test_user_without_password_first_login(testclient, backend, smtpd):
    assert len(smtpd.messages) == 0
    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.com", "johhny@doe.com"],
    )
    u.save()

    res = testclient.get("/login", status=200)
    res.form["login"] = "temp"
    res = res.form.submit(status=302)

    assert res.location == "/firstlogin/temp"
    res = res.follow(status=200)
    res.mustcontain("First login")

    res = res.form.submit(name="action", value="sendmail")
    assert (
        "success",
        "A password initialization link has been sent at your email address. "
        "You should receive it within a few minutes.",
    ) in res.flashes
    assert len(smtpd.messages) == 2
    assert [message["X-RcptTo"] for message in smtpd.messages] == u.emails
    assert "Password initialization" in smtpd.messages[0].get("Subject")
    u.delete()


@mock.patch("smtplib.SMTP")
def test_first_login_account_initialization_mail_sending_failed(
    SMTP, testclient, backend, smtpd
):
    SMTP.side_effect = mock.Mock(side_effect=OSError("unit test mail error"))
    assert len(smtpd.messages) == 0

    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.com"],
    )
    u.save()

    res = testclient.get("/firstlogin/temp")
    res = res.form.submit(name="action", value="sendmail", expect_errors=True)
    assert (
        "success",
        "A password initialization link has been sent at your email address. "
        "You should receive it within a few minutes.",
    ) not in res.flashes
    assert ("error", "Could not send the password initialization email") in res.flashes
    assert len(smtpd.messages) == 0
    u.delete()


def test_first_login_form_error(testclient, backend, smtpd):
    assert len(smtpd.messages) == 0
    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.com"],
    )
    u.save()

    res = testclient.get("/firstlogin/temp", status=200)
    res.form["csrf_token"] = "invalid"
    res = res.form.submit(
        name="action", value="sendmail", status=400, expect_errors=True
    )
    assert len(smtpd.messages) == 0
    u.delete()


def test_first_login_page_unavailable_for_users_with_password(
    testclient, backend, user
):
    testclient.get("/firstlogin/user", status=404)


def test_user_password_deleted_during_login(testclient, backend):
    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.com"],
        password="correct horse battery staple",
    )
    u.save()

    res = testclient.get("/login")
    res.form["login"] = "temp"
    res = res.form.submit().follow()
    res.form["password"] = "correct horse battery staple"

    u.password = None
    u.save()

    res = res.form.submit(status=302)
    assert res.location == "/firstlogin/temp"

    u.delete()


def test_user_deleted_in_session(testclient, backend):
    u = models.User(
        formatted_name="Jake Doe",
        family_name="Jake",
        user_name="jake",
        emails=["jake@doe.com"],
        password="correct horse battery staple",
    )
    u.save()
    testclient.get("/profile/jake", status=403)

    with testclient.session_transaction() as session:
        session["user_id"] = [u.id]

    u.delete()

    testclient.get("/profile/jake", status=404)
    with testclient.session_transaction() as session:
        assert not session.get("user_id")


def test_impersonate(testclient, logged_admin, user):
    res = testclient.get("/", status=302).follow(status=200).click("Account settings")
    assert "admin" == res.form["user_name"].value

    res = (
        testclient.get("/impersonate/user", status=302)
        .follow(status=302)
        .follow(status=200)
        .click("Account settings")
    )
    assert "user" == res.form["user_name"].value

    testclient.get("/logout", status=302).follow(status=302).follow(status=200)

    res = testclient.get("/", status=302).follow(status=200).click("Account settings")
    assert "admin" == res.form["user_name"].value


def test_wrong_login(testclient, user):
    testclient.app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] = True

    res = testclient.get("/login", status=200)
    res.form["login"] = "invalid"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = "incorrect horse"
    res = res.form.submit(status=200)
    res.mustcontain(no="The login &#39;invalid&#39; does not exist")

    testclient.app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] = False

    res = testclient.get("/login", status=200)
    res.form["login"] = "invalid"
    res = res.form.submit(status=200)
    res.mustcontain("The login &#39;invalid&#39; does not exist")


def test_admin_self_deletion(testclient, backend):
    admin = models.User(
        formatted_name="Temp admin",
        family_name="admin",
        user_name="temp",
        emails=["temp@temp.com"],
        password="admin",
    )
    admin.save()
    with testclient.session_transaction() as sess:
        sess["user_id"] = [admin.id]

    res = testclient.get("/profile/temp/settings")
    res = res.form.submit(name="action", value="confirm-delete")
    res = (
        res.form.submit(name="action", value="delete", status=302)
        .follow(status=302)
        .follow(status=200)
    )

    assert models.User.get_from_login("temp") is None

    with testclient.session_transaction() as sess:
        assert not sess.get("user_id")


def test_user_self_deletion(testclient, backend):
    user = models.User(
        formatted_name="Temp user",
        family_name="user",
        user_name="temp",
        emails=["temp@temp.com"],
        password="correct horse battery staple",
    )
    user.save()
    with testclient.session_transaction() as sess:
        sess["user_id"] = [user.id]

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = ["edit_self"]
    res = testclient.get("/profile/temp/settings")
    res.mustcontain(no="Delete my account")

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = [
        "edit_self",
        "delete_account",
    ]
    # Simulate an app restart
    user.reload()

    res = testclient.get("/profile/temp/settings")
    res.mustcontain("Delete my account")
    res = res.form.submit(name="action", value="confirm-delete")
    res = (
        res.form.submit(name="action", value="delete", status=302)
        .follow(status=302)
        .follow(status=200)
    )

    assert models.User.get_from_login("temp") is None

    with testclient.session_transaction() as sess:
        assert not sess.get("user_id")

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = []


def test_account_locking(user, backend):
    assert not user.locked
    assert not user.lock_date
    assert user.check_password("correct horse battery staple") == (True, None)

    user.lock_date = datetime.datetime.now(datetime.timezone.utc)
    assert user.locked
    user.save()
    assert user.locked
    assert models.User.get(id=user.id).locked
    assert user.check_password("correct horse battery staple") == (
        False,
        "Your account has been locked.",
    )

    user.lock_date = None
    user.save()
    assert not user.locked
    assert not models.User.get(id=user.id).locked
    assert user.check_password("correct horse battery staple") == (True, None)


def test_account_locking_past_date(user, backend):
    assert not user.locked
    assert not user.lock_date
    assert user.check_password("correct horse battery staple") == (True, None)

    user.lock_date = datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0
    ) - datetime.timedelta(days=30)
    user.save()
    assert user.locked
    assert models.User.get(id=user.id).locked
    assert user.check_password("correct horse battery staple") == (
        False,
        "Your account has been locked.",
    )


def test_account_locking_future_date(user, backend):
    assert not user.locked
    assert not user.lock_date
    assert user.check_password("correct horse battery staple") == (True, None)

    user.lock_date = datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0
    ) + datetime.timedelta(days=365 * 4)
    user.save()
    assert not user.locked
    assert not models.User.get(id=user.id).locked
    assert user.check_password("correct horse battery staple") == (True, None)


def test_signin_locked_account(testclient, user):
    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    user.lock_date = datetime.datetime.now(datetime.timezone.utc)
    user.save()

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"

    res = res.form.submit(status=302).follow(status=200)
    res.form["password"] = "correct horse battery staple"

    res = res.form.submit()
    res.mustcontain("Your account has been locked.")

    user.lock_date = None
    user.save()


def test_account_locked_during_session(testclient, logged_user):
    logged_user.lock_date = datetime.datetime.now(datetime.timezone.utc)
    logged_user.save()
    testclient.get("/profile/user/settings", status=403)
