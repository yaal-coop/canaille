import logging

import pytest
from flask import g
from webtest import Upload

from canaille.core.populate import fake_users


@pytest.fixture
def configuration(configuration):
    configuration["CANAILLE"]["EMAIL_CONFIRMATION"] = False
    return configuration


def test_invalid_form_request(testclient, logged_user):
    res = testclient.get("/profile/user")
    res = res.forms["baseform"].submit(
        name="action", value="invalid-action", status=400
    )


def test_user_list_pagination(testclient, logged_admin, backend):
    res = testclient.get("/users")
    res.mustcontain("1 item")

    users = fake_users(25)

    res = testclient.get("/users")
    res.mustcontain("26 items")
    user_name = res.pyquery(".users tbody tr:nth-of-type(1) td:nth-of-type(2) a").text()
    assert user_name

    form = res.forms["tableform"]
    res = form.submit(name="page", value="2")
    assert user_name not in res.pyquery(
        ".users tbody tr td:nth-of-type(2) a"
    ).text().split(" ")
    for user in users:
        backend.delete(user)

    res = testclient.get("/users")
    res.mustcontain("1 item")


def test_user_list_bad_pages(testclient, logged_admin):
    res = testclient.get("/users")
    form = res.forms["tableform"]
    testclient.post(
        "/users", {"csrf_token": form["csrf_token"].value, "page": "2"}, status=404
    )

    res = testclient.get("/users")
    form = res.forms["tableform"]
    testclient.post(
        "/users", {"csrf_token": form["csrf_token"].value, "page": "-1"}, status=404
    )


def test_user_list_search(testclient, logged_admin, user, moderator):
    res = testclient.get("/users")
    res.mustcontain("3 items")
    res.mustcontain(moderator.formatted_name)
    res.mustcontain(user.formatted_name)

    form = res.forms["search"]
    form["query"] = "Jack"
    res = form.submit()

    res.mustcontain("1 item")
    res.mustcontain(moderator.formatted_name)
    res.mustcontain(no=user.formatted_name)


def test_user_list_search_only_allowed_fields(
    testclient, logged_admin, user, moderator, backend
):
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["READ"].remove("user_name")
    testclient.app.config["CANAILLE"]["ACL"]["ADMIN"]["READ"].remove("user_name")

    res = testclient.get("/users")
    form = res.forms["search"]
    form["query"] = "user"
    res = form.submit()

    res.mustcontain("0 items")
    res.mustcontain(no=user.formatted_name)
    res.mustcontain(no=moderator.formatted_name)


def test_edition_permission(
    testclient,
    logged_user,
    admin,
    backend,
):
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = []
    backend.reload(logged_user)
    testclient.get("/profile/user", status=404)

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = ["edit_self"]
    backend.reload(g.user)
    testclient.get("/profile/user", status=200)


def test_edition(testclient, logged_user, admin, jpeg_photo, backend, caplog):
    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    form["given_name"] = "given_name"
    form["family_name"] = "family_name"
    form["display_name"] = "display_name"
    form["emails-0"] = "email@mydomain.test"
    form["phone_numbers-0"] = "555-666-777"
    form["formatted_address"] = "formatted_address"
    form["street"] = "street"
    form["postal_code"] = "postal_code"
    form["locality"] = "locality"
    form["region"] = "region"
    form["employee_number"] = 666
    form["department"] = 1337
    form["title"] = "title"
    form["organization"] = "organization"
    form["preferred_language"] = "fr"
    form["photo"] = Upload("logo.jpg", jpeg_photo)

    res = form.submit(name="action", value="edit-profile")
    assert res.flashes == [("success", "Le profil a été mis à jour avec succès.")], (
        res.text
    )
    assert (
        "canaille",
        logging.SECURITY,
        "Updated email for user from unknown IP",
    ) in caplog.record_tuples
    res = res.follow()

    backend.reload(logged_user)

    assert logged_user.given_name == "given_name"
    assert logged_user.family_name == "family_name"
    assert logged_user.display_name == "display_name"
    assert logged_user.emails == ["email@mydomain.test"]
    assert logged_user.phone_numbers == ["555-666-777"]
    assert logged_user.formatted_address == "formatted_address"
    assert logged_user.street == "street"
    assert logged_user.postal_code == "postal_code"
    assert logged_user.locality == "locality"
    assert logged_user.region == "region"
    assert logged_user.preferred_language == "fr"
    assert logged_user.employee_number == "666"
    assert logged_user.department == "1337"
    assert logged_user.title == "title"
    assert logged_user.organization == "organization"
    assert logged_user.photo == jpeg_photo

    logged_user.formatted_name = "John (johnny) Doe"
    logged_user.family_name = "Doe"
    logged_user.emails = ["john@doe.test"]
    logged_user.given_name = None
    logged_user.photo = None
    backend.save(logged_user)


def test_edition_remove_fields(
    testclient,
    logged_user,
    admin,
    backend,
):
    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    form["display_name"] = ""
    form["phone_numbers-0"] = ""

    res = form.submit(name="action", value="edit-profile")
    assert res.flashes == [("success", "Profile updated successfully.")], res.text
    res = res.follow()

    backend.reload(logged_user)

    assert not logged_user.display_name
    assert not logged_user.phone_numbers

    logged_user.formatted_name = "John (johnny) Doe"
    logged_user.family_name = "Doe"
    logged_user.emails = ["john@doe.test"]
    logged_user.given_name = None
    logged_user.photo = None
    backend.save(logged_user)


