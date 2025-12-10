import pytest
from scim2_client.errors import SCIMResponseErrorObject
from scim2_models import PatchOp
from scim2_models import PatchOperation

Op = PatchOperation.Op


def test_patch_user_replace_simple_attribute(app, backend, user, scim_client):
    """Test PATCH operation to replace a simple user attribute."""
    assert user.given_name == "John"
    assert backend.check_user_password(user, "correct horse battery staple")[0]

    scim_client.discover()
    User = scim_client.get_resource_model("User")
    op = PatchOperation(op=Op.replace_, path="title", value="Senior Developer")
    response_user = scim_client.modify(User, user.id, PatchOp[User](operations=[op]))

    assert response_user.title == "Senior Developer"

    backend.reload(user)
    assert user.title == "Senior Developer"
    assert user.given_name == "John"
    assert backend.check_user_password(user, "correct horse battery staple")[0]


def test_patch_user_activate_deactivate(app, backend, user, scim_client):
    """Test PATCH operation to replace a boolean attribute."""
    assert user.given_name == "John"
    assert backend.check_user_password(user, "correct horse battery staple")[0]

    scim_client.discover()
    User = scim_client.get_resource_model("User")

    op = PatchOperation(op=Op.replace_, path="active", value=False)
    response_user = scim_client.modify(User, user.id, PatchOp[User](operations=[op]))

    assert response_user.active is False

    backend.reload(user)
    assert user.lock_date
    assert user.given_name == "John"

    op = PatchOperation(op=Op.replace_, path="active", value=True)
    response_user = scim_client.modify(User, user.id, PatchOp[User](operations=[op]))

    assert response_user.active is True

    backend.reload(user)
    assert not user.lock_date
    assert user.given_name == "John"
    assert backend.check_user_password(user, "correct horse battery staple")[0]


def test_patch_replace_user_password(app, backend, user, scim_client):
    """Test PATCH operation to replace user passwords."""
    assert backend.check_user_password(user, "correct horse battery staple")[0]

    scim_client.discover()
    User = scim_client.get_resource_model("User")
    op = PatchOperation(
        op=Op.replace_, path="password", value="incorrect horse battery staple"
    )
    scim_client.modify(User, user.id, PatchOp[User](operations=[op]))

    backend.reload(user)
    assert backend.check_user_password(user, "incorrect horse battery staple")[0]


def test_patch_delete_user_password(app, backend, user, scim_client):
    """Test PATCH operation to delete user passwords."""
    assert backend.check_user_password(user, "correct horse battery staple")[0]

    scim_client.discover()
    User = scim_client.get_resource_model("User")
    op = PatchOperation(op=Op.remove, path="password")
    scim_client.modify(User, user.id, PatchOp[User](operations=[op]))

    backend.reload(user)
    assert not backend.check_user_password(user, "correct horse battery staple")[0]


def test_patch_user_add_email(app, backend, user, scim_client):
    """Test PATCH operation to add an email to a user."""
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    op = PatchOperation(
        op=Op.add, path="emails", value=[{"value": "newemail@example.com"}]
    )
    response_user = scim_client.modify(User, user.id, PatchOp[User](operations=[op]))

    email_values = [email.value for email in response_user.emails]
    assert "newemail@example.com" in email_values

    backend.reload(user)
    assert "newemail@example.com" in user.emails


def test_patch_user_remove_attribute(app, backend, user, scim_client):
    """Test PATCH operation to remove an attribute from a user."""
    user.title = "Manager"
    backend.save(user)

    scim_client.discover()
    User = scim_client.get_resource_model("User")
    op = PatchOperation(op=Op.remove, path="title")
    response_user = scim_client.modify(User, user.id, PatchOp[User](operations=[op]))

    assert response_user.title is None

    backend.reload(user)
    assert user.title is None


