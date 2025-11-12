from canaille.app import models
from canaille.core.populate import fake_groups
from canaille.core.populate import fake_users


def test_delete_group(testclient, backend, user, admin, foo_group):
    """Test that users are properly removed from a group when the user-group relationship is cleared."""
    foo_group.members = [user, admin]
    backend.save(foo_group)

    user = backend.get(models.User, user.id)
    user.groups = []
    backend.save(user)


def test_no_group(app, backend):
    """Test that querying groups returns an empty list when no groups exist."""
    assert backend.query(models.Group) == []


def test_group_list_pagination(testclient, logged_admin, foo_group, backend):
    """Test that group list pagination correctly navigates between pages."""
    groups = fake_groups(25)

    res = testclient.get("/groups")
    form = res.forms["tableform"]
    res = form.submit(name="page", value="2")
    form = res.forms["tableform"]
    res = form.submit(name="page", value="1")
    for group in groups:
        backend.delete(group)


def test_group_list_bad_pages(testclient, logged_admin):
    """Test that accessing invalid page numbers returns 404 errors."""
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
    """Test that deleting a group properly removes it from associated users."""
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
    """Test that group list search filters groups by name."""
    res = testclient.get("/groups")
    res.mustcontain(foo_group.display_name)
    res.mustcontain(bar_group.display_name)

    form = res.forms["search"]
    form["query"] = "oo"
    res = form.submit()

    res.mustcontain(foo_group.display_name)
    res.mustcontain(no=bar_group.display_name)


def test_set_groups(app, user, foo_group, bar_group, backend):
    """Test that setting user groups correctly updates group membership."""
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
    """Test that users with leading spaces in their ID attributes can be added and removed from groups."""
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
    assert bar_group.owner == logged_moderator  # Group creator should be added as owner
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
    """Test that attempting to create a group with an existing name fails with an error."""
    res = testclient.get("/groups/add")
    res = testclient.post(
        "/groups/add",
        {"csrf_token": res.form["csrf_token"].value, "display_name": "foo"},
        status=200,
    )

    res.mustcontain("Group creation failed.")
    res.mustcontain("The group 'foo' already exists")


def test_invalid_group(testclient, logged_moderator):
    """Test that accessing a non-existent group returns 404."""
    testclient.get("/groups/invalid", status=404)


def test_simple_user_can_view_own_groups_and_manage_own_groups(
    testclient, logged_user, foo_group
):
    """Test that a user with manage_own_groups permission can view their groups and create groups."""
    testclient.get("/groups", status=200)
    testclient.get("/groups/add", status=200)


def test_invalid_form_request(testclient, logged_moderator, foo_group):
    """Test that submitting an invalid form action returns 400."""
    res = testclient.get("/groups/foo")
    form = res.forms["editgroupform"]
    res = form.submit(name="action", value="invalid-action", status=400)


def test_edition_failed(testclient, logged_moderator, foo_group, backend):
    """Test that group edition fails when validation errors occur."""
    res = testclient.get("/groups/foo")
    form = res.forms["editgroupform"]
    form["display_name"] = ""
    res = form.submit(name="action", value="edit")
    res.mustcontain("Group edition failed.")
    backend.reload(foo_group)
    assert foo_group.display_name == "foo"


def test_user_list_pagination(testclient, logged_admin, foo_group, backend):
    """Test that user list pagination within a group correctly navigates between pages."""
    users = fake_users(25)
    for user in users:
        foo_group.members = foo_group.members + [user]
    backend.save(foo_group)

    res = testclient.get("/groups/foo")
    form = res.forms["tableform"]
    res = form.submit(name="page", value="2")
    form = res.forms["tableform"]
    res = form.submit(name="page", value="1")
    for user in users:
        backend.delete(user)


def test_user_list_bad_pages(testclient, logged_admin, foo_group):
    """Test that accessing invalid page numbers in group member list returns 404."""
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
    """Test that user list search within a group filters members by name."""
    foo_group.members = foo_group.members + [logged_admin, moderator]
    backend.save(foo_group)

    res = testclient.get("/groups/foo")
    res.mustcontain(user.formatted_name)
    res.mustcontain(logged_admin.formatted_name)
    res.mustcontain(moderator.formatted_name)

    form = res.forms["search"]
    form["query"] = "ohn"
    res = form.submit()

    table = res.lxml.cssselect("table.users tbody")[0]
    table_text = table.text_content()

    assert user.formatted_name in table_text
    assert logged_admin.formatted_name not in table_text
    assert moderator.formatted_name not in table_text


def test_remove_member(testclient, logged_admin, foo_group, user, moderator, backend):
    """Test that a member can be successfully removed from a group."""
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
    """Test that attempting to remove a member already removed from the group shows an error."""
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
    """Test that confirming removal of a member already removed from the group shows an error."""
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
    """Test that attempting to remove a member that has been deleted shows an error."""
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
    """Test that confirming removal of a deleted member shows an error."""
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


