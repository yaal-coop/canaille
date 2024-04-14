from canaille.app import models


def test_model_references_set_unsaved_object(
    testclient, logged_moderator, user, backend
):
    """LDAP groups can be inconsistent by containing members which doesn't
    exist."""
    group = models.Group(members=[user], display_name="foo")
    backend.save(group)
    backend.reload(user)

    non_existent_user = models.User(
        formatted_name="foo", family_name="bar", user_name="baz"
    )
    group.members = group.members + [non_existent_user]
    assert group.members == [user, non_existent_user]

    backend.save(group)
    assert group.members == [user, non_existent_user]

    backend.reload(group)
    assert group.members == [user]

    testclient.get("/groups/foo", status=200)

    backend.delete(group)
