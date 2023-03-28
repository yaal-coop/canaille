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
        "/users", {"csrf_token": form["csrf_token"].value, "page": "2"}, status=404
    )

    res = testclient.get("/users")
    form = res.forms["next"]
    testclient.post(
        "/users", {"csrf_token": form["csrf_token"].value, "page": "-1"}, status=404
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
    jpeg_photo,
):
    res = testclient.get("/profile/user", status=200)
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
    res.form["o"] = "organization"
    res.form["preferredLanguage"] = "fr"
    res.form["jpegPhoto"] = Upload("logo.jpg", jpeg_photo)

    res = res.form.submit(name="action", value="edit")
    assert res.flashes == [
        ("success", "Le profil a été mis à jour avec succès.")
    ], res.text
    res = res.follow()

    logged_user = User.get(id=logged_user.id)

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
    assert logged_user.o == ["organization"]
    assert logged_user.jpegPhoto == [jpeg_photo]

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
        "/profile/user",
        {
            "action": "edit",
            "telephoneNumber": "000-000-000",
            "csrf_token": res.form["csrf_token"].value,
        },
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
        "/profile/user",
        {
            "action": "edit",
            "telephoneNumber": "000-000-000",
            "csrf_token": res.form["csrf_token"].value,
        },
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
        "/profile/user",
        {
            "action": "edit",
            "telephoneNumber": "000-000-000",
            "csrf_token": res.form["csrf_token"].value,
        },
    )
    user = User.get(id=logged_user.id)
    assert user.telephoneNumber == ["000-000-000"]


def test_simple_user_cannot_edit_other(testclient, logged_user):
    res = testclient.get("/profile/user", status=200)
    testclient.get("/profile/admin", status=403)
    testclient.post(
        "/profile/admin",
        {"action": "edit", "csrf_token": res.form["csrf_token"].value},
        status=403,
    )
    testclient.post(
        "/profile/admin",
        {"action": "delete", "csrf_token": res.form["csrf_token"].value},
        status=403,
    )
    testclient.get("/users", status=403)


def test_admin_bad_request(testclient, logged_moderator):
    testclient.get("/profile/foobar", status=404)


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
