from unittest import mock

from scim2_models import BulkOperation
from scim2_models import BulkRequest
from scim2_models import PatchOp
from scim2_models import PatchOperation

from canaille.app import models


def test_bulk_operation_create_user(backend, scim_client):
    alice = backend.get(models.User, user_name="Alice")
    assert alice is None

    scim_client.discover()
    User = scim_client.get_resource_model("User")
    request = BulkRequest(
        operations=[
            BulkOperation(
                method="POST",
                path="/Users",
                bulk_id="qwerty",
                data=User(
                    user_name="Alice",
                    name={"formatted": "Alice Jones", "family_name": "Jones"},
                    active=True,
                ),
            ),
        ]
    )
    response = scim_client.bulk(request)
    assert response.operations[0].location == "http://canaille.test/scim/v2/Users/Alice"
    assert response.operations[0].status == 201

    alice = backend.get(models.User, user_name="Alice")
    assert alice is not None
    assert alice.user_name == "Alice"

    backend.delete(alice)


def test_bulk_operation_create_group(backend, scim_client, user):
    groupe = backend.get(models.Group, display_name="Le Groupe")
    assert groupe is None

    scim_client.discover()
    Group = scim_client.get_resource_model("Group")

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="POST",
                path="/Groups",
                bulk_id="qwerty",
                data=Group(
                    display_name="Le Groupe",
                    members=[{"value": user.id, "ref": "Users/example"}],
                ),
            ),
        ]
    )
    response = scim_client.bulk(request)
    assert (
        response.operations[0].location
        == "http://canaille.test/scim/v2/Groups/Le Groupe"
    )
    assert response.operations[0].status == 201

    groupe = backend.get(models.Group, display_name="Le Groupe")
    assert groupe is not None
    assert groupe.display_name == "Le Groupe"

    backend.delete(groupe)


def test_bulk_operation_post_validation_error(scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    request = BulkRequest(
        operations=[
            BulkOperation(
                method="POST",
                path="/Users",
                bulk_id="qwerty",
                data=User(user_name="Alice"),  # user is missing required fields
            ),
        ]
    )
    response = scim_client.bulk(request)
    assert response.operations[0].status == 400
    assert response.operations[0].location is None


def test_bulk_operation_post_database_error(scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    request = BulkRequest(
        operations=[
            BulkOperation(
                method="POST",
                path="/Users",
                bulk_id="qwerty",
                data=User(
                    user_name="Alice",
                    name={"formatted": "Alice Jones", "family_name": "Jones"},
                    active=True,
                ),
            ),
        ]
    )
    with mock.patch(
        "canaille.backends.Backend.instance.save",
        side_effect=Exception("Database error"),
    ):
        response = scim_client.bulk(request)
    assert response.operations[0].status == 500
    assert response.operations[0].location is None


def test_bulk_operation_replace_user(backend, scim_client, user):
    scim_client.discover()
    User = scim_client.get_resource_model("User")

    user_scim = scim_client.query(User, "user")
    assert user_scim.display_name == "Johnny"

    user_scim.display_name = "Changed"

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="PUT",
                path="/Users/user",
                data=user_scim,
            ),
        ]
    )
    response = scim_client.bulk(request)
    assert response.operations[0].status == 200
    assert response.operations[0].location == "http://canaille.test/scim/v2/Users/user"

    backend.reload(user)
    assert user.display_name == "Changed"


def test_bulk_operation_replace_user_not_found(scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="PUT",
                path="/Users/invalid",
                data=User(
                    user_name="invalid",
                ),
            ),
        ]
    )
    response = scim_client.bulk(request)
    assert response.operations[0].status == 404
    assert response.operations[0].response["detail"] == "User not found"
    assert (
        response.operations[0].location == "http://canaille.test/scim/v2/Users/invalid"
    )


def test_bulk_operation_replace_user_validation_error(scim_client, user):
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    user_scim = scim_client.query(User, "user")
    user_scim.active = None  # user is now missing required field

    request = BulkRequest(
        operations=[
            BulkOperation(method="PUT", path="/Users/user", data=user_scim),
        ]
    )
    response = scim_client.bulk(request)
    assert response.operations[0].status == 400
    assert response.operations[0].location == "http://canaille.test/scim/v2/Users/user"


def test_bulk_operation_replace_user_database_error(scim_client, user):
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    user_scim = scim_client.query(User, "user")

    request = BulkRequest(
        operations=[
            BulkOperation(method="PUT", path="/Users/user", data=user_scim),
        ]
    )
    with mock.patch(
        "canaille.backends.Backend.instance.save",
        side_effect=Exception("Database error"),
    ):
        response = scim_client.bulk(request)
    assert response.operations[0].status == 500
    assert response.operations[0].location == "http://canaille.test/scim/v2/Users/user"


