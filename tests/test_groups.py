from canaille.models import Group
from canaille.models import User
from canaille.populate import fake_groups
from canaille.populate import fake_users


def test_no_group(app, slapd_connection):
    assert Group.query() == []


def test_group_list_pagination(testclient, logged_admin, foo_group):
    res = testclient.get("/groups")
    assert "1 items" in res

    groups = fake_groups(25)

    res = testclient.get("/groups")
    assert "26 items" in res, res.text
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
    assert "1 items" in res


def test_group_list_bad_pages(testclient, logged_admin):
    res = testclient.get("/groups")
    form = res.forms["next"]
    testclient.post(
        "/groups", {"csrf_token": form["csrf_token"], "page": "2"}, status=404
    )

    res = testclient.get("/groups")
    form = res.forms["next"]
    testclient.post(
        "/groups", {"csrf_token": form["csrf_token"], "page": "-1"}, status=404
    )


def test_group_list_search(testclient, logged_admin, foo_group, bar_group):
    res = testclient.get("/groups")
    assert "2 items" in res
    assert foo_group.name in res
    assert bar_group.name in res

    form = res.forms["search"]
    form["query"] = "oo"
    res = form.submit()

    assert "1 items" in res, res.text
    assert foo_group.name in res
    assert bar_group.name not in res


def test_set_groups(app, user, foo_group, bar_group):
    foo_dns = {m.dn for m in foo_group.get_members()}
    assert user.dn in foo_dns
    assert user.groups[0].dn == foo_group.dn

    user.load_groups()
    user.set_groups([foo_group, bar_group])

    bar_group = Group.get(bar_group.dn)
    bar_dns = {m.dn for m in bar_group.get_members()}
    assert user.dn in bar_dns
    assert user.groups[1].dn == bar_group.dn

    user.load_groups()
    user.set_groups([foo_group])

    foo_group = Group.get(foo_group.dn)
    bar_group = Group.get(bar_group.dn)
    foo_dns = {m.dn for m in foo_group.get_members()}
    bar_dns = {m.dn for m in bar_group.get_members()}
    assert user.dn in foo_dns
    assert user.dn not in bar_dns


def test_set_groups_with_leading_space_in_user_id_attribute(app, foo_group):
    user = User(
        cn=" Doe",  # leading space in id attribute
        sn="Doe",
        uid="user2",
        mail="john@doe.com",
    )
    user.save()

    user.load_groups()
    user.set_groups([foo_group])

    foo_dns = {m.dn for m in foo_group.get_members()}
    assert user.dn in foo_dns

    user.load_groups()
    user.set_groups([])

    foo_group = Group.get(foo_group.dn)
    foo_dns = {m.dn for m in foo_group.get_members()}
    assert user.dn not in foo_dns

    user.delete()


def test_moderator_can_create_edit_and_delete_group(
    testclient, logged_moderator, foo_group
):
    # The group does not exist
    res = testclient.get("/groups", status=200)
    assert Group.get("bar") is None
    assert Group.get("foo") == foo_group
    assert "bar" not in res.text
    assert "foo" in res.text

    # Fill the form for a new group
    res = testclient.get("/groups/add", status=200)
    form = res.forms["creategroupform"]
    form["name"] = "bar"
    form["description"] = "yolo"

    # Group has been created
    res = form.submit(status=302).follow(status=200)

    bar_group = Group.get("bar")
    assert bar_group.name == "bar"
    assert bar_group.description == ["yolo"]
    assert [member.dn for member in bar_group.get_members()] == [
        logged_moderator.dn
    ]  # Group cannot be empty so creator is added in it
    assert "bar" in res.text

    # Group name can not be edited
    res = testclient.get("/groups/bar", status=200)
    form = res.forms["editgroupform"]
    form["name"] = "bar2"
    form["description"] = ["yolo2"]

    res = form.submit(name="action", value="edit").follow()

    bar_group = Group.get("bar")
    assert bar_group.name == "bar"
    assert bar_group.description == ["yolo2"]
    assert Group.get("bar2") is None
    members = bar_group.get_members()
    for member in members:
        assert member.name in res.text

    # Group is deleted
    res = form.submit(name="action", value="delete", status=302)
    assert Group.get("bar") is None
    assert ("success", "The group bar has been sucessfully deleted") in res.flashes


def test_cannot_create_already_existing_group(testclient, logged_moderator, foo_group):
    res = testclient.post("/groups/add", {"name": "foo"}, status=200)

    assert "Group creation failed." in res
    assert "The group &#39;foo&#39; already exists" in res


def test_invalid_group(testclient, logged_moderator):
    testclient.get("/groups/invalid", status=404)


def test_simple_user_cannot_view_or_edit_groups(testclient, logged_user, foo_group):
    testclient.get("/groups", status=403)
    testclient.get("/groups/add", status=403)
    testclient.get("/groups/foo", status=403)


def test_get_members_filters_non_existent_user(
    testclient, logged_moderator, foo_group, user
):
    # an LDAP group can be inconsistent by containing members which doesn't exist
    non_existent_user = User(cn="foo", sn="bar")
    foo_group.member = foo_group.member + [non_existent_user]
    foo_group.save()

    foo_group.get_members()

    assert foo_group.member == [user, non_existent_user]

    testclient.get("/groups/foo", status=200)


def test_invalid_form_request(testclient, logged_moderator, foo_group):
    res = testclient.get("/groups/foo")
    form = res.forms["editgroupform"]
    res = form.submit(name="action", value="invalid-action", status=400)


def test_edition_failed(testclient, logged_moderator, foo_group):
    res = testclient.get("/groups/foo")
    form = res.forms["editgroupform"]
    form["csrf_token"] = "invalid"
    res = form.submit(name="action", value="edit")
    assert "Group edition failed." in res
    foo_group = Group.get(foo_group.dn)
    assert foo_group.name == "foo"


def test_user_list_pagination(testclient, logged_admin, foo_group):
    res = testclient.get("/groups/foo")
    assert "1 items" in res

    users = fake_users(25)
    for user in users:
        foo_group.add_member(user)
    foo_group.save()

    res = testclient.get("/groups/foo")
    assert "26 items" in res, res.text
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
    assert "1 items" in res


def test_user_list_bad_pages(testclient, logged_admin, foo_group):
    res = testclient.get("/groups/foo")
    form = res.forms["next"]
    testclient.post(
        "/groups/foo", {"csrf_token": form["csrf_token"], "page": "2"}, status=404
    )

    res = testclient.get("/groups/foo")
    form = res.forms["next"]
    testclient.post(
        "/groups/foo", {"csrf_token": form["csrf_token"], "page": "-1"}, status=404
    )


def test_user_list_search(testclient, logged_admin, foo_group, user, moderator):
    foo_group.add_member(logged_admin)
    foo_group.add_member(moderator)
    foo_group.save()

    res = testclient.get("/groups/foo")
    assert "3 items" in res
    assert user.name in res
    assert moderator.name in res

    form = res.forms["search"]
    form["query"] = "ohn"
    res = form.submit()

    assert "1 items" in res
    assert user.name in res
    assert logged_admin.name not in res
    assert moderator.name not in res
