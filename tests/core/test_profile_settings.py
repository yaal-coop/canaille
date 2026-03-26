import datetime

from flask import g

from canaille.app import models


def test_edition(testclient, logged_user, admin, foo_group, bar_group, backend):
    res = testclient.get("/profile/user/settings", status=200)
    assert (foo_group.id, True, "foo") in res.form["groups"].options
    assert (bar_group.id, False, "bar") in res.form["groups"].options
    assert logged_user.groups == [foo_group]
    assert foo_group.members == [logged_user]
    assert bar_group.members == [admin]
    assert "readonly" in res.form["groups"].attrs
    assert "readonly" in res.form["user_name"].attrs

    res.form["user_name"] = "toto"
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [
        (
            "error",
            "Your changes couldn't be saved. Please check the form and try again.",
        )
    ]
    backend.reload(logged_user)

    assert logged_user.user_name == "user"

    backend.reload(foo_group)
    backend.reload(bar_group)
    assert logged_user.groups == [foo_group]
    assert foo_group.members == [logged_user]
    assert bar_group.members == [admin]
    assert "readonly" in res.form["groups"].attrs
    assert "readonly" in res.form["user_name"].attrs


def test_group_removal(testclient, logged_admin, user, foo_group, backend):
    """Tests that one can remove a group from a user."""
    foo_group.members = [user, logged_admin]
    backend.save(foo_group)
    backend.reload(user)
    assert foo_group in user.groups

    res = testclient.get("/profile/user/settings", status=200)
    res.form["groups"] = []
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("success", "Profile updated successfully.")]

    backend.reload(user)
    assert foo_group not in user.groups

    backend.reload(foo_group)
    backend.reload(logged_admin)
    assert foo_group.members == [logged_admin]


def test_empty_group_removal(testclient, logged_admin, user, foo_group, backend):
    """Tests that one cannot remove a group from a user, when was the last person in the group.

    This is because LDAP groups cannot be empty because
    groupOfNames.member is a MUST attribute.
    https://www.rfc-editor.org/rfc/rfc2256.html#section-7.10
    """
    assert foo_group in user.groups

    res = testclient.get("/profile/user/settings", status=200)
    res.form["groups"] = []
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [
        (
            "error",
            "Your changes couldn't be saved. Please check the form and try again.",
        )
    ]

    res.mustcontain(
        "The group 'foo' cannot be removed, because it must have at least one user left."
    )

    backend.reload(user)
    assert foo_group in user.groups


def test_edition_without_groups(
    testclient,
    logged_user,
    admin,
    backend,
):
    res = testclient.get("/profile/user/settings", status=200)
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["READ"] = []

    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("success", "Profile updated successfully.")]
    res = res.follow()

    backend.reload(logged_user)

    assert logged_user.user_name == "user"
    assert backend.check_user_password(logged_user, "correct horse battery staple")[0]

    logged_user.user_name = "user"
    backend.save(logged_user)


def test_delete_invalid_user(testclient, backend, logged_admin):
    res = testclient.get("/profile/admin/settings")
    testclient.post(
        "/profile/invalid/settings",
        {"action": "delete", "csrf_token": res.form["csrf_token"].value},
        status=404,
    )


def test_impersonate_invalid_user(testclient, backend, logged_admin):
    testclient.get("/impersonate/invalid", status=404)


def test_impersonate_locked_user(testclient, backend, logged_admin, user):
    res = testclient.get("/profile/user/settings")
    res.mustcontain("Impersonate")

    user.lock_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=1
    )
    backend.save(user)

    assert user.locked
    res = testclient.get("/profile/user/settings")
    res.mustcontain(no="Impersonate")

    res = testclient.get("/impersonate/user", status=403)
    res.mustcontain("Locked users cannot be impersonated.")


def test_invalid_form_request(testclient, logged_admin):
    res = testclient.get("/profile/admin/settings")
    res = res.form.submit(name="action", value="invalid-action", status=400)


def test_admin_bad_request(testclient, logged_admin):
    res = testclient.get("/profile/admin/settings")
    testclient.post(
        "/profile/admin/settings",
        {"action": "foobar", "csrf_token": res.form["csrf_token"].value},
        status=400,
    )
    testclient.get("/profile/foobar/settings", status=404)


