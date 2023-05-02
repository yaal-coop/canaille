def test_group_permissions_by_id(testclient, user, foo_group):
    assert not user.can_manage_users

    testclient.app.config["ACL"]["ADMIN"]["FILTER"] = {"groups": foo_group.id}
    user.reload()

    assert user.can_manage_users


def test_group_permissions_by_display_name(testclient, user, foo_group):
    assert not user.can_manage_users

    testclient.app.config["ACL"]["ADMIN"]["FILTER"] = {"groups": foo_group.display_name}
    user.reload()

    assert user.can_manage_users
