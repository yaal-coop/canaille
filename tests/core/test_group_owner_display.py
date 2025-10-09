


def test_group_owner_star_icon_displayed(testclient, logged_moderator, foo_group, bar_group, backend):
    """Test that the group owner is displayed with a star icon on the group page."""
    # Set logged_moderator as the owner of foo_group
    foo_group.owner = logged_moderator
    foo_group.members = [logged_moderator]  # Make sure moderator is a member
    backend.save(foo_group)

    # Access the foo_group page where logged_moderator should be the owner
    res = testclient.get(f"/groups/{foo_group.display_name}", status=200)

    # Should see the group owner star icon and tooltip
    assert 'star yellow icon' in res.text
    assert 'Group owner' in res.text

    # The star should appear in the members table
    assert 'moderator' in res.text  # moderator user should be displayed


def test_group_owner_star_only_for_owner(testclient, logged_admin, foo_group, user, backend):
    """Test that the star icon only appears for the actual group owner."""
    # Set admin as owner and add regular user to the group
    foo_group.owner = logged_admin
    foo_group.members = [logged_admin, user]
    backend.save(foo_group)

    # Access the group page
    res = testclient.get(f"/groups/{foo_group.display_name}", status=200)

    # Should see the star icon (for the owner)
    assert 'star yellow icon' in res.text
    assert 'Group owner' in res.text

    # Both users should be listed but only one should have a star
    # Count the number of star icons - should be exactly 1 (only in username column)
    star_count = res.text.count('star yellow icon')
    assert star_count == 1  # One star for the owner (only in username column)


def test_no_star_when_no_owner(testclient, logged_admin, foo_group, backend):
    """Test that no star is displayed when group has no owner."""
    # Remove the owner
    foo_group.owner = None
    backend.save(foo_group)

    # Access the group page
    res = testclient.get(f"/groups/{foo_group.display_name}", status=200)

    # Should not see any star icons
    assert 'star yellow icon' not in res.text
    assert 'Group owner' not in res.text