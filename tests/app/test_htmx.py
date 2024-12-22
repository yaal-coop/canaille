def test_render_htmx(testclient, logged_admin, foo_group):
    """Test that partial templates are used for HTMX requests."""
    res = testclient.get("/groups")
    assert res.template == "core/groups.html"

    res = testclient.get("/groups", headers={"HX-Request": "true"})
    assert res.template == "core/partial/groups.html"

    res = testclient.get(f"/groups/{foo_group.display_name}")
    assert res.template == "core/group.html"

    res = testclient.get(
        f"/groups/{foo_group.display_name}", headers={"HX-Request": "true"}
    )
    assert res.template == "core/partial/group-members.html"
