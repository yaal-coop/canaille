def test_group_permissions(testclient, user, foo_group):
    assert not user.can_manage_users

    testclient.app.config["ACL"]["ADMIN"]["FILTER"] = {"groups": foo_group.id}
    user.reload()

    assert user.can_manage_users