def test_edition_permission(
    testclient,
    logged_user,
    admin,
    backend,
):
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    backend.reload(logged_user)
    testclient.get("/profile/user/settings", status=404)

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = ["edit_self"]
    backend.reload(g.session.user)
    testclient.get("/profile/user/settings", status=200)


def test_account_locking(
    testclient,
    backend,
    logged_admin,
    user,
):
    res = testclient.get("/profile/user/settings")
    assert not user.lock_date
    assert not user.locked
    res.mustcontain("Lock the account")
    res.mustcontain(no="Unlock")

    res = res.form.submit(name="action", value="lock-confirm")
    res = res.form.submit(name="action", value="lock-execute")
    user = backend.get(models.User, id=user.id)
    assert user.lock_date <= datetime.datetime.now(datetime.timezone.utc)
    assert user.locked
    res.mustcontain("The account has been locked.")
    res.mustcontain(no="Lock the account")
    res.mustcontain("Unlock")

    res = res.form.submit(name="action", value="unlock")
    user = backend.get(models.User, id=user.id)
    assert not user.lock_date
    assert not user.locked
    res.mustcontain("The account has been unlocked.")
    res.mustcontain("Lock the account")
    res.mustcontain(no="Unlock")


def test_past_lock_date(
    testclient,
    backend,
    logged_admin,
    user,
):
    res = testclient.get("/profile/user/settings", status=200)
    assert not user.lock_date
    assert not user.locked

    expiration_datetime = datetime.datetime.now(datetime.timezone.utc).replace(
        second=0, microsecond=0
    ) - datetime.timedelta(days=30)
    res.form["lock_date"] = expiration_datetime.strftime("%Y-%m-%d %H:%M")
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("success", "Profile updated successfully.")]

    res = res.follow()
    user = backend.get(models.User, id=user.id)
    assert user.lock_date == expiration_datetime
    assert user.locked


def test_future_lock_date(
    testclient,
    backend,
    logged_admin,
    user,
):
    res = testclient.get("/profile/user/settings", status=200)
    assert not user.lock_date
    assert not user.locked

    expiration_datetime = datetime.datetime.now(datetime.timezone.utc).replace(
        second=0, microsecond=0
    ) + datetime.timedelta(days=30)
    res.form["lock_date"] = expiration_datetime.strftime("%Y-%m-%d %H:%M")
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("success", "Profile updated successfully.")]

    res = res.follow()
    user = backend.get(models.User, id=user.id)
    assert user.lock_date == expiration_datetime
    assert not user.locked
    assert res.form["lock_date"].value == expiration_datetime.strftime("%Y-%m-%d %H:%M")


def test_empty_lock_date(
    testclient,
    backend,
    logged_admin,
    user,
):
    expiration_datetime = datetime.datetime.now(datetime.timezone.utc).replace(
        second=0, microsecond=0
    ) + datetime.timedelta(days=30)
    user.lock_date = expiration_datetime
    backend.save(user)

    res = testclient.get("/profile/user/settings", status=200)
    res.form["lock_date"] = ""
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("success", "Profile updated successfully.")]

    res = res.follow()
    backend.reload(user)
    assert not user.lock_date


def test_account_limit_values(
    testclient,
    backend,
    logged_admin,
    user,
):
    res = testclient.get("/profile/user/settings", status=200)
    assert not user.lock_date
    assert not user.locked

    expiration_datetime = datetime.datetime.max.replace(
        microsecond=0, tzinfo=datetime.timezone.utc
    )
    res.form["lock_date"] = expiration_datetime.strftime("%Y-%m-%d %H:%M:%S")
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("success", "Profile updated successfully.")]

    res = res.follow()
    user = backend.get(models.User, id=user.id)
    assert user.lock_date == expiration_datetime
    assert not user.locked


def test_edition_invalid_group(testclient, logged_admin, user, foo_group):
    res = testclient.get("/profile/user/settings", status=200)
    res.form["groups"].force_value("invalid")
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [
        (
            "error",
            "Your changes couldn't be saved. Please check the form and try again.",
        )
    ]
    res.mustcontain("Invalid choice(s): one or more data inputs could not be coerced.")