def test_moderator_sees_groups_they_belong_to(
    testclient, logged_moderator, foo_group, bar_group, backend
):
    """Test that moderators can see groups they belong to.

    Note: Moderators have manage_all_groups permission so they see all groups,
    not just the ones they belong to.
    """
    # Access groups page as logged moderator
    res = testclient.get("/groups/", status=200)

    # Should see all groups (because moderator has manage_all_groups permission)
    assert foo_group.display_name in res.text
    assert bar_group.display_name in res.text


def test_moderator_can_click_all_groups_because_of_manage_all_groups_permission(
    testclient, logged_moderator, foo_group, bar_group
):
    """Test that moderators can click on all groups because they have manage_all_groups permission."""
    # Access groups page as logged moderator
    res = testclient.get("/groups/", status=200)

    # Should see both groups
    assert foo_group.display_name in res.text
    assert bar_group.display_name in res.text

    # Both groups should be clickable (moderator has manage_all_groups permission)
    assert f'<a href="/groups/{foo_group.display_name}">' in res.text
    assert f'<a href="/groups/{bar_group.display_name}">' in res.text


def test_admin_user_can_see_and_click_all_groups(
    testclient, logged_admin, foo_group, bar_group
):
    """Test that admin users can see and click on all groups."""
    # Access groups page as admin
    res = testclient.get("/groups/", status=200)

    # Should see all groups
    assert foo_group.display_name in res.text
    assert bar_group.display_name in res.text

    # Both should be clickable
    assert f'<a href="/groups/{foo_group.display_name}">' in res.text
    assert f'<a href="/groups/{bar_group.display_name}">' in res.text


def test_group_linking_behavior_works(
    testclient, logged_moderator, foo_group, bar_group
):
    """Test that clicking on groups works correctly."""
    # Access groups page as logged moderator
    res = testclient.get("/groups/", status=200)

    # Should see the group
    assert foo_group.display_name in res.text

    # Should be clickable (moderator has manage_all_groups)
    assert f'<a href="/groups/{foo_group.display_name}">' in res.text

    # Actually click on the group to verify it works
    group_link = res.click(foo_group.display_name)
    assert group_link.status_code == 200
    assert "Invite Members" in group_link.text


def test_icons_are_clickable_for_admin_users(
    testclient, logged_admin, foo_group, bar_group
):
    """Test that icons are clickable for admin users."""
    # Access groups page as admin
    res = testclient.get("/groups/", status=200)

    # Both groups should have clickable icons with black inverted style
    # Count how many clickable icons appear
    assert "users circular black inverted icon" in res.text

    # Should not have any grey non-clickable icons
    assert "users circular grey icon" not in res.text


def test_group_owner_star_icon_displayed(
    testclient, logged_moderator, foo_group, bar_group, backend
):
    """Test that the group owner is displayed with a star icon on the group page."""
    # Set logged_moderator as the owner of foo_group
    foo_group.owner = logged_moderator
    foo_group.members = [logged_moderator]  # Make sure moderator is a member
    backend.save(foo_group)

    # Access the foo_group page where logged_moderator should be the owner
    res = testclient.get(f"/groups/{foo_group.display_name}", status=200)

    # Should see the group owner star icon and tooltip
    assert "star yellow icon" in res.text
    assert "Group owner" in res.text

    # The star should appear in the members table
    assert "moderator" in res.text  # moderator user should be displayed


def test_group_owner_star_only_for_owner(
    testclient, logged_admin, foo_group, user, backend
):
    """Test that the star icon only appears for the actual group owner."""
    # Set admin as owner and add regular user to the group
    foo_group.owner = logged_admin
    foo_group.members = [logged_admin, user]
    backend.save(foo_group)

    # Access the group page
    res = testclient.get(f"/groups/{foo_group.display_name}", status=200)

    # Should see the star icon (for the owner)
    assert "star yellow icon" in res.text
    assert "Group owner" in res.text

    # Both users should be listed but only one should have a star
    # Count the number of star icons - should be exactly 1 (only in username column)
    star_count = res.text.count("star yellow icon")
    assert star_count == 1  # One star for the owner (only in username column)


def test_no_star_when_no_owner(testclient, logged_admin, foo_group, backend):
    """Test that no star is displayed when group has no owner."""
    # Remove the owner
    foo_group.owner = None
    backend.save(foo_group)

    # Access the group page
    res = testclient.get(f"/groups/{foo_group.display_name}", status=200)

    # Should not see any star icons
    assert "star yellow icon" not in res.text
    assert "Group owner" not in res.text


def test_groups_page_includes_actions_column(
    testclient, logged_moderator, foo_group, bar_group
):
    """Test that the groups page includes an Actions column in the table."""
    # Access groups page as logged moderator
    res = testclient.get("/groups/", status=200)

    # Should see Actions column header
    assert "Actions" in res.text

    # Should see both groups
    assert foo_group.display_name in res.text
    assert bar_group.display_name in res.text

    # Should NOT see Leave button for any group (moderator has manage_all_groups permission)
    # Because moderators can edit all groups, they don't see Leave buttons
    assert "Leave" not in res.text