def test_patch_user_multiple_operations(app, backend, user, scim_client):
    """Test PATCH with multiple operations in a single request."""
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    ops = [
        PatchOperation(op=Op.replace_, path="title", value="CTO"),
        PatchOperation(op=Op.add, path="preferredLanguage", value="en-US"),
    ]
    response_user = scim_client.modify(User, user.id, PatchOp[User](operations=ops))

    assert response_user.title == "CTO"
    assert response_user.preferred_language == "en-US"

    backend.reload(user)
    assert user.title == "CTO"
    assert user.preferred_language == "en-US"


def test_patch_group_replace_members(
    app, backend, foo_group, user, moderator, scim_client
):
    """Test PATCH operation to replace members in a group."""
    foo_group.members = [user]
    backend.save(foo_group)

    scim_client.discover()
    Group = scim_client.get_resource_model("Group")
    op = PatchOperation(
        op=Op.replace_,
        path="members",
        value=[{"value": moderator.id, "display": moderator.display_name}],
    )
    response_group = scim_client.modify(
        Group, foo_group.id, PatchOp[Group](operations=[op])
    )

    member_ids = [member.value for member in response_group.members]
    assert moderator.identifier in member_ids
    assert user.id not in member_ids

    backend.reload(foo_group)
    member_ids_persisted = [member.identifier for member in foo_group.members]
    assert moderator.identifier in member_ids_persisted
    assert user.identifier not in member_ids_persisted


def test_patch_group_add_invalid_member(app, backend, foo_group, user, scim_client):
    """Test PATCH operation to add a member to a group."""
    foo_group.members = [user]
    backend.save(foo_group)

    scim_client.discover()
    Group = scim_client.get_resource_model("Group")
    op = PatchOperation(
        op=Op.add,
        path="members",
        value=[{"value": "invalid", "display": "http://invalid"}],
    )
    response_group = scim_client.modify(
        Group, foo_group.id, PatchOp[Group](operations=[op])
    )

    member_ids = [member.value for member in response_group.members]
    assert member_ids == [user.identifier]


def test_patch_group_add_member(app, backend, foo_group, user, moderator, scim_client):
    """Test PATCH operation to add a member to a group."""
    foo_group.members = [user]
    backend.save(foo_group)

    scim_client.discover()
    Group = scim_client.get_resource_model("Group")
    op = PatchOperation(
        op=Op.add,
        path="members",
        value=[{"value": moderator.id, "display": moderator.display_name}],
    )
    response_group = scim_client.modify(
        Group, foo_group.id, PatchOp[Group](operations=[op])
    )

    member_ids = [member.value for member in response_group.members]
    assert user.identifier in member_ids
    assert moderator.identifier in member_ids

    backend.reload(foo_group)
    member_ids_persisted = [member.identifier for member in foo_group.members]
    assert user.identifier in member_ids_persisted
    assert moderator.identifier in member_ids_persisted


def test_patch_invalid_operation(app, backend, user, scim_client):
    """Test PATCH with an invalid operation type."""
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    patch_op_dict = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "invalid_operation", "path": "title", "value": "Test"}],
    }

    with pytest.raises(SCIMResponseErrorObject):
        scim_client.modify(User, user.id, patch_op_dict, check_request_payload=False)


def test_patch_user_no_modifications(app, backend, user, scim_client):
    """Test PATCH user that results in no modifications."""
    user.title = "Developer"
    backend.save(user)

    scim_client.discover()
    User = scim_client.get_resource_model("User")
    op = PatchOperation(op=Op.replace_, path="title", value="Developer")
    response_user = scim_client.modify(User, user.id, PatchOp[User](operations=[op]))

    assert response_user.title == "Developer"

    backend.reload(user)
    assert user.title == "Developer"


def test_patch_group_no_modification(app, backend, foo_group, user, scim_client):
    """Test PATCH user that results in no modifications."""
    foo_group.members = [user]
    backend.save(foo_group)

    scim_client.discover()
    Group = scim_client.get_resource_model("Group")
    op = PatchOperation(op=Op.replace_, path="displayName", value="foo")
    response_group = scim_client.modify(
        Group, foo_group.id, PatchOp[Group](operations=[op])
    )

    member_ids = [member.value for member in response_group.members]
    assert user.identifier in member_ids
