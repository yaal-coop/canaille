from unittest import mock

from canaille.models import User
from canaille.populate import fake_users
from webtest import Upload


def test_user_list_pagination(testclient, logged_admin):
    res = testclient.get("/users")
    res.mustcontain("1 items")

    users = fake_users(25)

    res = testclient.get("/users")
    res.mustcontain("26 items")
    user_name = res.pyquery(".users tbody tr:nth-of-type(1) td:nth-of-type(2) a").text()
    assert user_name

    form = res.forms["next"]
    form["page"] = 2
    res = form.submit()
    assert user_name not in res.pyquery(
        ".users tbody tr td:nth-of-type(2) a"
    ).text().split(" ")
    for user in users:
        user.delete()

    res = testclient.get("/users")
    res.mustcontain("1 items")


def test_user_list_bad_pages(testclient, logged_admin):
    res = testclient.get("/users")
    form = res.forms["next"]
    testclient.post(
        "/users", {"csrf_token": form["csrf_token"], "page": "2"}, status=404
    )

    res = testclient.get("/users")
    form = res.forms["next"]
    testclient.post(
        "/users", {"csrf_token": form["csrf_token"], "page": "-1"}, status=404
    )


def test_user_list_search(testclient, logged_admin, user, moderator):
    res = testclient.get("/users")
    res.mustcontain("3 items")
    res.mustcontain(moderator.name)
    res.mustcontain(user.name)

    form = res.forms["search"]
    form["query"] = "Jack"
    res = form.submit()

    res.mustcontain("1 items")
    res.mustcontain(moderator.name)
    res.mustcontain(no=user.name)


def test_user_list_search_only_allowed_fields(
    testclient, logged_admin, user, moderator
):
    res = testclient.get("/users")
    res.mustcontain("3 items")
    res.mustcontain(moderator.name)
    res.mustcontain(user.name)

    form = res.forms["search"]
    form["query"] = "user"
    res = form.submit()

    res.mustcontain("1 items")
    res.mustcontain(user.name)
    res.mustcontain(no=moderator.name)

    testclient.app.config["ACL"]["DEFAULT"]["READ"].remove("uid")

    form = res.forms["search"]
    form["query"] = "user"
    res = form.submit()

    res.mustcontain("0 items")
    res.mustcontain(no=user.name)
    res.mustcontain(no=moderator.name)


def test_edition_permission(
    testclient,
    slapd_server,
    logged_user,
    admin,
    foo_group,
    bar_group,
    jpeg_photo,
):
    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    testclient.get("/profile/user", status=403)

    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = ["edit_self"]
    testclient.get("/profile/user", status=200)


