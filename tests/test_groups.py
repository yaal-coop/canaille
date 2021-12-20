from canaille.models import Group
from canaille.models import User


def test_no_group(app, slapd_connection):
    with app.app_context():
        assert Group.available_groups(conn=slapd_connection) == []


def test_set_groups(app, slapd_connection, user, foo_group, bar_group):
    with app.app_context():
        Group.ldap_object_attributes(conn=slapd_connection)
        User.ldap_object_attributes(conn=slapd_connection)

        user = User.get(dn=user.dn, conn=slapd_connection)
        user.load_groups(conn=slapd_connection)
        assert set(Group.available_groups(conn=slapd_connection)) == {
            ("foo", foo_group.dn),
            ("bar", bar_group.dn),
        }
        foo_dns = {g.dn for g in foo_group.get_members(conn=slapd_connection)}
        assert user.dn in foo_dns
        assert user.groups[0].dn == foo_group.dn

        user.set_groups([foo_group, bar_group], conn=slapd_connection)

        bar_dns = {g.dn for g in bar_group.get_members(conn=slapd_connection)}
        assert user.dn in bar_dns
        assert user.groups[1].dn == bar_group.dn

        user.set_groups([foo_group], conn=slapd_connection)

        foo_dns = {g.dn for g in foo_group.get_members(conn=slapd_connection)}
        bar_dns = {g.dn for g in bar_group.get_members(conn=slapd_connection)}
        assert user.dn in foo_dns
        assert user.dn not in bar_dns


def test_moderator_can_create_edit_and_delete_group(
    testclient, slapd_connection, logged_moderator, foo_group
):
    # The group does not exist
    res = testclient.get("/groups", status=200)
    with testclient.app.app_context():
        assert Group.get("bar", conn=slapd_connection) is None
        assert Group.get("foo", conn=slapd_connection) == foo_group
    assert "bar" not in res.text
    assert "foo" in res.text

    # Fill the form for a new group
    res = testclient.get("/groups/add", status=200)
    res.form["name"] = "bar"
    res.form["description"] = "yolo"

    # Group has been created
    res = res.form.submit(status=302).follow(status=200)

    with testclient.app.app_context():
        bar_group = Group.get("bar", conn=slapd_connection)
        assert bar_group.name == "bar"
        assert bar_group.description == ["yolo"]
        assert [
            member.dn for member in bar_group.get_members(conn=slapd_connection)
        ] == [
            logged_moderator.dn
        ]  # Group cannot be empty so creator is added in it
    assert "bar" in res.text

    # Group name can not be edited
    res = testclient.get("/groups/bar", status=200)
    res.form["name"] = "bar2"
    res.form["description"] = ["yolo2"]

    res = res.form.submit(name="action", value="edit", status=200)

    with testclient.app.app_context():
        bar_group = Group.get("bar", conn=slapd_connection)
        assert bar_group.name == "bar"
        assert bar_group.description == ["yolo2"]
        assert Group.get("bar2", conn=slapd_connection) is None
        members = bar_group.get_members(conn=slapd_connection)
        for member in members:
            assert member.name in res.text

    # Group is deleted
    res = res.form.submit(name="action", value="delete", status=302).follow(status=200)
    with testclient.app.app_context():
        assert Group.get("bar", conn=slapd_connection) is None
    assert "The group bar has been sucessfully deleted" in res.text


def test_cannot_create_already_existing_group(
    testclient, slapd_connection, logged_moderator, foo_group
):
    res = testclient.post("/groups/add", {"name": "foo"}, status=200)

    assert "Group creation failed." in res
    assert "The group &#39;foo&#39; already exists" in res


def test_simple_user_cannot_view_or_edit_groups(
    testclient, slapd_connection, logged_user, foo_group
):
    testclient.get("/groups", status=403)
    testclient.get("/groups/add", status=403)
    testclient.get("/groups/foo", status=403)


def test_get_members_filters_non_existent_user(
    testclient, slapd_connection, logged_moderator, foo_group, user
):
    # an LDAP group can be inconsistent by containing members which doesn't exist
    with testclient.app.app_context():
        non_existent_user_dn = user.dn.replace(user.name, "yolo")
        foo_group.member = foo_group.member + [non_existent_user_dn]
        foo_group.save(conn=slapd_connection)

    with testclient.app.app_context():
        foo_members = foo_group.get_members(conn=slapd_connection)

    assert foo_group.member == [user.dn, non_existent_user_dn]
    assert len(foo_members) == 1
    assert foo_members[0].dn == user.dn

    testclient.get("/groups/foo", status=200)
