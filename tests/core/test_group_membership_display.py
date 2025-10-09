def test_moderator_sees_groups_they_belong_to(
    testclient, logged_moderator, foo_group, bar_group, backend
):
    """Test that moderators can see groups they belong to.

    Note: Moderators have manage_groups permission so they see all groups,
    not just the ones they belong to.
    """
    # Access groups page as logged moderator
    res = testclient.get("/groups/", status=200)

    # Should see all groups (because moderator has manage_groups permission)
    assert foo_group.display_name in res.text
    assert bar_group.display_name in res.text


def test_moderator_can_click_all_groups_because_of_manage_groups_permission(
    testclient, logged_moderator, foo_group, bar_group
):
    """Test that moderators can click on all groups because they have manage_groups permission."""
    # Access groups page as logged moderator
    res = testclient.get("/groups/", status=200)

    # Should see both groups
    assert foo_group.display_name in res.text
    assert bar_group.display_name in res.text

    # Both groups should be clickable (moderator has manage_groups permission)
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

    # Should be clickable (moderator has manage_groups)
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