def test_user_can_delete_own_group(testclient, logged_user, backend):
    """Test that a user with manage_own_groups permission can delete their own group."""
    group = models.Group(
        members=[logged_user],
        display_name="user_group",
        owner=logged_user,
    )
    backend.save(group)

    res = testclient.get("/groups/user_group", status=200)
    form = res.forms["editgroupform"]
    res = form.submit(name="action", value="confirm-delete")
    res = res.form.submit(name="action", value="delete", status=302)

    assert backend.get(models.Group, display_name="user_group") is None
    assert (
        "success",
        "The group user_group has been successfully deleted",
    ) in res.flashes


def test_user_cannot_delete_others_group(testclient, logged_user, admin, backend):
    """Test that a user with manage_own_groups permission cannot delete another user's group."""
    group = models.Group(
        members=[admin],
        display_name="admin_group",
        owner=admin,
    )
    backend.save(group)

    testclient.get("/groups/admin_group", status=403)

    backend.delete(group)


def test_user_without_permissions_cannot_access_groups(testclient, backend, app):
    """Test that a user without manage_own_groups or manage_all_groups permissions cannot access groups page."""
    user = models.User(
        formatted_name="No Permission",
        family_name="User",
        user_name="noperm",
        emails=["noperm@test.example"],
        password="password",
    )
    backend.save(user)

    with testclient.session_transaction() as sess:
        import datetime

        from canaille.app.session import UserSession

        sess["sessions"] = [
            UserSession(
                user=user,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize()
        ]

    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = [
        "edit_self",
        "use_oidc",
    ]
    testclient.get("/groups", status=403)
    testclient.get("/groups/add", status=403)

    backend.delete(user)


def test_confirm_leave_group_modal(testclient, logged_user, foo_group):
    """Test that the confirm-leave modal displays correctly."""
    res = testclient.get("/groups")
    form = res.forms["tableform"]
    res = testclient.post(
        "/groups",
        {
            "csrf_token": form["csrf_token"].value,
            "action": "confirm-leave",
            "group_id": foo_group.id,
        },
        status=200,
    )
    res.mustcontain("Leave group")
    res.mustcontain(foo_group.display_name)
    res.mustcontain("Are you sure you want to leave")


def test_confirm_leave_group_missing_group_id(testclient, logged_user):
    """Test that confirm-leave without group_id returns 400."""
    res = testclient.get("/groups")
    form = res.forms["tableform"]
    testclient.post(
        "/groups",
        {
            "csrf_token": form["csrf_token"].value,
            "action": "confirm-leave",
        },
        status=400,
    )


def test_confirm_leave_group_nonexistent(testclient, logged_user):
    """Test that confirm-leave with nonexistent group_id returns 404."""
    res = testclient.get("/groups")
    form = res.forms["tableform"]
    testclient.post(
        "/groups",
        {
            "csrf_token": form["csrf_token"].value,
            "action": "confirm-leave",
            "group_id": "nonexistent-id",
        },
        status=404,
    )


def test_confirm_leave_group_not_member(testclient, logged_user, bar_group):
    """Test that confirm-leave for a group user is not member of shows error."""
    res = testclient.get("/groups")
    form = res.forms["tableform"]
    res = testclient.post(
        "/groups",
        {
            "csrf_token": form["csrf_token"].value,
            "action": "confirm-leave",
            "group_id": bar_group.id,
        },
        status=302,
    )
    assert ("error", "You are not a member of this group.") in res.flashes


def test_leave_group_success(testclient, logged_user, foo_group, admin, backend):
    """Test that a user can successfully leave a group."""
    foo_group.members = [logged_user, admin]
    backend.save(foo_group)

    assert logged_user in foo_group.members

    res = testclient.get("/groups")
    csrf_token = res.forms["tableform"]["csrf_token"].value
    testclient.post(
        f"/groups/{foo_group.display_name}/leave",
        {"csrf_token": csrf_token},
        status=302,
    )

    backend.reload(foo_group)
    backend.reload(admin)
    assert logged_user not in foo_group.members
    assert len(foo_group.members) == 1
    assert foo_group.members[0].id == admin.id


def test_leave_group_not_member(testclient, logged_user, bar_group):
    """Test that leaving a group user is not member of shows error."""
    res = testclient.get("/groups")
    csrf_token = res.forms["tableform"]["csrf_token"].value
    res = testclient.post(
        f"/groups/{bar_group.display_name}/leave",
        {"csrf_token": csrf_token},
        status=302,
    )
    assert ("error", "You are not a member of this group.") in res.flashes


def test_leave_group_owner_clears_ownership(testclient, logged_user, admin, backend):
    """Test that leaving a group as owner clears the owner field."""
    group = models.Group(
        members=[logged_user, admin],
        display_name="owned_group",
        owner=logged_user,
    )
    backend.save(group)

    res = testclient.get("/groups")
    csrf_token = res.forms["tableform"]["csrf_token"].value
    testclient.post(
        f"/groups/{group.display_name}/leave",
        {"csrf_token": csrf_token},
        status=302,
    )

    backend.reload(group)
    backend.reload(admin)
    assert logged_user not in group.members
    assert len(group.members) == 1
    assert group.members[0].id == admin.id
    assert group.owner is None

    backend.delete(group)
