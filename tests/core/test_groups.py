from canaille.core.models import Group
from canaille.core.models import User
from canaille.core.populate import fake_groups
from canaille.core.populate import fake_users


def test_no_group(app, backend):
    assert Group.query() == []


def test_group_list_pagination(testclient, logged_admin, foo_group):
    res = testclient.get("/groups")
    res.mustcontain("1 items")

    groups = fake_groups(25)

    res = testclient.get("/groups")
    res.mustcontain("26 items")
    group_name = res.pyquery(
        ".groups tbody tr:nth-of-type(1) td:nth-of-type(2) a"
    ).text()
    assert group_name

    form = res.forms["next"]
    form["page"] = 2
    res = form.submit()
    assert group_name not in res.pyquery(
        ".groups tbody tr td:nth-of-type(2) a"
    ).text().split(" ")
    for group in groups:
        group.delete()

    res = testclient.get("/groups")
    res.mustcontain("1 items")


def test_group_list_bad_pages(testclient, logged_admin):
    res = testclient.get("/groups")
    form = res.forms["next"]
    testclient.post(
        "/groups", {"csrf_token": form["csrf_token"].value, "page": "2"}, status=404
    )

    res = testclient.get("/groups")
    form = res.forms["next"]
    testclient.post(
        "/groups", {"csrf_token": form["csrf_token"].value, "page": "-1"}, status=404
    )


def test_group_deletion(testclient, slapd_server, backend):
    user = User(
        formatted_name="foobar",
        family_name="foobar",
        user_name="foobar",
        email="foo@bar.com",
    )
    user.save()

    group = Group(
        members=[user],
        display_name="foobar",
    )
    group.save()

    user.reload()
    assert user.groups == [group]

    group.delete()
    user.reload()
    assert not user.groups

    user.delete()


def test_group_list_search(testclient, logged_admin, foo_group, bar_group):
    res = testclient.get("/groups")
    res.mustcontain("2 items")
    res.mustcontain(foo_group.display_name)
    res.mustcontain(bar_group.display_name)

    form = res.forms["search"]
    form["query"] = "oo"
    res = form.submit()

    res.mustcontain("1 items")
    res.mustcontain(foo_group.display_name)
    res.mustcontain(no=bar_group.display_name)


def test_set_groups(app, user, foo_group, bar_group):
    assert user in foo_group.members
    assert user.groups == [foo_group]

    user.groups = [foo_group, bar_group]
    user.save()

    bar_group.reload()
    assert user in bar_group.members
    assert user.groups[1] == bar_group

    user.groups = [foo_group]
    user.save()

    foo_group.reload()
    bar_group.reload()
    assert user in foo_group.members
    assert user not in bar_group.members


def test_set_groups_with_leading_space_in_user_id_attribute(app, foo_group):
    user = User(
        formatted_name=" Doe",  # leading space in id attribute
        family_name="Doe",
        user_name="user2",
        email="john@doe.com",
    )
    user.save()

    user.groups = [foo_group]
    user.save()

    foo_group.reload()
    assert user in foo_group.members

    user.groups = []
    user.save()

    foo_group.reload()
    assert user.id not in foo_group.members

    user.delete()


def test_moderator_can_create_edit_and_delete_group(
    testclient, logged_moderator, foo_group
):
    # The group does not exist
    res = testclient.get("/groups", status=200)
    assert Group.get(display_name="bar") is None
    assert Group.get(display_name="foo") == foo_group
    res.mustcontain(no="bar")
    res.mustcontain("foo")

    # Fill the form for a new group
    res = testclient.get("/groups/add", status=200)
    form = res.forms["creategroupform"]
    form["display_name"] = "bar"
    form["description"] = "yolo"

    # Group has been created
    res = form.submit(status=302).follow(status=200)

    logged_moderator.reload()
    bar_group = Group.get(display_name="bar")
    assert bar_group.display_name == "bar"
    assert bar_group.description == ["yolo"]
    assert bar_group.members == [
        logged_moderator
    ]  # Group cannot be empty so creator is added in it
    res.mustcontain("bar")

    # Group name can not be edited
    res = testclient.get("/groups/bar", status=200)
    form = res.forms["editgroupform"]
    form["display_name"] = "bar2"
    form["description"] = ["yolo2"]

    res = form.submit(name="action", value="edit").follow()

    bar_group = Group.get(display_name="bar")
    assert bar_group.display_name == "bar"
    assert bar_group.description == ["yolo2"]
    assert Group.get(display_name="bar2") is None
    members = bar_group.members
    for member in members:
        res.mustcontain(member.formatted_name[0])

    # Group is deleted
    res = form.submit(name="action", value="delete", status=302)
    assert Group.get(display_name="bar") is None
    assert ("success", "The group bar has been sucessfully deleted") in res.flashes


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


def test_edition_failed(testclient, logged_moderator, foo_group):
    res = testclient.get("/groups/foo")
    form = res.forms["editgroupform"]
    form["display_name"] = ""
    res = form.submit(name="action", value="edit")
    res.mustcontain("Group edition failed.")
    foo_group.reload()
    assert foo_group.display_name == "foo"


def test_user_list_pagination(testclient, logged_admin, foo_group):
    res = testclient.get("/groups/foo")
    res.mustcontain("1 items")

    users = fake_users(25)
    for user in users:
        foo_group.members = foo_group.members + [user]
    foo_group.save()

    res = testclient.get("/groups/foo")
    res.mustcontain("26 items")
    user_name = res.pyquery(".users tbody tr:nth-of-type(1) td:nth-of-type(2) a").text()
    assert user_name

    form = res.forms["next"]
    form["page"] = 2
    res = form.submit()
    assert user_name not in res.pyquery(".users tr td:nth-of-type(2) a").text().split(
        " "
    )
    for user in users:
        user.delete()

    res = testclient.get("/groups/foo")
    res.mustcontain("1 items")


def test_user_list_bad_pages(testclient, logged_admin, foo_group):
    res = testclient.get("/groups/foo")
    form = res.forms["next"]
    testclient.post(
        "/groups/foo", {"csrf_token": form["csrf_token"].value, "page": "2"}, status=404
    )

    res = testclient.get("/groups/foo")
    form = res.forms["next"]
    testclient.post(
        "/groups/foo",
        {"csrf_token": form["csrf_token"].value, "page": "-1"},
        status=404,
    )


def test_user_list_search(testclient, logged_admin, foo_group, user, moderator):
    foo_group.members = foo_group.members + [logged_admin, moderator]
    foo_group.save()

    res = testclient.get("/groups/foo")
    res.mustcontain("3 items")
    res.mustcontain(user.formatted_name[0])
    res.mustcontain(logged_admin.formatted_name[0])
    res.mustcontain(moderator.formatted_name[0])

    form = res.forms["search"]
    form["query"] = "ohn"
    res = form.submit()

    res.mustcontain("1 items")
    res.mustcontain(user.formatted_name[0])
    res.mustcontain(no=logged_admin.formatted_name[0])
    res.mustcontain(no=moderator.formatted_name[0])
