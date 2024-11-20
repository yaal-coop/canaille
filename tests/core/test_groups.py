from canaille.app import models
from canaille.core.populate import fake_groups
from canaille.core.populate import fake_users


def test_delete_group(testclient, backend, user, admin, foo_group):
    foo_group.members = [user, admin]
    backend.save(foo_group)

    user = backend.get(models.User, user.id)
    user.groups = []
    backend.save(user)


def test_no_group(app, backend):
    assert backend.query(models.Group) == []


def test_group_list_pagination(testclient, logged_admin, foo_group, backend):
    res = testclient.get("/groups")
    res.mustcontain("1 item")

    groups = fake_groups(25)

    res = testclient.get("/groups")
    res.mustcontain("26 items")
    group_name = res.pyquery(
        ".groups tbody tr:nth-of-type(1) td:nth-of-type(2) a"
    ).text()
    assert group_name

    form = res.forms["tableform"]
    res = form.submit(name="page", value="2")
    assert group_name not in res.pyquery(
        ".groups tbody tr td:nth-of-type(2) a"
    ).text().split(" ")
    for group in groups:
        backend.delete(group)

    res = testclient.get("/groups")
    res.mustcontain("1 item")


def test_group_list_bad_pages(testclient, logged_admin):
    res = testclient.get("/groups")
    form = res.forms["tableform"]
    testclient.post(
        "/groups", {"csrf_token": form["csrf_token"].value, "page": "2"}, status=404
    )

    res = testclient.get("/groups")
    form = res.forms["tableform"]
    testclient.post(
        "/groups", {"csrf_token": form["csrf_token"].value, "page": "-1"}, status=404
    )


def test_group_deletion(testclient, backend):
    user = models.User(
        formatted_name="foobar",
        family_name="foobar",
        user_name="foobar",
        emails=["foo@bar.test"],
    )
    backend.save(user)

    group = models.Group(
        members=[user],
        display_name="foobar",
    )
    backend.save(group)

    backend.reload(user)
    assert user.groups == [group]

    backend.delete(group)
    backend.reload(user)
    assert not user.groups

    backend.delete(user)


def test_group_list_search(testclient, logged_admin, foo_group, bar_group):
    res = testclient.get("/groups")
    res.mustcontain("2 items")
    res.mustcontain(foo_group.display_name)
    res.mustcontain(bar_group.display_name)

    form = res.forms["search"]
    form["query"] = "oo"
    res = form.submit()

    res.mustcontain("1 item")
    res.mustcontain(foo_group.display_name)
    res.mustcontain(no=bar_group.display_name)


def test_set_groups(app, user, foo_group, bar_group, backend):
    assert user in foo_group.members
    assert user.groups == [foo_group]

    user.groups = [foo_group, bar_group]
    backend.save(user)

    backend.reload(bar_group)
    assert user in bar_group.members
    assert bar_group in user.groups

    user.groups = [foo_group]
    backend.save(user)

    backend.reload(foo_group)
    backend.reload(bar_group)
    assert user in foo_group.members
    assert user not in bar_group.members


def test_set_groups_with_leading_space_in_user_id_attribute(app, foo_group, backend):
    user = models.User(
        formatted_name=" Doe",  # leading space in id attribute
        family_name="Doe",
        user_name="user2",
        emails=["john@doe.test"],
    )
    backend.save(user)

    user.groups = [foo_group]
    backend.save(user)

    backend.reload(foo_group)
    assert user in foo_group.members

    user.groups = []
    backend.save(user)

    backend.reload(foo_group)
    assert user.id not in foo_group.members

    backend.delete(user)


