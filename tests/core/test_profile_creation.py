from canaille.app import models


def test_user_creation_edition_and_deletion(
    testclient, logged_moderator, foo_group, bar_group, backend
):
    # The user does not exist.
    res = testclient.get("/users", status=200)
    assert backend.get(models.User, user_name="george") is None
    res.mustcontain(no="george")

    # Fill the profile for a new user.
    res = testclient.get("/profile", status=200)
    res.form["user_name"] = "george"
    res.form["given_name"] = "George"
    res.form["family_name"] = "Abitbol"
    res.form["emails-0"] = "george@abitbol.test"
    res.form["phone_numbers-0"] = "555-666-888"
    res.form["groups"] = [foo_group.id]
    res.form["password1"] = "totoyolo"
    res.form["password2"] = "totoyolo"

    # User have been created
    res = res.form.submit(name="action", value="create-profile", status=302)
    assert ("success", "User account creation succeed.") in res.flashes
    res = res.follow(status=200)
    george = backend.get(models.User, user_name="george")
    backend.reload(foo_group)
    assert "George" == george.given_name
    assert george.groups == [foo_group]
    assert backend.check_user_password(george, "totoyolo")[0]

    res = testclient.get("/users", status=200)
    res.mustcontain("george")

    res = testclient.get("/profile/george/settings", status=200)
    assert "readonly" not in res.form["groups"].attrs

    # User have been edited
    res = testclient.get("/profile/george", status=200)
    res.form["given_name"] = "Georgio"
    res = res.form.submit(name="action", value="edit-profile").follow()

    res = testclient.get("/profile/george/settings", status=200)
    res.form["groups"] = [foo_group.id, bar_group.id]
    res = res.form.submit(name="action", value="edit-settings").follow()

    george = backend.get(models.User, user_name="george")
    assert "Georgio" == george.given_name
    assert backend.check_user_password(george, "totoyolo")[0]

    backend.reload(foo_group)
    backend.reload(bar_group)
    assert george in set(foo_group.members)
    assert george in set(bar_group.members)
    assert set(george.groups) == {foo_group, bar_group}
    res = testclient.get("/users", status=200)
    res.mustcontain("george")

    # User have been deleted.
    res = testclient.get("/profile/george/settings", status=200)
    res = res.form.submit(name="action", value="confirm-delete", status=200)
    res = res.form.submit(name="action", value="delete", status=302)
    res = res.follow(status=200)
    assert backend.get(models.User, user_name="george") is None
    res.mustcontain(no="george")


def test_profile_creation_dynamic_validation(testclient, logged_admin, user):
    res = testclient.get("/profile")
    res = testclient.post(
        "/profile",
        {
            "csrf_token": res.form["csrf_token"].value,
            "emails-0": "john@doe.test",
        },
        headers={
            "HX-Request": "true",
            "HX-Trigger-Name": "emails-0",
        },
    )
    res.mustcontain("The email &#39;john@doe.test&#39; is already used")


def test_user_creation_without_password(testclient, logged_moderator, backend):
    res = testclient.get("/profile", status=200)
    res.form["user_name"] = "george"
    res.form["family_name"] = "Abitbol"
    res.form["emails-0"] = "george@abitbol.test"

    res = res.form.submit(name="action", value="create-profile", status=302)
    assert ("success", "User account creation succeed.") in res.flashes
    res = res.follow(status=200)
    george = backend.get(models.User, user_name="george")
    assert george.user_name == "george"
    assert not george.has_password()

    backend.delete(george)


def test_user_creation_form_validation_failed(
    testclient, logged_moderator, foo_group, bar_group, backend
):
    res = testclient.get("/users", status=200)
    assert backend.get(models.User, user_name="george") is None
    res.mustcontain(no="george")

    res = testclient.get("/profile", status=200)
    res = res.form.submit(name="action", value="create-profile")
    assert ("error", "User account creation failed.") in res.flashes
    assert backend.get(models.User, user_name="george") is None


def test_username_already_taken(
    testclient, logged_moderator, user, foo_group, bar_group
):
    res = testclient.get("/profile", status=200)
    res.form["user_name"] = "user"
    res.form["family_name"] = "foo"
    res.form["emails-0"] = "any@thing.test"
    res = res.form.submit(name="action", value="create-profile")
    assert ("error", "User account creation failed.") in res.flashes
    res.mustcontain("The user name &#39;user&#39; already exists")


def test_email_already_taken(testclient, logged_moderator, user, foo_group, bar_group):
    res = testclient.get("/profile", status=200)
    res.form["user_name"] = "user2"
    res.form["family_name"] = "foo"
    res.form["emails-0"] = "john@doe.test"
    res = res.form.submit(name="action", value="create-profile")
    assert ("error", "User account creation failed.") in res.flashes
    res.mustcontain("The email &#39;john@doe.test&#39; is already used")


def test_cn_setting_with_given_name_and_surname(testclient, logged_moderator, backend):
    res = testclient.get("/profile", status=200)
    res.form["user_name"] = "george"
    res.form["given_name"] = "George"
    res.form["family_name"] = "Abitbol"
    res.form["emails-0"] = "george@abitbol.test"

    res = res.form.submit(name="action", value="create-profile", status=302).follow(
        status=200
    )

    george = backend.get(models.User, user_name="george")
    assert george.formatted_name == "George Abitbol"
    backend.delete(george)


def test_cn_setting_with_surname_only(testclient, logged_moderator, backend):
    res = testclient.get("/profile", status=200)
    res.form["user_name"] = "george"
    res.form["family_name"] = "Abitbol"
    res.form["emails-0"] = "george@abitbol.test"

    res = res.form.submit(name="action", value="create-profile", status=302).follow(
        status=200
    )

    george = backend.get(models.User, user_name="george")
    assert george.formatted_name == "Abitbol"
    backend.delete(george)


def test_formcontrol(testclient, logged_admin):
    res = testclient.get("/profile")
    assert "emails-1" not in res.form.fields

    res = res.form.submit(status=200, name="fieldlist_add", value="emails-0")
    assert "emails-1" in res.form.fields


def test_formcontrol_htmx(testclient, logged_admin):
    res = testclient.get("/profile")
    data = {
        field: res.form[field].value
        for field in res.form.fields
        if len(res.form.fields.get(field)) == 1
    }
    data["fieldlist_add"] = "emails-0"
    response = testclient.post(
        "/profile",
        data,
        headers={
            "HX-Request": "true",
            "HX-Trigger-Name": "listfield_add",
        },
    )
    assert "emails-0" in response.text
    assert "emails-1" in response.text