def test_edition(
    testclient,
    slapd_server,
    logged_user,
    admin,
    foo_group,
    bar_group,
    jpeg_photo,
):
    res = testclient.get("/profile/user", status=200)
    assert set(res.form["groups"].options) == {
        ("cn=foo,ou=groups,dc=mydomain,dc=tld", True, "foo"),
        ("cn=bar,ou=groups,dc=mydomain,dc=tld", False, "bar"),
    }
    assert logged_user.groups == [foo_group]
    assert foo_group.members == [logged_user]
    assert bar_group.members == [admin]
    assert res.form["groups"].attrs["readonly"]
    assert res.form["uid"].attrs["readonly"]

    res.form["uid"] = "toto"
    res.form["givenName"] = "given_name"
    res.form["sn"] = "family_name"
    res.form["displayName"] = "display_name"
    res.form["mail"] = "email@mydomain.tld"
    res.form["telephoneNumber"] = "555-666-777"
    res.form["postalAddress"] = "postal_address"
    res.form["street"] = "street"
    res.form["postalCode"] = "postal_code"
    res.form["l"] = "locality"
    res.form["st"] = "region"
    res.form["employeeNumber"] = 666
    res.form["departmentNumber"] = 1337
    res.form["title"] = "title"
    res.form["groups"] = [
        "cn=foo,ou=groups,dc=mydomain,dc=tld",
        "cn=bar,ou=groups,dc=mydomain,dc=tld",
    ]
    res.form["preferredLanguage"] = "fr"
    res.form["jpegPhoto"] = Upload("logo.jpg", jpeg_photo)
    res = res.form.submit(name="action", value="edit")
    assert res.flashes == [("success", "Le profil a été mis à jour avec succès.")]
    res = res.follow()

    logged_user = User.get(id=logged_user.id)
    logged_user.load_groups()

    assert logged_user.uid == ["user"]
    assert logged_user.givenName == ["given_name"]
    assert logged_user.sn == ["family_name"]
    assert logged_user.displayName == "display_name"
    assert logged_user.mail == ["email@mydomain.tld"]
    assert logged_user.telephoneNumber == ["555-666-777"]
    assert logged_user.postalAddress == ["postal_address"]
    assert logged_user.street == ["street"]
    assert logged_user.postalCode == ["postal_code"]
    assert logged_user.l == ["locality"]
    assert logged_user.st == ["region"]
    assert logged_user.preferredLanguage == "fr"
    assert logged_user.employeeNumber == "666"
    assert logged_user.departmentNumber == ["1337"]
    assert logged_user.title == ["title"]
    assert logged_user.jpegPhoto == [jpeg_photo]

    foo_group.reload()
    bar_group.reload()
    assert logged_user.groups == [foo_group]
    assert foo_group.members == [logged_user]
    assert bar_group.members == [admin]

    assert logged_user.check_password("correct horse battery staple")

    logged_user.uid = ["user"]
    logged_user.cn = ["John (johnny) Doe"]
    logged_user.sn = ["Doe"]
    logged_user.mail = ["john@doe.com"]
    logged_user.givenName = None
    logged_user.jpegPhoto = None
    logged_user.save()


def test_field_permissions_none(testclient, slapd_server, logged_user):
    testclient.get("/profile/user", status=200)
    logged_user.telephoneNumber = ["555-666-777"]
    logged_user.save()

    testclient.app.config["ACL"]["DEFAULT"] = {
        "READ": ["uid"],
        "WRITE": [],
        "PERMISSIONS": ["edit_self"],
    }

    res = testclient.get("/profile/user", status=200)
    assert "telephoneNumber" not in res.form.fields

    testclient.post(
        "/profile/user", {"action": "edit", "telephoneNumber": "000-000-000"}
    )
    user = User.get(id=logged_user.id)
    assert user.telephoneNumber == ["555-666-777"]


def test_field_permissions_read(testclient, slapd_server, logged_user):
    testclient.get("/profile/user", status=200)
    logged_user.telephoneNumber = ["555-666-777"]
    logged_user.save()

    testclient.app.config["ACL"]["DEFAULT"] = {
        "READ": ["uid", "telephoneNumber"],
        "WRITE": [],
        "PERMISSIONS": ["edit_self"],
    }
    res = testclient.get("/profile/user", status=200)
    assert "telephoneNumber" in res.form.fields

    testclient.post(
        "/profile/user", {"action": "edit", "telephoneNumber": "000-000-000"}
    )
    user = User.get(id=logged_user.id)
    assert user.telephoneNumber == ["555-666-777"]


def test_field_permissions_write(testclient, slapd_server, logged_user):
    testclient.get("/profile/user", status=200)
    logged_user.telephoneNumber = ["555-666-777"]
    logged_user.save()

    testclient.app.config["ACL"]["DEFAULT"] = {
        "READ": ["uid"],
        "WRITE": ["telephoneNumber"],
        "PERMISSIONS": ["edit_self"],
    }
    res = testclient.get("/profile/user", status=200)
    assert "telephoneNumber" in res.form.fields

    testclient.post(
        "/profile/user", {"action": "edit", "telephoneNumber": "000-000-000"}
    )
    user = User.get(id=logged_user.id)
    assert user.telephoneNumber == ["000-000-000"]


def test_simple_user_cannot_edit_other(testclient, logged_user):
    testclient.get("/profile/user", status=200)
    testclient.get("/profile/admin", status=403)
    testclient.post("/profile/admin", {"action": "edit"}, status=403)
    testclient.post("/profile/admin", {"action": "delete"}, status=403)
    testclient.get("/users", status=403)


