def test_group_permissions_by_id(testclient, user, foo_group, backend):
    assert not user.can_manage_users

    testclient.app.config["CANAILLE"]["ACL"]["ADMIN"]["FILTER"] = {
        "groups": foo_group.id
    }
    backend.reload(user)

    assert user.can_manage_users


def test_group_permissions_by_display_name(testclient, user, foo_group, backend):
    assert not user.can_manage_users

    testclient.app.config["CANAILLE"]["ACL"]["ADMIN"]["FILTER"] = {
        "groups": foo_group.display_name
    }
    backend.reload(user)

    assert user.can_manage_users


def test_invalid_group_permission(testclient, user, foo_group, backend):
    assert not user.can_manage_users

    testclient.app.config["CANAILLE"]["ACL"]["ADMIN"]["FILTER"] = {"groups": "invalid"}
    backend.reload(user)

    assert not user.can_manage_users
