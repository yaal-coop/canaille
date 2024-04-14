import datetime

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

    assert backend.get(models.User, user_name="temp") is None

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

    assert backend.get(models.User, user_name="temp") is None

    with testclient.session_transaction() as sess:
        assert not sess.get("user_id")

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = []


def test_account_locking(user, backend):
    assert not user.locked
    assert not user.lock_date
    assert backend.check_user_password(user, "correct horse battery staple") == (
        True,
        None,
    )

    user.lock_date = datetime.datetime.now(datetime.timezone.utc)
    assert user.locked
    user.save()
    assert user.locked
    assert backend.get(models.User, id=user.id).locked
    assert backend.check_user_password(user, "correct horse battery staple") == (
        False,
        "Your account has been locked.",
    )

    user.lock_date = None
    user.save()
    assert not user.locked
    assert not backend.get(models.User, id=user.id).locked
    assert backend.check_user_password(user, "correct horse battery staple") == (
        True,
        None,
    )


def test_account_locking_past_date(user, backend):
    assert not user.locked
    assert not user.lock_date
    assert backend.check_user_password(user, "correct horse battery staple") == (
        True,
        None,
    )

    user.lock_date = datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0
    ) - datetime.timedelta(days=30)
    user.save()
    assert user.locked
    assert backend.get(models.User, id=user.id).locked
    assert backend.check_user_password(user, "correct horse battery staple") == (
        False,
        "Your account has been locked.",
    )


def test_account_locking_future_date(user, backend):
    assert not user.locked
    assert not user.lock_date
    assert backend.check_user_password(user, "correct horse battery staple") == (
        True,
        None,
    )

    user.lock_date = datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0
    ) + datetime.timedelta(days=365 * 4)
    user.save()
    assert not user.locked
    assert not backend.get(models.User, id=user.id).locked
    assert backend.check_user_password(user, "correct horse battery staple") == (
        True,
        None,
    )


def test_account_locked_during_session(testclient, logged_user):
    logged_user.lock_date = datetime.datetime.now(datetime.timezone.utc)
    logged_user.save()
    testclient.get("/profile/user/settings", status=403)