def test_moderator_can_create_edit_and_delete_group(
    testclient, logged_moderator, foo_group, backend
):
    # The group does not exist
    res = testclient.get("/groups", status=200)
    assert backend.get(models.Group, display_name="bar") is None
    assert backend.get(models.Group, display_name="foo") == foo_group
    res.mustcontain(no="bar")
    res.mustcontain("foo")

    # Fill the form for a new group
    res = testclient.get("/groups/add", status=200)
    form = res.forms["creategroupform"]
    form["display_name"] = "bar"
    form["description"] = "yolo"

    # Group has been created
    res = form.submit(status=302).follow(status=200)

    backend.reload(logged_moderator)
    bar_group = backend.get(models.Group, display_name="bar")
    assert bar_group.display_name == "bar"
    assert bar_group.description == "yolo"
    assert bar_group.members == [
        logged_moderator
    ]  # Group cannot be empty so creator is added in it
    res.mustcontain("bar")

    # Group name can not be edited
    res = testclient.get("/groups/bar", status=200)
    form = res.forms["editgroupform"]
    form["display_name"] = "bar2"
    form["description"] = "yolo2"

    res = form.submit(name="action", value="edit")
    assert res.flashes == [("error", "Group edition failed.")]
    res.mustcontain("This field cannot be edited")

    bar_group = backend.get(models.Group, display_name="bar")
    assert bar_group.display_name == "bar"
    assert bar_group.description == "yolo"
    assert backend.get(models.Group, display_name="bar2") is None

    # Group description can be edited
    res = testclient.get("/groups/bar", status=200)
    form = res.forms["editgroupform"]
    form["description"] = "yolo2"

    res = form.submit(name="action", value="edit")
    assert res.flashes == [("success", "The group bar has been successfully edited.")]
    res = res.follow()

    bar_group = backend.get(models.Group, display_name="bar")
    assert bar_group.display_name == "bar"
    assert bar_group.description == "yolo2"

    # Group is deleted
    res = res.forms["editgroupform"].submit(name="action", value="confirm-delete")
    res = res.form.submit(name="action", value="delete", status=302)
    assert backend.get(models.Group, display_name="bar") is None
    assert ("success", "The group bar has been successfully deleted") in res.flashes


def test_cannot_create_already_existing_group(testclient, logged_moderator, foo_group):
    res = testclient.get("/groups/add")
    res = testclient.post(
        "/groups/add",
        {"csrf_token": res.form["csrf_token"].value, "display_name": "foo"},
        status=200,
    )

    res.mustcontain("Group creation failed.")
    res.mustcontain("The group &#39;foo&#39; already exists")


def test_invalid_group(testclient, logged_moderator):
    testclient.get("/groups/invalid", status=404)


def test_simple_user_cannot_view_or_edit_groups(testclient, logged_user, foo_group):
    testclient.get("/groups", status=403)
    testclient.get("/groups/add", status=403)
    testclient.get("/groups/foo", status=403)


def test_invalid_form_request(testclient, logged_moderator, foo_group):
    res = testclient.get("/groups/foo")
    form = res.forms["editgroupform"]
    res = form.submit(name="action", value="invalid-action", status=400)


def test_edition_failed(testclient, logged_moderator, foo_group, backend):
    res = testclient.get("/groups/foo")
    form = res.forms["editgroupform"]
    form["display_name"] = ""
    res = form.submit(name="action", value="edit")
    res.mustcontain("Group edition failed.")
    backend.reload(foo_group)
    assert foo_group.display_name == "foo"


def test_user_list_pagination(testclient, logged_admin, foo_group, backend):
    res = testclient.get("/groups/foo")
    res.mustcontain("1 item")

    users = fake_users(25)
    for user in users:
        foo_group.members = foo_group.members + [user]
    backend.save(foo_group)

    assert len(foo_group.members) == 26
    res = testclient.get("/groups/foo")
    res.mustcontain("26 items")
    user_name = res.pyquery(".users tbody tr:nth-of-type(1) td:nth-of-type(2) a").text()
    assert user_name

    form = res.forms["tableform"]
    res = form.submit(name="page", value="2")
    assert user_name not in res.pyquery(".users tr td:nth-of-type(2) a").text().split(
        " "
    )
    for user in users:
        backend.delete(user)

    res = testclient.get("/groups/foo")
    res.mustcontain("1 item")


