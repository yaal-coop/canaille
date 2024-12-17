import datetime
from unittest import mock

import pytest
import time_machine
from flask import g

from canaille.app import models


def test_index(testclient, user, backend):
    res = testclient.get("/", status=302)
    assert res.location == "/login"

    g.user = user
    res = testclient.get("/", status=302)
    assert res.location == "/profile/user"

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    backend.reload(g.user)
    res = testclient.get("/", status=302)
    assert res.location == "/about"


def test_user_deleted_in_session(testclient, backend):
    u = models.User(
        formatted_name="Jake Doe",
        family_name="Jake",
        user_name="jake",
        emails=["jake@doe.test"],
        password="correct horse battery staple",
    )
    backend.save(u)
    testclient.get("/profile/jake", status=403)

    with testclient.session_transaction() as session:
        session["user_id"] = [u.id]

    backend.delete(u)

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
        emails=["temp@temp.test"],
        password="admin",
    )
    backend.save(admin)
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
        emails=["temp@temp.test"],
        password="correct horse battery staple",
    )
    backend.save(user)
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
    backend.reload(user)

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
    backend.save(user)
    assert user.locked
    assert backend.get(models.User, id=user.id).locked
    assert backend.check_user_password(user, "correct horse battery staple") == (
        False,
        "Your account has been locked.",
    )

    user.lock_date = None
    backend.save(user)
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
    backend.save(user)
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
    backend.save(user)
    assert not user.locked
    assert not backend.get(models.User, id=user.id).locked
    assert backend.check_user_password(user, "correct horse battery staple") == (
        True,
        None,
    )


def test_account_locked_during_session(testclient, logged_user, backend):
    logged_user.lock_date = datetime.datetime.now(datetime.timezone.utc)
    backend.save(logged_user)
    testclient.get("/profile/user/settings", status=403)


def test_expired_password_redirection_and_register_new_password_for_memory_and_sql(
    testclient,
    logged_user,
    user,
    backend,
    admin,
):
    """time_machine does not work with ldap."""
    if "ldap" in backend.__class__.__module__:
        pytest.skip()

    testclient.app.config["WTF_CSRF_ENABLED"] = False
    backend.reload(logged_user)
    res = testclient.get("/profile/user/settings", status=200)
    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"

    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False) as traveller:
        res = res.form.submit(name="action", value="edit-settings")

        testclient.app.config["CANAILLE"]["PASSWORD_LIFETIME"] = "P5D"

        traveller.shift(datetime.timedelta(days=5, minutes=1))

        backend.reload(g.user)

        res = testclient.get("/profile/user/settings")

        testclient.get("/reset/admin", status=403)

        assert (
            "info",
            "Your password has expired, please choose a new password.",
        ) in res.flashes
        assert res.location == "/reset/user"

        backend.reload(logged_user)
        res = testclient.get("/reset/user")

        res.form["password"] = "foobarbaz"
        res.form["confirmation"] = "foobarbaz"
        res = res.form.submit()
        assert ("success", "Your password has been updated successfully") in res.flashes


@mock.patch("canaille.core.models.User.has_expired_password")
def test_expired_password_redirection_and_register_new_password_for_ldap_sql_and_memory(
    has_expired,
    testclient,
    logged_user,
    user,
    backend,
    admin,
):
    """time_machine does not work with ldap."""
    has_expired.return_value = False
    assert user.password_last_update is None
    res = testclient.get("/profile/user/settings", status=200)
    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"
    res = res.form.submit(name="action", value="edit-settings")
    backend.reload(logged_user)
    assert user.password_last_update is not None

    has_expired.return_value = True
    res = testclient.get("/profile/user/settings")
    testclient.get("/reset/admin", status=403)
    assert (
        "info",
        "Your password has expired, please choose a new password.",
    ) in res.flashes
    assert res.location == "/reset/user"
    backend.reload(logged_user)
    backend.reload(g.user)
    backend.reload(user)

    res = testclient.get("/reset/user")

    res.form["password"] = "foobarbaz"
    res.form["confirmation"] = "foobarbaz"
    res = res.form.submit()
    assert ("success", "Your password has been updated successfully") in res.flashes


def test_not_expired_password_or_wrong_user_redirection(
    testclient, logged_user, user, backend, admin
):
    assert user.password_last_update is None
    res = testclient.get("/profile/user/settings", status=200)
    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"
    res = res.form.submit(name="action", value="edit-settings")
    backend.reload(logged_user)
    assert user.password_last_update is not None

    def test_two_redirections(password_lifetime):
        testclient.app.config["CANAILLE"]["PASSWORD_LIFETIME"] = password_lifetime
        testclient.get("/reset/user", status=403)
        testclient.get("/reset/admin", status=403)

    test_two_redirections(None)

    testclient.app.config["CANAILLE"]["PASSWORD_LIFETIME"] = "PT0S"
    res = testclient.get("/profile/user/settings")
    assert (
        "info",
        "Your password has expired, please choose a new password.",
    ) in res.flashes
    assert res.location == "/reset/user"

    testclient.app.config["CANAILLE"]["PASSWORD_LIFETIME"] = "P1D"
    res = testclient.get("/profile/user/settings")
    res.form["password1"] = "123456789"
    res.form["password2"] = "123456789"
    res = res.form.submit(name="action", value="edit-settings")

    test_two_redirections("P1D")


def test_expired_password_needed_without_current_user(testclient, user):
    testclient.get("/reset/user", status=403)
