from canaille.core.populate import fake_users
from webtest import Upload


def test_user_list_pagination(testclient, logged_admin):
    res = testclient.get("/users")
    res.mustcontain("1 item")

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
    res.mustcontain("1 item")


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
    res.mustcontain(moderator.formatted_name[0])
    res.mustcontain(user.formatted_name[0])

    form = res.forms["search"]
    form["query"] = "Jack"
    res = form.submit()

    res.mustcontain("1 item")
    res.mustcontain(moderator.formatted_name[0])
    res.mustcontain(no=user.formatted_name[0])


def test_user_list_search_only_allowed_fields(
    testclient, logged_admin, user, moderator
):
    res = testclient.get("/users")
    res.mustcontain("3 items")
    res.mustcontain(moderator.formatted_name[0])
    res.mustcontain(user.formatted_name[0])

    form = res.forms["search"]
    form["query"] = "user"
    res = form.submit()

    res.mustcontain("1 item")
    res.mustcontain(user.formatted_name[0])
    res.mustcontain(no=moderator.formatted_name[0])

    testclient.app.config["ACL"]["DEFAULT"]["READ"].remove("user_name")

    form = res.forms["search"]
    form["query"] = "user"
    res = form.submit()

    res.mustcontain("0 items")
    res.mustcontain(no=user.formatted_name[0])
    res.mustcontain(no=moderator.formatted_name[0])


def test_edition_permission(
    testclient,
    logged_user,
    admin,
):
    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    testclient.get("/profile/user", status=404)

    testclient.app.config["ACL"]["DEFAULT"]["PERMISSIONS"] = ["edit_self"]
    testclient.get("/profile/user", status=200)


def test_edition(
    testclient,
    logged_user,
    admin,
    jpeg_photo,
):
    res = testclient.get("/profile/user", status=200)
    res.form["given_name"] = "given_name"
    res.form["family_name"] = "family_name"
    res.form["display_name"] = "display_name"
    res.form["emails-0"] = "email@mydomain.tld"
    res.form["phone_numbers-0"] = "555-666-777"
    res.form["formatted_address"] = "formatted_address"
    res.form["street"] = "street"
    res.form["postal_code"] = "postal_code"
    res.form["locality"] = "locality"
    res.form["region"] = "region"
    res.form["employee_number"] = 666
    res.form["department"] = 1337
    res.form["title"] = "title"
    res.form["organization"] = "organization"
    res.form["preferred_language"] = "fr"
    res.form["photo"] = Upload("logo.jpg", jpeg_photo)

    res = res.form.submit(name="action", value="edit")
    assert res.flashes == [
        ("success", "Le profil a été mis à jour avec succès.")
    ], res.text
    res = res.follow()

    logged_user.reload()

    assert logged_user.given_name == ["given_name"]
    assert logged_user.family_name == ["family_name"]
    assert logged_user.display_name == "display_name"
    assert logged_user.emails == ["email@mydomain.tld"]
    assert logged_user.phone_numbers == ["555-666-777"]
    assert logged_user.formatted_address == ["formatted_address"]
    assert logged_user.street == ["street"]
    assert logged_user.postal_code == ["postal_code"]
    assert logged_user.locality == ["locality"]
    assert logged_user.region == ["region"]
    assert logged_user.preferred_language == "fr"
    assert logged_user.employee_number == "666"
    assert logged_user.department == ["1337"]
    assert logged_user.title == ["title"]
    assert logged_user.organization == ["organization"]
    assert logged_user.photo == [jpeg_photo]

    logged_user.formatted_name = ["John (johnny) Doe"]
    logged_user.family_name = ["Doe"]
    logged_user.emails = ["john@doe.com"]
    logged_user.given_name = None
    logged_user.photo = None
    logged_user.save()


def test_edition_remove_fields(
    testclient,
    logged_user,
    admin,
):
    res = testclient.get("/profile/user", status=200)
    res.form["display_name"] = ""
    res.form["phone_numbers-0"] = ""

    res = res.form.submit(name="action", value="edit")
    assert res.flashes == [("success", "Profile updated successfully.")], res.text
    res = res.follow()

    logged_user.reload()

    assert not logged_user.display_name
    assert not logged_user.phone_numbers

    logged_user.formatted_name = ["John (johnny) Doe"]
    logged_user.family_name = ["Doe"]
    logged_user.emails = ["john@doe.com"]
    logged_user.given_name = None
    logged_user.photo = None
    logged_user.save()


def test_field_permissions_none(testclient, logged_user):
    testclient.get("/profile/user", status=200)
    logged_user.phone_numbers = ["555-666-777"]
    logged_user.save()

    testclient.app.config["ACL"]["DEFAULT"] = {
        "READ": ["user_name"],
        "WRITE": [],
        "PERMISSIONS": ["edit_self"],
    }

    res = testclient.get("/profile/user", status=200)
    assert "phone_numbers-0" not in res.form.fields

    testclient.post(
        "/profile/user",
        {
            "action": "edit",
            "phone_numbers-0": "000-000-000",
            "csrf_token": res.form["csrf_token"].value,
        },
    )
    logged_user.reload()
    assert logged_user.phone_numbers == ["555-666-777"]


