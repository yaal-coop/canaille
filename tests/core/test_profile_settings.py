import datetime
from unittest import mock

from flask import g

from canaille.app import models


def test_edition(testclient, logged_user, admin, foo_group, bar_group, backend):
    res = testclient.get("/profile/user/settings", status=200)
    assert set(res.form["groups"].options) == {
        (foo_group.id, True, "foo"),
        (bar_group.id, False, "bar"),
    }
    assert logged_user.groups == [foo_group]
    assert foo_group.members == [logged_user]
    assert bar_group.members == [admin]
    assert "readonly" in res.form["groups"].attrs
    assert "readonly" in res.form["user_name"].attrs

    res.form["user_name"] = "toto"
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("error", "Profile edition failed.")]
    logged_user.reload()

    assert logged_user.user_name == "user"

    foo_group.reload()
    bar_group.reload()
    assert logged_user.groups == [foo_group]
    assert foo_group.members == [logged_user]
    assert bar_group.members == [admin]

    assert backend.check_user_password(logged_user, "correct horse battery staple")[0]

    logged_user.user_name = "user"
    backend.save(logged_user)


def test_group_removal(testclient, logged_admin, user, foo_group, backend):
    """Tests that one can remove a group from a user."""
    foo_group.members = [user, logged_admin]
    backend.save(foo_group)
    user.reload()
    assert foo_group in user.groups

    res = testclient.get("/profile/user/settings", status=200)
    res.form["groups"] = []
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("success", "Profile updated successfully.")]

    user.reload()
    assert foo_group not in user.groups

    foo_group.reload()
    logged_admin.reload()
    assert foo_group.members == [logged_admin]


def test_empty_group_removal(testclient, logged_admin, user, foo_group, backend):
    """Tests that one cannot remove a group from a user, when was the last
    person in the group.

    This is because LDAP groups cannot be empty because
    groupOfNames.member is a MUST attribute.
    https://www.rfc-editor.org/rfc/rfc2256.html#section-7.10
    """
    assert foo_group in user.groups

    res = testclient.get("/profile/user/settings", status=200)
    res.form["groups"] = []
    res = res.form.submit(name="action", value="edit-settings")
    assert res.flashes == [("error", "Profile edition failed.")]

    res.mustcontain(
        "The group &#39;foo&#39; cannot be removed, because it must have at least one user left."
    )

    user.reload()
    assert foo_group in user.groups


def test_profile_settings_edition_dynamic_validation(testclient, logged_admin):
    res = testclient.get("/profile/admin/settings")
    res = testclient.post(
        "/profile/admin/settings",
        {
            "csrf_token": res.form["csrf_token"].value,
            "password1": "short",
        },
        headers={
            "HX-Request": "true",
            "HX-Trigger-Name": "password1",
        },
    )
    res.mustcontain("Field must be at least 8 characters long.")


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

    logged_user.reload()

    assert logged_user.user_name == "user"
    assert backend.check_user_password(logged_user, "correct horse battery staple")[0]

    logged_user.user_name = "user"
    backend.save(logged_user)


def test_password_change(testclient, logged_user, backend):
    res = testclient.get("/profile/user/settings", status=200)

    res.form["password1"] = "new_password"
    res.form["password2"] = "new_password"

    res = res.form.submit(name="action", value="edit-settings").follow()

    logged_user.reload()
    assert backend.check_user_password(logged_user, "new_password")[0]

    res = testclient.get("/profile/user/settings", status=200)

    res.form["password1"] = "correct horse battery staple"
    res.form["password2"] = "correct horse battery staple"

    res = res.form.submit(name="action", value="edit-settings")
    assert ("success", "Profile updated successfully.") in res.flashes
    res = res.follow()

    logged_user.reload()
    assert backend.check_user_password(logged_user, "correct horse battery staple")[0]


def test_password_change_fail(testclient, logged_user, backend):
    res = testclient.get("/profile/user/settings", status=200)

    res.form["password1"] = "new_password"
    res.form["password2"] = "other_password"

    res = res.form.submit(name="action", value="edit-settings", status=200)

    logged_user.reload()
    assert backend.check_user_password(logged_user, "correct horse battery staple")[0]

    res = testclient.get("/profile/user/settings", status=200)

    res.form["password1"] = "new_password"
    res.form["password2"] = ""

    res = res.form.submit(name="action", value="edit-settings", status=200)

    logged_user.reload()
    assert backend.check_user_password(logged_user, "correct horse battery staple")[0]