def test_bad_email(testclient, logged_user):
    res = testclient.get("/profile/user", status=200)

    res.form["mail"] = "john@doe.com"

    res = res.form.submit(name="action", value="edit").follow()

    assert ["john@doe.com"] == logged_user.mail

    res = testclient.get("/profile/user", status=200)

    res.form["mail"] = "yolo"

    res = res.form.submit(name="action", value="edit", status=200)

    logged_user.reload()

    assert ["john@doe.com"] == logged_user.mail


def test_surname_is_mandatory(testclient, logged_user):
    res = testclient.get("/profile/user", status=200)
    logged_user.sn = ["Doe"]

    res.form["sn"] = ""

    res = res.form.submit(name="action", value="edit", status=200)

    logged_user.reload()

    assert ["Doe"] == logged_user.sn


def test_password_change(testclient, logged_user):
    res = testclient.get("/profile/user", status=200)

    res.form["password1"] = "new_password"
    res.form["password2"] = "new_password"

    res = res.form.submit(name="action", value="edit").follow()

    assert logged_user.check_password("new_password")

    res = testclient.get("/profile/user", status=200)

    res.form["password1"] = "correct horse battery staple"
    res.form["password2"] = "correct horse battery staple"

    res = res.form.submit(name="action", value="edit")
    assert ("success", "Profile updated successfuly.") in res.flashes
    res = res.follow()

    assert logged_user.check_password("correct horse battery staple")


def test_password_change_fail(testclient, logged_user):
    res = testclient.get("/profile/user", status=200)

    res.form["password1"] = "new_password"
    res.form["password2"] = "other_password"

    res = res.form.submit(name="action", value="edit", status=200)

    assert logged_user.check_password("correct horse battery staple")

    res = testclient.get("/profile/user", status=200)

    res.form["password1"] = "new_password"
    res.form["password2"] = ""

    res = res.form.submit(name="action", value="edit", status=200)

    assert logged_user.check_password("correct horse battery staple")


def test_admin_bad_request(testclient, logged_moderator):
    testclient.post("/profile/admin", {"action": "foobar"}, status=400)
    testclient.get("/profile/foobar", status=404)


def test_user_creation_edition_and_deletion(
    testclient, logged_moderator, foo_group, bar_group
):
    # The user does not exist.
    res = testclient.get("/users", status=200)
    assert User.get("george") is None
    res.mustcontain(no="george")

    # Fill the profile for a new user.
    res = testclient.get("/profile", status=200)
    res.form["uid"] = "george"
    res.form["givenName"] = "George"
    res.form["sn"] = "Abitbol"
    res.form["mail"] = "george@abitbol.com"
    res.form["telephoneNumber"] = "555-666-888"
    res.form["groups"] = ["cn=foo,ou=groups,dc=mydomain,dc=tld"]
    res.form["password1"] = "totoyolo"
    res.form["password2"] = "totoyolo"

    # User have been created
    res = res.form.submit(name="action", value="edit", status=302)
    assert ("success", "User account creation succeed.") in res.flashes
    res = res.follow(status=200)
    george = User.get("george")
    george.load_groups()
    foo_group.reload()
    assert "George" == george.givenName[0]
    assert george.groups == [foo_group]
    assert george.check_password("totoyolo")

    assert "george" in testclient.get("/users", status=200).text
    assert "readonly" not in res.form["groups"].attrs

    res.form["givenName"] = "Georgio"
    res.form["groups"] = [
        "cn=foo,ou=groups,dc=mydomain,dc=tld",
        "cn=bar,ou=groups,dc=mydomain,dc=tld",
    ]

    # User have been edited
    res = res.form.submit(name="action", value="edit").follow()
    george = User.get("george")
    george.load_groups()
    assert "Georgio" == george.givenName[0]
    assert george.check_password("totoyolo")

    foo_group.reload()
    bar_group.reload()
    assert george in set(foo_group.members)
    assert george in set(bar_group.members)
    assert set(george.groups) == {foo_group, bar_group}
    assert "george" in testclient.get("/users", status=200).text
    assert "george" in testclient.get("/users", status=200).text

    # User have been deleted.
    res = res.form.submit(name="action", value="delete", status=302).follow(status=200)
    assert User.get("george") is None
    res.mustcontain(no="george")


