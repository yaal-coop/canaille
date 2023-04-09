from unittest import mock

from canaille.core.models import User


def test_edition(
    testclient,
    slapd_server,
    logged_user,
    admin,
    foo_group,
    bar_group,
):
    res = testclient.get("/profile/user/settings", status=200)
    assert set(res.form["groups"].options) == {
        (foo_group.id, True, "foo"),
        (bar_group.id, False, "bar"),
    }
    assert logged_user.groups == [foo_group]
    assert foo_group.members == [logged_user]
    assert bar_group.members == [admin]
    assert res.form["groups"].attrs["readonly"]
    assert res.form["user_name"].attrs["readonly"]

    res.form["user_name"] = "toto"
    res = res.form.submit(name="action", value="edit")
    assert res.flashes == [("success", "Profile updated successfuly.")]
    res = res.follow()

    logged_user.reload()

    assert logged_user.user_name == ["user"]

    foo_group.reload()
    bar_group.reload()
    assert logged_user.groups == [foo_group]
    assert foo_group.members == [logged_user]
    assert bar_group.members == [admin]

    assert logged_user.check_password("correct horse battery staple")

    logged_user.user_name = ["user"]
    logged_user.save()


def test_profile_settings_edition_dynamic_validation(testclient, logged_admin):
    res = testclient.get(f"/profile/admin/settings")
    res = testclient.post(
        f"/profile/admin/settings",
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
    slapd_server,
    logged_user,
    admin,
):
    res = testclient.get("/profile/user/settings", status=200)
    testclient.app.config["ACL"]["DEFAULT"]["READ"] = []

    res = res.form.submit(name="action", value="edit")
    assert res.flashes == [("success", "Profile updated successfuly.")]
    res = res.follow()

    logged_user.reload()

    assert logged_user.user_name == ["user"]
    assert logged_user.check_password("correct horse battery staple")

    logged_user.user_name = ["user"]
    logged_user.save()


def test_password_change(testclient, logged_user):
    res = testclient.get("/profile/user/settings", status=200)

    res.form["password1"] = "new_password"
    res.form["password2"] = "new_password"

    res = res.form.submit(name="action", value="edit").follow()

    assert logged_user.check_password("new_password")

    res = testclient.get("/profile/user/settings", status=200)

    res.form["password1"] = "correct horse battery staple"
    res.form["password2"] = "correct horse battery staple"

    res = res.form.submit(name="action", value="edit")
    assert ("success", "Profile updated successfuly.") in res.flashes
    res = res.follow()

    assert logged_user.check_password("correct horse battery staple")


def test_password_change_fail(testclient, logged_user):
    res = testclient.get("/profile/user/settings", status=200)

    res.form["password1"] = "new_password"
    res.form["password2"] = "other_password"

    res = res.form.submit(name="action", value="edit", status=200)

    assert logged_user.check_password("correct horse battery staple")

    res = testclient.get("/profile/user/settings", status=200)

    res.form["password1"] = "new_password"
    res.form["password2"] = ""

    res = res.form.submit(name="action", value="edit", status=200)

    assert logged_user.check_password("correct horse battery staple")


def test_password_initialization_mail(
    smtpd, testclient, slapd_connection, logged_admin
):
    u = User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        email="john@doe.com",
    )
    u.save()

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

    u.reload()
    u.password = ["{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz"]
    u.save()

    res = testclient.get("/profile/temp/settings", status=200)
    res.mustcontain(no="This user does not have a password yet")

    u.delete()


@mock.patch("smtplib.SMTP")
def test_password_initialization_mail_send_fail(
    SMTP, smtpd, testclient, slapd_connection, logged_admin
):
    SMTP.side_effect = mock.Mock(side_effect=OSError("unit test mail error"))
    u = User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        email="john@doe.com",
    )
    u.save()

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

    u.delete()


def test_password_initialization_invalid_user(
    smtpd, testclient, slapd_connection, logged_admin
):
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


def test_password_reset_invalid_user(smtpd, testclient, slapd_connection, logged_admin):
    assert len(smtpd.messages) == 0
    res = testclient.get("/profile/admin/settings")
    testclient.post(
        "/profile/invalid/settings",
        {"action": "password-reset-mail", "csrf_token": res.form["csrf_token"].value},
        status=404,
    )
    assert len(smtpd.messages) == 0


def test_delete_invalid_user(testclient, slapd_connection, logged_admin):
    res = testclient.get("/profile/admin/settings")
    testclient.post(
        "/profile/invalid/settings",
        {"action": "delete", "csrf_token": res.form["csrf_token"].value},
        status=404,
    )


def test_impersonate_invalid_user(testclient, slapd_connection, logged_admin):
    testclient.get("/impersonate/invalid", status=404)


def test_invalid_form_request(testclient, logged_admin):
    res = testclient.get("/profile/admin/settings")
    res = res.form.submit(name="action", value="invalid-action", status=400)


def test_password_reset_email(smtpd, testclient, slapd_connection, logged_admin):
    u = User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        email="john@doe.com",
        password="{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz",
    )
    u.save()

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

    u.delete()


@mock.patch("smtplib.SMTP")
def test_password_reset_email_failed(
    SMTP, smtpd, testclient, slapd_connection, logged_admin
):
    SMTP.side_effect = mock.Mock(side_effect=OSError("unit test mail error"))
    u = User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="temp",
        email="john@doe.com",
        password=["{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz"],
    )
    u.save()

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

    u.delete()


def test_admin_bad_request(testclient, logged_admin):
    testclient.post("/profile/admin/settings", {"action": "foobar"}, status=400)
    testclient.get("/profile/foobar/settings", status=404)


def test_edition_permission(
    testclient,
    slapd_server,
    logged_user,
    admin,
):
    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    testclient.get("/profile/user/settings", status=403)

    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = ["edit_self"]
    testclient.get("/profile/user/settings", status=200)
