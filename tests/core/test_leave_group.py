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

    # Should NOT see Leave button for any group (moderator has manage_groups permission)
    # Because moderators can edit all groups, they don't see Leave buttons
    assert "Leave" not in res.text