def test_user_creation_without_password(testclient, logged_moderator):
    res = testclient.get("/profile", status=200)
    res.form["uid"] = "george"
    res.form["sn"] = "Abitbol"
    res.form["mail"] = "george@abitbol.com"

    res = res.form.submit(name="action", value="edit", status=302)
    assert ("success", "User account creation succeed.") in res.flashes
    res = res.follow(status=200)
    george = User.get("george")
    assert george.uid[0] == "george"
    assert not george.userPassword

    george.delete()


def test_user_creation_form_validation_failed(
    testclient, logged_moderator, foo_group, bar_group
):
    res = testclient.get("/users", status=200)
    assert User.get("george") is None
    res.mustcontain(no="george")

    res = testclient.get("/profile", status=200)
    res = res.form.submit(name="action", value="edit")
    assert ("error", "User account creation failed.") in res.flashes
    assert User.get("george") is None


def test_cn_setting_with_given_name_and_surname(testclient, logged_moderator):
    res = testclient.get("/profile", status=200)
    res.form["uid"] = "george"
    res.form["givenName"] = "George"
    res.form["sn"] = "Abitbol"
    res.form["mail"] = "george@abitbol.com"

    res = res.form.submit(name="action", value="edit", status=302).follow(status=200)

    george = User.get("george")
    assert george.cn[0] == "George Abitbol"
    george.delete()


def test_cn_setting_with_surname_only(testclient, logged_moderator):
    res = testclient.get("/profile", status=200)
    res.form["uid"] = "george"
    res.form["sn"] = "Abitbol"
    res.form["mail"] = "george@abitbol.com"

    res = res.form.submit(name="action", value="edit", status=302).follow(status=200)

    george = User.get("george")
    assert george.cn[0] == "Abitbol"
    george.delete()


def test_password_initialization_mail(
    smtpd, testclient, slapd_connection, logged_admin
):
    u = User(
        cn="Temp User",
        sn="Temp",
        uid="temp",
        mail="john@doe.com",
    )
    u.save()

    res = testclient.get("/profile/temp", status=200)
    res.mustcontain("This user does not have a password yet")
    res.mustcontain("Send")

    res = res.form.submit(name="action", value="password-initialization-mail")
    assert (
        "success",
        "A password initialization link has been sent at the user email address. "
        "It should be received within a few minutes.",
    ) in res.flashes
    assert len(smtpd.messages) == 1
    res = res.follow()

    u.reload()
    u.userPassword = ["{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz"]
    u.save()

    res = testclient.get("/profile/temp", status=200)
    res.mustcontain(no="This user does not have a password yet")

    u.delete()


@mock.patch("smtplib.SMTP")
def test_password_initialization_mail_send_fail(
    SMTP, smtpd, testclient, slapd_connection, logged_admin
):
    SMTP.side_effect = mock.Mock(side_effect=OSError("unit test mail error"))
    u = User(
        cn="Temp User",
        sn="Temp",
        uid="temp",
        mail="john@doe.com",
    )
    u.save()

    res = testclient.get("/profile/temp", status=200)
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

    res = res.follow()
    u.delete()


def test_password_initialization_invalid_user(
    smtpd, testclient, slapd_connection, logged_admin
):
    assert len(smtpd.messages) == 0
    testclient.post(
        "/profile/invalid", {"action": "password-initialization-mail"}, status=404
    )
    assert len(smtpd.messages) == 0


def test_password_reset_invalid_user(smtpd, testclient, slapd_connection, logged_admin):
    assert len(smtpd.messages) == 0
    testclient.post("/profile/invalid", {"action": "password-reset-mail"}, status=404)
    assert len(smtpd.messages) == 0


def test_delete_invalid_user(testclient, slapd_connection, logged_admin):
    testclient.post("/profile/invalid", {"action": "delete"}, status=404)


def test_impersonate_invalid_user(testclient, slapd_connection, logged_admin):
    testclient.get("/impersonate/invalid", status=404)