def test_user_list_bad_pages(testclient, logged_admin, foo_group):
    res = testclient.get("/groups/foo")
    form = res.forms["tableform"]
    testclient.post(
        "/groups/foo", {"csrf_token": form["csrf_token"].value, "page": "2"}, status=404
    )

    res = testclient.get("/groups/foo")
    form = res.forms["tableform"]
    testclient.post(
        "/groups/foo",
        {"csrf_token": form["csrf_token"].value, "page": "-1"},
        status=404,
    )


def test_user_list_search(
    testclient, logged_admin, foo_group, user, moderator, backend
):
    foo_group.members = foo_group.members + [logged_admin, moderator]
    backend.save(foo_group)

    res = testclient.get("/groups/foo")
    res.mustcontain("3 items")
    res.mustcontain(user.formatted_name)
    res.mustcontain(logged_admin.formatted_name)
    res.mustcontain(moderator.formatted_name)

    form = res.forms["search"]
    form["query"] = "ohn"
    res = form.submit()

    res.mustcontain("1 item")
    res.mustcontain(user.formatted_name)
    res.mustcontain(no=logged_admin.formatted_name)
    res.mustcontain(no=moderator.formatted_name)


def test_remove_member(testclient, logged_admin, foo_group, user, moderator, backend):
    foo_group.members = [user, moderator]
    backend.save(foo_group)

    res = testclient.get("/groups/foo")
    form = res.forms[f"deletegroupmemberform-{user.id}"]

    res = form.submit(name="action", value="confirm-remove-member")
    res = res.form.submit(name="action", value="remove-member")
    assert (
        "success",
        "John (johnny) Doe has been removed from the group foo",
    ) in res.flashes

    backend.reload(foo_group)
    assert user not in foo_group.members


def test_remove_member_already_remove_from_group(
    testclient, logged_admin, foo_group, user, moderator, backend
):
    foo_group.members = [user, moderator]
    backend.save(foo_group)

    res = testclient.get("/groups/foo")
    form = res.forms[f"deletegroupmemberform-{user.id}"]
    foo_group.members = [moderator]
    backend.save(foo_group)

    res = form.submit(name="action", value="confirm-remove-member")
    assert (
        "error",
        "The user 'John (johnny) Doe' has already been removed from the group 'foo'",
    ) in res.flashes


def test_confirm_remove_member_already_removed_from_group(
    testclient, logged_admin, foo_group, user, moderator, backend
):
    foo_group.members = [user, moderator]
    backend.save(foo_group)

    res = testclient.get("/groups/foo")
    form = res.forms[f"deletegroupmemberform-{user.id}"]
    res = form.submit(name="action", value="confirm-remove-member")

    foo_group.members = [moderator]
    backend.save(foo_group)
    res = res.form.submit(name="action", value="remove-member")

    assert (
        "error",
        "The user 'John (johnny) Doe' has already been removed from the group 'foo'",
    ) in res.flashes


def test_remove_member_already_deleted(
    testclient, logged_admin, foo_group, moderator, backend
):
    user = models.User(
        formatted_name="Foo bar",
        family_name="Bar",
        user_name="foobar",
        emails=["foobar@example.test"],
    )
    backend.save(user)
    foo_group.members = [user, moderator]
    backend.save(foo_group)

    res = testclient.get("/groups/foo")
    form = res.forms[f"deletegroupmemberform-{user.id}"]
    backend.delete(user)

    res = form.submit(name="action", value="confirm-remove-member")
    assert (
        "error",
        "The user you are trying to remove does not exist.",
    ) in res.flashes


def test_confirm_remove_member_already_deleted(
    testclient, logged_admin, foo_group, moderator, backend
):
    user = models.User(
        formatted_name="Foo bar",
        family_name="Bar",
        emails=["foobar@example.test"],
        user_name="foobar",
    )
    backend.save(user)
    foo_group.members = [user, moderator]
    backend.save(foo_group)

    res = testclient.get("/groups/foo")
    form = res.forms[f"deletegroupmemberform-{user.id}"]
    res = form.submit(name="action", value="confirm-remove-member")

    backend.delete(user)
    res = res.form.submit(name="action", value="remove-member")

    assert (
        "error",
        "The user you are trying to remove does not exist.",
    ) in res.flashes