def test_field_permissions_none(testclient, logged_user, backend):
    logged_user.phone_numbers = ["555-666-777"]
    backend.save(logged_user)

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"] = {
        "READ": ["user_name"],
        "WRITE": [],
        "PERMISSIONS": ["edit_self"],
        "FILTER": None,
    }

    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    assert "phone_numbers-0" not in form.fields

    res = testclient.post(
        "/profile/user",
        {
            "action": "edit-profile",
            "phone_numbers-0": "000-000-000",
            "csrf_token": form["csrf_token"].value,
        },
    )
    assert ("success", "Profile updated successfully.") in res.flashes

    backend.reload(logged_user)
    assert logged_user.phone_numbers == ["555-666-777"]


def test_field_permissions_read(testclient, logged_user, backend):
    logged_user.phone_numbers = ["555-666-777"]
    backend.save(logged_user)

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"] = {
        "READ": ["user_name", "phone_numbers"],
        "WRITE": [],
        "PERMISSIONS": ["edit_self"],
        "FILTER": None,
    }

    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    assert "phone_numbers-0" in form.fields

    res = testclient.post(
        "/profile/user",
        {
            "action": "edit-profile",
            "phone_numbers-0": "000-000-000",
            "csrf_token": form["csrf_token"].value,
        },
    )
    assert ("error", "Profile edition failed.") in res.flashes

    backend.reload(logged_user)
    assert logged_user.phone_numbers == ["555-666-777"]


def test_field_permissions_write(testclient, logged_user, backend):
    logged_user.phone_numbers = ["555-666-777"]
    backend.save(logged_user)

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"] = {
        "READ": ["user_name"],
        "WRITE": ["phone_numbers"],
        "PERMISSIONS": ["edit_self"],
        "FILTER": None,
    }

    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    assert "phone_numbers-0" in form.fields

    res = testclient.post(
        "/profile/user",
        {
            "action": "edit-profile",
            "phone_numbers-0": "000-000-000",
            "csrf_token": form["csrf_token"].value,
        },
    )
    assert ("success", "Profile updated successfully.") in res.flashes

    backend.reload(logged_user)
    assert logged_user.phone_numbers == ["000-000-000"]


def test_simple_user_cannot_edit_other(testclient, admin, logged_user):
    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    testclient.get("/profile/admin", status=404)
    testclient.post(
        "/profile/admin",
        {"action": "edit-profile", "csrf_token": form["csrf_token"].value},
        status=404,
    )
    testclient.post(
        "/profile/admin",
        {"action": "delete", "csrf_token": form["csrf_token"].value},
        status=404,
    )
    testclient.get("/users", status=403)


def test_admin_bad_request(testclient, logged_moderator):
    testclient.get("/profile/foobar", status=404)


def test_bad_email(testclient, logged_user, backend):
    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]

    form["emails-0"] = "john@doe.test"

    res = form.submit(name="action", value="edit-profile").follow()

    assert ["john@doe.test"] == logged_user.emails

    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]

    form["emails-0"] = "yolo"

    res = form.submit(name="action", value="edit-profile", status=200)

    backend.reload(logged_user)

    assert ["john@doe.test"] == logged_user.emails


def test_surname_is_mandatory(testclient, logged_user, backend):
    res = testclient.get("/profile/user", status=200)
    form = res.forms["baseform"]
    logged_user.family_name = "Doe"

    form["family_name"] = ""

    res = form.submit(name="action", value="edit-profile", status=200)

    backend.reload(logged_user)

    assert "Doe" == logged_user.family_name


def test_formcontrol(testclient, logged_user):
    res = testclient.get("/profile/user")
    form = res.forms["baseform"]
    assert "emails-1" not in form.fields

    res = form.submit(status=200, name="fieldlist_add", value="emails-0")
    form = res.forms["baseform"]
    assert "emails-1" in form.fields


def test_formcontrol_htmx(testclient, logged_user):
    res = testclient.get("/profile/user")
    form = res.forms["baseform"]
    data = {
        field: form[field].value
        for field in form.fields
        if len(form.fields.get(field)) == 1
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
    form = res.forms["baseform"]
    res = testclient.post(
        "/profile/admin",
        {
            "csrf_token": form["csrf_token"].value,
            "emails-0": "john@doe.test",
            "action": "edit-profile",
        },
        headers={
            "HX-Request": "true",
            "HX-Trigger-Name": "emails-0",
        },
    )
    res.mustcontain("The email &#39;john@doe.test&#39; is already used")


def test_inline_validation_keep_indicators(testclient, logged_admin, user, backend):
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["WRITE"].remove("display_name")
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["READ"].append("display_name")
    testclient.app.config["CANAILLE"]["ACL"]["ADMIN"]["WRITE"].append("display_name")
    backend.reload(logged_admin)
    backend.reload(user)

    res = testclient.get("/profile/admin")
    form = res.forms["baseform"]
    res = testclient.post(
        "/profile/user",
        {
            "csrf_token": form["csrf_token"].value,
            "display_name": "George Abitbol",
            "action": "edit-profile",
        },
        headers={
            "HX-Request": "true",
            "HX-Trigger-Name": "display_name",
        },
    )
    res.mustcontain("This user cannot edit this field")