def test_bulk_operation_replace_group(backend, scim_client, foo_group, user, admin):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")

    group_scim = scim_client.query(Group, "foo")

    assert group_scim.members[0].value == "user"

    group_scim.members = [
        {"value": "admin", "ref": "User/admin"},
    ]

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="PUT",
                path="/Groups/foo",
                data=group_scim,
            ),
        ]
    )
    response = scim_client.bulk(request)
    assert response.operations[0].status == 200
    assert response.operations[0].location == "http://canaille.test/scim/v2/Groups/foo"

    backend.reload(foo_group)
    assert foo_group.members == [admin]


def test_bulk_operation_replace_group_not_found(scim_client):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="PUT",
                path="/Groups/invalid",
                data=Group(
                    display_name="invalid",
                ),
            )
        ]
    )

    response = scim_client.bulk(request)
    assert response.operations[0].status == 404
    assert response.operations[0].response["detail"] == "Group not found"
    assert (
        response.operations[0].location == "http://canaille.test/scim/v2/Groups/invalid"
    )


def test_bulk_operation_replace_group_validation_error(scim_client, foo_group):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")
    group_scim = scim_client.query(Group, "foo")
    group_scim.members = None  # group is now missing required field

    request = BulkRequest(
        operations=[
            BulkOperation(method="PUT", path="/Groups/foo", data=group_scim),
        ]
    )
    response = scim_client.bulk(request)
    assert response.operations[0].status == 400
    assert response.operations[0].location == "http://canaille.test/scim/v2/Groups/foo"


def test_bulk_operation_replace_group_database_error(scim_client, foo_group):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")
    group_scim = scim_client.query(Group, "foo")

    request = BulkRequest(
        operations=[
            BulkOperation(method="PUT", path="/Groups/foo", data=group_scim),
        ]
    )
    with mock.patch(
        "canaille.backends.Backend.instance.save",
        side_effect=Exception("Database error"),
    ):
        response = scim_client.bulk(request)
    assert response.operations[0].status == 500
    assert response.operations[0].location == "http://canaille.test/scim/v2/Groups/foo"


def test_bulk_operation_modify_user(backend, scim_client, user):
    scim_client.discover()
    User = scim_client.get_resource_model("User")

    user_scim = scim_client.query(User, "user")
    assert user_scim.display_name == "Johnny"

    operation = PatchOperation(
        op=PatchOperation.Op.replace_, path="displayName", value="Updated Display Name"
    )
    patch_op = PatchOp[User](operations=[operation])

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="PATCH",
                path="/Users/user",
                data=patch_op,
            ),
        ]
    )

    response = scim_client.bulk(request)

    assert response.operations[0].status == 200

    backend.reload(user)
    assert user.display_name == "Updated Display Name"
    assert response.operations[0].location == "http://canaille.test/scim/v2/Users/user"


def test_bulk_operation_modify_user_not_found(scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")

    operation = PatchOperation(
        op=PatchOperation.Op.replace_, path="displayName", value="Updated Display Name"
    )
    patch_op = PatchOp[User](operations=[operation])

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="PATCH",
                path="/Users/invalid",
                data=patch_op,
            ),
        ]
    )

    response = scim_client.bulk(request)

    assert response.operations[0].status == 404
    assert (
        response.operations[0].location == "http://canaille.test/scim/v2/Users/invalid"
    )


def test_bulk_operation_modify_user_validation_error(scim_client, user):
    scim_client.discover()
    User = scim_client.get_resource_model("User")

    # operations shouldn't be none
    patch_op = PatchOp[User](operations=None)

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="PATCH",
                path="/Users/user",
                data=patch_op,
            ),
        ]
    )

    response = scim_client.bulk(request)
    assert response.operations[0].status == 400
    assert response.operations[0].location == "http://canaille.test/scim/v2/Users/user"


def test_bulk_operation_modify_user_database_error(scim_client, user):
    scim_client.discover()
    User = scim_client.get_resource_model("User")

    operation = PatchOperation(
        op=PatchOperation.Op.replace_, path="displayName", value="Updated Display Name"
    )
    patch_op = PatchOp[User](operations=[operation])

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="PATCH",
                path="/Users/user",
                data=patch_op,
            ),
        ]
    )

    with mock.patch(
        "canaille.backends.Backend.instance.save",
        side_effect=Exception("Database error"),
    ):
        response = scim_client.bulk(request)

    assert response.operations[0].status == 500
    assert response.operations[0].location == "http://canaille.test/scim/v2/Users/user"


