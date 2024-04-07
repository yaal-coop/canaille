def test_group_permissions_by_dn(testclient, user, foo_group):
    assert not user.can_manage_users

    testclient.app.config["CANAILLE"]["ACL"]["ADMIN"]["FILTER"] = {
        "groups": foo_group.dn
    }
    user.reload()

    assert user.can_manage_users


def test_group_permissions_str(testclient, user, foo_group):
    assert not user.can_manage_users

    testclient.app.config["CANAILLE"]["ACL"]["ADMIN"]["FILTER"] = (
        f"memberOf={foo_group.dn}"
    )
    user.reload()

    assert user.can_manage_users