def test_password_reset_email(smtpd, testclient, slapd_connection, logged_admin):
    u = User(
        cn="Temp User",
        sn="Temp",
        uid="temp",
        mail="john@doe.com",
        userPassword=["{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz"],
    )
    u.save()

    res = testclient.get("/profile/temp", status=200)
    res.mustcontain("If the user has forgotten his password")
    res.mustcontain("Send")

    res = res.form.submit(name="action", value="password-reset-mail")
    assert (
        "success",
        "A password reset link has been sent at the user email address. "
        "It should be received within a few minutes.",
    ) in res.flashes
    assert len(smtpd.messages) == 1

    res = res.follow()
    u.delete()


@mock.patch("smtplib.SMTP")
def test_password_reset_email_failed(
    SMTP, smtpd, testclient, slapd_connection, logged_admin
):
    SMTP.side_effect = mock.Mock(side_effect=OSError("unit test mail error"))
    u = User(
        cn="Temp User",
        sn="Temp",
        uid="temp",
        mail="john@doe.com",
        userPassword=["{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz"],
    )
    u.save()

    res = testclient.get("/profile/temp", status=200)
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

    res = res.follow()
    u.delete()


def test_photo_on_profile_edition(
    testclient,
    slapd_server,
    logged_user,
    jpeg_photo,
):
    # Add a photo
    res = testclient.get("/profile/user", status=200)
    res.form["jpegPhoto"] = Upload("logo.jpg", jpeg_photo)
    res.form["jpegPhoto_delete"] = False
    res = res.form.submit(name="action", value="edit")
    assert ("success", "Profile updated successfuly.") in res.flashes
    res = res.follow()

    logged_user = User.get(id=logged_user.id)

    assert [jpeg_photo] == logged_user.jpegPhoto

    # No change
    res = testclient.get("/profile/user", status=200)
    res.form["jpegPhoto_delete"] = False
    res = res.form.submit(name="action", value="edit")
    assert ("success", "Profile updated successfuly.") in res.flashes
    res = res.follow()

    logged_user = User.get(id=logged_user.id)

    assert [jpeg_photo] == logged_user.jpegPhoto

    # Photo deletion
    res = testclient.get("/profile/user", status=200)
    res.form["jpegPhoto_delete"] = True
    res = res.form.submit(name="action", value="edit")
    assert ("success", "Profile updated successfuly.") in res.flashes
    res = res.follow()

    logged_user = User.get(id=logged_user.id)

    assert [] == logged_user.jpegPhoto

    # Photo deletion AND upload, this should never happen
    res = testclient.get("/profile/user", status=200)
    res.form["jpegPhoto"] = Upload("logo.jpg", jpeg_photo)
    res.form["jpegPhoto_delete"] = True
    res = res.form.submit(name="action", value="edit")
    assert ("success", "Profile updated successfuly.") in res.flashes
    res = res.follow()

    logged_user = User.get(id=logged_user.id)

    assert [] == logged_user.jpegPhoto


def test_photo_on_profile_creation(testclient, slapd_server, jpeg_photo, logged_admin):
    res = testclient.get("/users", status=200)
    assert User.get("foobar") is None
    res.mustcontain(no="foobar")

    res = testclient.get("/profile", status=200)
    res.form["jpegPhoto"] = Upload("logo.jpg", jpeg_photo)
    res.form["uid"] = "foobar"
    res.form["sn"] = "Abitbol"
    res.form["mail"] = "george@abitbol.com"
    res = res.form.submit(name="action", value="edit", status=302).follow(status=200)

    user = User.get("foobar")
    assert user.jpegPhoto == [jpeg_photo]
    user.delete()


def test_photo_deleted_on_profile_creation(
    testclient, slapd_server, jpeg_photo, logged_admin
):
    res = testclient.get("/users", status=200)
    assert User.get("foobar") is None
    res.mustcontain(no="foobar")

    res = testclient.get("/profile", status=200)
    res.form["jpegPhoto"] = Upload("logo.jpg", jpeg_photo)
    res.form["jpegPhoto_delete"] = True
    res.form["uid"] = "foobar"
    res.form["sn"] = "Abitbol"
    res.form["mail"] = "george@abitbol.com"
    res = res.form.submit(name="action", value="edit", status=302).follow(status=200)

    user = User.get("foobar")
    assert user.jpegPhoto == []
    user.delete()