def test_password_initialization_mail(smtpd, testclient, backend, logged_admin):
    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.com"],
    )
    backend.save(u)

    res = testclient.get("/profile/temp/settings", status=200)
    res.mustcontain("This user does not have a password yet")
    res.mustcontain("Send")

    res = res.form.submit(name="action", value="password-initialization-mail")
    assert (
        "success",
        "A password initialization link has been sent at the user email address. "
        "It should be received within a few minutes.",
    ) in res.flashes
    assert len(smtpd.messages) == 1
    assert smtpd.messages[0]["X-RcptTo"] == "john@doe.com"

    u.reload()
    u.password = "correct horse battery staple"
    backend.save(u)

    res = testclient.get("/profile/temp/settings", status=200)
    res.mustcontain(no="This user does not have a password yet")

    backend.delete(u)


@mock.patch("smtplib.SMTP")
def test_password_initialization_mail_send_fail(
    SMTP, smtpd, testclient, backend, logged_admin
):
    SMTP.side_effect = mock.Mock(side_effect=OSError("unit test mail error"))
    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.com"],
    )
    backend.save(u)

    res = testclient.get("/profile/temp/settings", status=200)
    res.mustcontain("This user does not have a password yet")
    res.mustcontain("Send")

    res = res.form.submit(
        name="action", value="password-initialization-mail", expect_errors=True
    )
    assert (
        "success",
        "A password initialization link has been sent at the user email address. "
        "It should be received within a few minutes.",
    ) not in res.flashes
    assert ("error", "Could not send the password initialization email") in res.flashes
    assert len(smtpd.messages) == 0

    backend.delete(u)


def test_password_initialization_invalid_user(smtpd, testclient, backend, logged_admin):
    assert len(smtpd.messages) == 0
    res = testclient.get("/profile/admin/settings")
    testclient.post(
        "/profile/invalid/settings",
        {
            "action": "password-initialization-mail",
            "csrf_token": res.form["csrf_token"].value,
        },
        status=404,
    )
    assert len(smtpd.messages) == 0


def test_password_reset_invalid_user(smtpd, testclient, backend, logged_admin):
    assert len(smtpd.messages) == 0
    res = testclient.get("/profile/admin/settings")
    testclient.post(
        "/profile/invalid/settings",
        {"action": "password-reset-mail", "csrf_token": res.form["csrf_token"].value},
        status=404,
    )
    assert len(smtpd.messages) == 0


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


def test_password_reset_email(smtpd, testclient, backend, logged_admin):
    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.com"],
        password="correct horse battery staple",
    )
    backend.save(u)

    res = testclient.get("/profile/temp/settings", status=200)
    res.mustcontain("If the user has forgotten his password")
    res.mustcontain("Send")

    res = res.form.submit(name="action", value="password-reset-mail")
    assert (
        "success",
        "A password reset link has been sent at the user email address. "
        "It should be received within a few minutes.",
    ) in res.flashes
    assert len(smtpd.messages) == 1
    assert smtpd.messages[0]["X-RcptTo"] == "john@doe.com"

    backend.delete(u)


@mock.patch("smtplib.SMTP")
def test_password_reset_email_failed(SMTP, smtpd, testclient, backend, logged_admin):
    SMTP.side_effect = mock.Mock(side_effect=OSError("unit test mail error"))
    u = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        emails=["john@doe.com"],
        password="correct horse battery staple",
    )
    backend.save(u)

    res = testclient.get("/profile/temp/settings", status=200)
    res.mustcontain("If the user has forgotten his password")
    res.mustcontain("Send")

    res = res.form.submit(
        name="action", value="password-reset-mail", expect_errors=True
    )
    assert (
        "success",
        "A password reset link has been sent at the user email address. "
        "It should be received within a few minutes.",
    ) not in res.flashes
    assert ("error", "Could not send the password reset email") in res.flashes
    assert len(smtpd.messages) == 0

    backend.delete(u)


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
):
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    logged_user.reload()
    testclient.get("/profile/user/settings", status=404)

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = ["edit_self"]
    g.user.reload()
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

    res = res.form.submit(name="action", value="confirm-lock")
    res = res.form.submit(name="action", value="lock")
    user = backend.get(models.User, id=user.id)
    assert user.lock_date <= datetime.datetime.now(datetime.timezone.utc)
    assert user.locked
    res.mustcontain("The account has been locked")
    res.mustcontain(no="Lock the account")
    res.mustcontain("Unlock")

    res = res.form.submit(name="action", value="unlock")
    user = backend.get(models.User, id=user.id)
    assert not user.lock_date
    assert not user.locked
    res.mustcontain("The account has been unlocked")
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
    user.reload()
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
    assert res.flashes == [("error", "Profile edition failed.")]
    res.mustcontain("Invalid choice(s): one or more data inputs could not be coerced.")