def test_bulk_operation_modify_group(backend, scim_client, foo_group, admin):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")

    group_scim = scim_client.query(Group, "foo")
    assert group_scim.members[0].value == "user"

    operation = PatchOperation(
        op=PatchOperation.Op.replace_,
        path="members",
        value=[{"value": "admin", "ref": "Users/admin"}],
    )
    patch_op = PatchOp[Group](operations=[operation])

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="PATCH",
                path="/Groups/foo",
                data=patch_op,
            ),
        ]
    )

    response = scim_client.bulk(request)

    assert response.operations[0].status == 200
    assert response.operations[0].location == "http://canaille.test/scim/v2/Groups/foo"
    backend.reload(foo_group)
    assert foo_group.members == [admin]


def test_bulk_operation_modify_group_not_found(scim_client, admin):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")

    operation = PatchOperation(
        op=PatchOperation.Op.replace_,
        path="members",
        value=[{"value": "admin", "ref": "Users/admin"}],
    )
    patch_op = PatchOp[Group](operations=[operation])

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="PATCH",
                path="/Groups/invalid",
                data=patch_op,
            ),
        ]
    )

    response = scim_client.bulk(request)

    assert response.operations[0].status == 404
    assert (
        response.operations[0].location == "http://canaille.test/scim/v2/Groups/invalid"
    )


def test_bulk_operation_modify_group_validation_error(scim_client, foo_group):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")

    # operations shouldn't be none
    patch_op = PatchOp[Group](operations=None)

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="PATCH",
                path="/Groups/foo",
                data=patch_op,
            ),
        ]
    )

    response = scim_client.bulk(request)
    assert response.operations[0].status == 400
    assert response.operations[0].location == "http://canaille.test/scim/v2/Groups/foo"


def test_bulk_operation_modify_group_database_error(scim_client, foo_group, admin):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")

    operation = PatchOperation(
        op=PatchOperation.Op.replace_,
        path="members",
        value=[{"value": "admin", "ref": "Users/admin"}],
    )
    patch_op = PatchOp[Group](operations=[operation])

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="PATCH",
                path="/Groups/foo",
                data=patch_op,
            ),
        ]
    )

    with mock.patch(
        "canaille.backends.Backend.instance.save",
        side_effect=Exception("Database error"),
    ):
        response = scim_client.bulk(request)

    assert response.operations[0].status == 500
    assert response.operations[0].location == "http://canaille.test/scim/v2/Groups/foo"


def test_bulk_operation_delete_user(backend, scim_client, user):
    scim_client.discover()

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="DELETE",
                path="/Users/user",
            ),
        ]
    )

    response = scim_client.bulk(request)

    assert response.operations[0].status == 204
    assert response.operations[0].location == "http://canaille.test/scim/v2/Users/user"

    user = backend.get(models.User, user_name="user")
    assert user is None


def test_bulk_operation_delete_user_not_found(scim_client):
    scim_client.discover()

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="DELETE",
                path="/Users/invalid",
            ),
        ]
    )

    response = scim_client.bulk(request)

    assert response.operations[0].status == 404
    assert (
        response.operations[0].location == "http://canaille.test/scim/v2/Users/invalid"
    )


def test_bulk_operation_delete_user_database_error(scim_client, user):
    scim_client.discover()

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="DELETE",
                path="/Users/user",
            ),
        ]
    )

    with mock.patch(
        "canaille.backends.Backend.instance.delete",
        side_effect=Exception("Database error"),
    ):
        response = scim_client.bulk(request)

    assert response.operations[0].status == 500
    assert response.operations[0].location == "http://canaille.test/scim/v2/Users/user"


def test_bulk_operation_delete_group(backend, scim_client, foo_group):
    scim_client.discover()

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="DELETE",
                path="/Groups/foo",
            ),
        ]
    )

    response = scim_client.bulk(request)

    assert response.operations[0].status == 204
    assert response.operations[0].location == "http://canaille.test/scim/v2/Groups/foo"

    foo_group = backend.get(models.Group, display_name="foo")
    assert foo_group is None


def test_bulk_operation_delete_group_not_found(scim_client):
    scim_client.discover()

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="DELETE",
                path="/Groups/invalid",
            ),
        ]
    )

    response = scim_client.bulk(request)

    assert response.operations[0].status == 404
    assert (
        response.operations[0].location == "http://canaille.test/scim/v2/Groups/invalid"
    )


def test_bulk_operation_delete_group_database_error(scim_client, foo_group):
    scim_client.discover()

    request = BulkRequest(
        operations=[
            BulkOperation(
                method="DELETE",
                path="/Groups/foo",
            ),
        ]
    )

    with mock.patch(
        "canaille.backends.Backend.instance.delete",
        side_effect=Exception("Database error"),
    ):
        response = scim_client.bulk(request)

    assert response.operations[0].status == 500
    assert response.operations[0].location == "http://canaille.test/scim/v2/Groups/foo"