def test_field_permissions_read(testclient, logged_user):
    testclient.get("/profile/user", status=200)
    logged_user.phone_numbers = ["555-666-777"]
    logged_user.save()

    testclient.app.config["ACL"]["DEFAULT"] = {
        "READ": ["user_name", "phone_numbers"],
        "WRITE": [],
        "PERMISSIONS": ["edit_self"],
    }
    res = testclient.get("/profile/user", status=200)
    assert "phone_numbers-0" in res.form.fields

    testclient.post(
        "/profile/user",
        {
            "action": "edit",
            "phone_numbers-0": "000-000-000",
            "csrf_token": res.form["csrf_token"].value,
        },
    )
    logged_user.reload()
    assert logged_user.phone_numbers == ["555-666-777"]


def test_field_permissions_write(testclient, logged_user):
    testclient.get("/profile/user", status=200)
    logged_user.phone_numbers = ["555-666-777"]
    logged_user.save()

    testclient.app.config["ACL"]["DEFAULT"] = {
        "READ": ["user_name"],
        "WRITE": ["phone_numbers"],
        "PERMISSIONS": ["edit_self"],
    }
    res = testclient.get("/profile/user", status=200)
    assert "phone_numbers-0" in res.form.fields

    testclient.post(
        "/profile/user",
        {
            "action": "edit",
            "phone_numbers-0": "000-000-000",
            "csrf_token": res.form["csrf_token"].value,
        },
    )
    logged_user.reload()
    assert logged_user.phone_numbers == ["000-000-000"]


def test_simple_user_cannot_edit_other(testclient, admin, logged_user):
    res = testclient.get("/profile/user", status=200)
    testclient.get("/profile/admin", status=404)
    testclient.post(
        "/profile/admin",
        {"action": "edit", "csrf_token": res.form["csrf_token"].value},
        status=404,
    )
    testclient.post(
        "/profile/admin",
        {"action": "delete", "csrf_token": res.form["csrf_token"].value},
        status=404,
    )
    testclient.get("/users", status=403)


def test_admin_bad_request(testclient, logged_moderator):
    testclient.get("/profile/foobar", status=404)


def test_bad_email(testclient, logged_user):
    res = testclient.get("/profile/user", status=200)

    res.form["emails-0"] = "john@doe.com"

    res = res.form.submit(name="action", value="edit").follow()

    assert ["john@doe.com"] == logged_user.emails

    res = testclient.get("/profile/user", status=200)

    res.form["emails-0"] = "yolo"

    res = res.form.submit(name="action", value="edit", status=200)

    logged_user.reload()

    assert ["john@doe.com"] == logged_user.emails


def test_surname_is_mandatory(testclient, logged_user):
    res = testclient.get("/profile/user", status=200)
    logged_user.family_name = ["Doe"]

    res.form["family_name"] = ""

    res = res.form.submit(name="action", value="edit", status=200)

    logged_user.reload()

    assert ["Doe"] == logged_user.family_name


def test_formcontrol(testclient, logged_user):
    res = testclient.get("/profile/user")
    assert "emails-1" not in res.form.fields

    res = res.form.submit(status=200, name="fieldlist_add", value="emails-0")
    assert "emails-1" in res.form.fields


def test_formcontrol_htmx(testclient, logged_user):
    res = testclient.get("/profile/user")
    data = {
        field: res.form[field].value
        for field in res.form.fields
        if len(res.form.fields.get(field)) == 1
    }
    data["fieldlist_add"] = "emails-0"
    response = testclient.post(
        "/profile/user",
        data,
        headers={
            "HX-Request": "true",
            "HX-Trigger-Name": "listfield_add",
        },
    )
    assert "emails-0" in response.text
    assert "emails-1" in response.text


def test_inline_validation(testclient, logged_admin, user):
    res = testclient.get("/profile/admin")
    res = testclient.post(
        "/profile/admin",
        {
            "csrf_token": res.form["csrf_token"].value,
            "emails-0": "john@doe.com",
        },
        headers={
            "HX-Request": "true",
            "HX-Trigger-Name": "emails-0",
        },
    )
    res.mustcontain("The email &#39;john@doe.com&#39; is already used")


def test_inline_validation_keep_indicators(
    configuration, testclient, logged_admin, user
):
    configuration["ACL"]["DEFAULT"]["WRITE"].remove("display_name")
    configuration["ACL"]["DEFAULT"]["READ"].append("display_name")
    configuration["ACL"]["ADMIN"]["WRITE"].append("display_name")

    res = testclient.get("/profile/admin")
    res = testclient.post(
        "/profile/user",
        {
            "csrf_token": res.form["csrf_token"].value,
            "display_name": "George Abitbol",
        },
        headers={
            "HX-Request": "true",
            "HX-Trigger-Name": "display_name",
        },
    )
    res.mustcontain("This user cannot edit this field")
