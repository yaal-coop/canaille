from canaille.models import User


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
    res.form["groups"] = [foo_group.id]
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

    res = testclient.get("/users", status=200)
    res.mustcontain("george")

    res = testclient.get("/profile/george/settings", status=200)
    assert "readonly" not in res.form["groups"].attrs

    # User have been edited
    res = testclient.get("/profile/george", status=200)
    res.form["givenName"] = "Georgio"
    res = res.form.submit(name="action", value="edit").follow()

    res = testclient.get("/profile/george/settings", status=200)
    res.form["groups"] = [foo_group.id, bar_group.id]
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
    res = testclient.get("/users", status=200)
    res.mustcontain("george")

    # User have been deleted.
    res = testclient.get("/profile/george/settings", status=200)
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


def test_username_already_taken(
    testclient, logged_moderator, user, foo_group, bar_group
):
    res = testclient.get("/profile", status=200)
    res.form["uid"] = "user"
    res.form["sn"] = "foo"
    res.form["mail"] = "any@thing.com"
    res = res.form.submit(name="action", value="edit")
    assert ("error", "User account creation failed.") in res.flashes
    res.mustcontain("The login &#39;user&#39; already exists")


def test_email_already_taken(testclient, logged_moderator, user, foo_group, bar_group):
    res = testclient.get("/profile", status=200)
    res.form["uid"] = "user2"
    res.form["sn"] = "foo"
    res.form["mail"] = "john@doe.com"
    res = res.form.submit(name="action", value="edit")
    assert ("error", "User account creation failed.") in res.flashes
    res.mustcontain("The email &#39;john@doe.com&#39; already exists")


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
