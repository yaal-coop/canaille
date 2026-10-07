from unittest import mock

import pytest
from scim2_models import BulkOperation
from scim2_models import BulkRequest
from scim2_models import Context
from scim2_models import Error
from scim2_models import PatchOp
from scim2_models import PatchOperation

from canaille.app import models

pytestmark = pytest.mark.usefixtures("clean_backend")


def test_bulk_operation_create_user(backend, scim_client):
    alice = backend.get(models.User, user_name="Alice")
    assert alice is None

    scim_client.discover()
    User = scim_client.get_resource_model("User")
    request = BulkRequest[User](
        operations=[
            BulkOperation[User](
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
    alice = backend.get(models.User, user_name="Alice")
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Users/{alice.id}"
    )
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

    request = BulkRequest[Group](
        operations=[
            BulkOperation[Group](
                method="POST",
                path="/Groups",
                bulk_id="qwerty",
                data=Group(
                    display_name="Le Groupe",
                    members=[
                        Group.Members(
                            value=user.user_name, ref=f"Users/{user.user_name}"
                        )
                    ],
                ),
            ),
        ]
    )
    response = scim_client.bulk(request)
    groupe = backend.get(models.Group, display_name="Le Groupe")
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Groups/{groupe.id}"
    )
    assert response.operations[0].status == 201

    groupe = backend.get(models.Group, display_name="Le Groupe")
    assert groupe is not None
    assert groupe.display_name == "Le Groupe"
    assert groupe.members == [user]

    backend.delete(groupe)


def test_bulk_operation_create_user_validation_error(scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    request = BulkRequest[User](
        operations=[
            BulkOperation[User](
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


def test_bulk_operation_create_group_validation_error(scim_client, user):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")
    request = BulkRequest[Group](
        operations=[
            BulkOperation[Group](
                method="POST",
                path="/Groups",
                bulk_id="qwerty",
                # group is missing display name
                data=Group(
                    members=[Group.Members(value=user.id, ref=f"Users/{user.id}")]
                ),
            ),
        ]
    )
    response = scim_client.bulk(request)
    assert response.operations[0].status == 400
    assert response.operations[0].location is None


def test_bulk_operation_create_user_database_error(scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    request = BulkRequest[User](
        operations=[
            BulkOperation[User](
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


def test_bulk_operation_create_group_database_error(scim_client, user):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")
    request = BulkRequest[Group](
        operations=[
            BulkOperation[Group](
                method="POST",
                path="/Groups",
                bulk_id="qwerty",
                data=Group(
                    display_name="Le Groupe",
                    members=[Group.Members(value=user.id, ref=f"Users/{user.id}")],
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

    user_scim = scim_client.query(User, user.id)
    assert user_scim.display_name == "Johnny"

    user_scim.display_name = "Changed"

    request = BulkRequest[User](
        operations=[
            BulkOperation[User](
                method="PUT",
                path=f"/Users/{user.id}",
                data=user_scim,
            ),
        ]
    )
    response = scim_client.bulk(request)
    assert response.operations[0].status == 200
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Users/{user.id}"
    )

    backend.reload(user)
    assert user.display_name == "Changed"


def test_bulk_operation_replace_user_not_found(scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")

    request = BulkRequest[User](
        operations=[
            BulkOperation[User](
                method="PUT",
                path="/Users/invalid",
                data=User(
                    user_name="invalid",
                    name={"formatted": "Invalid", "family_name": "Invalid"},
                    active=True,
                ),
            ),
        ]
    )
    response = scim_client.bulk(request)
    assert response.operations[0].status == 404
    assert response.operations[0].response.detail == "Resource invalid not found"
    assert (
        response.operations[0].location == "http://canaille.test/scim/v2/Users/invalid"
    )


def test_bulk_operation_replace_user_validation_error(scim_client, user):
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    user_scim = scim_client.query(User, user.id)
    user_scim.active = None  # user is now missing required field

    request = BulkRequest[User](
        operations=[
            BulkOperation[User](method="PUT", path=f"/Users/{user.id}", data=user_scim),
        ]
    )
    response = scim_client.bulk(request)
    assert response.operations[0].status == 400
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Users/{user.id}"
    )


def test_bulk_operation_replace_user_database_error(scim_client, user):
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    user_scim = scim_client.query(User, user.id)
    user_scim.display_name = "Changed"

    request = BulkRequest[User](
        operations=[
            BulkOperation[User](method="PUT", path=f"/Users/{user.id}", data=user_scim),
        ]
    )
    with mock.patch(
        "canaille.backends.Backend.instance.save",
        side_effect=Exception("Database error"),
    ):
        response = scim_client.bulk(request)
    assert response.operations[0].status == 500
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Users/{user.id}"
    )


def test_bulk_operation_replace_group(backend, scim_client, foo_group, user, admin):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")

    group_scim = scim_client.query(Group, foo_group.id)

    assert group_scim.members[0].value == foo_group.members[0].id

    group_scim.members = [
        {"value": "admin", "ref": "User/admin"},
    ]

    request = BulkRequest[Group](
        operations=[
            BulkOperation[Group](
                method="PUT",
                path=f"/Groups/{foo_group.id}",
                data=group_scim,
            ),
        ]
    )
    response = scim_client.bulk(request)
    assert response.operations[0].status == 200
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Groups/{foo_group.id}"
    )

    backend.reload(foo_group)
    assert foo_group.members == [admin]


def test_bulk_operation_replace_group_not_found(scim_client):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")

    request = BulkRequest[Group](
        operations=[
            BulkOperation[Group](
                method="PUT",
                path="/Groups/invalid",
                data=Group(
                    display_name="invalid",
                    members=[{"value": "invalid", "ref": "Users/invalid"}],
                ),
            )
        ]
    )

    response = scim_client.bulk(request)
    assert response.operations[0].status == 404
    assert response.operations[0].response.detail == "Resource invalid not found"
    assert (
        response.operations[0].location == "http://canaille.test/scim/v2/Groups/invalid"
    )


def test_bulk_operation_replace_group_validation_error(scim_client, foo_group):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")
    group_scim = scim_client.query(Group, foo_group.id)
    group_scim.members = None  # group is now missing required field

    request = BulkRequest[Group](
        operations=[
            BulkOperation[Group](
                method="PUT", path=f"/Groups/{foo_group.id}", data=group_scim
            ),
        ]
    )
    response = scim_client.bulk(request)
    assert response.operations[0].status == 400
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Groups/{foo_group.id}"
    )


def test_bulk_operation_replace_group_database_error(scim_client, foo_group, admin):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")
    group_scim = scim_client.query(Group, foo_group.id)
    group_scim.members = [
        {"value": "admin", "ref": "User/admin"},
    ]

    request = BulkRequest[Group](
        operations=[
            BulkOperation[Group](
                method="PUT", path=f"/Groups/{foo_group.id}", data=group_scim
            ),
        ]
    )
    with mock.patch(
        "canaille.backends.Backend.instance.save",
        side_effect=Exception("Database error"),
    ):
        response = scim_client.bulk(request)
    assert response.operations[0].status == 500
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Groups/{foo_group.id}"
    )


def test_bulk_operation_modify_user(backend, scim_client, user):
    scim_client.discover()
    User = scim_client.get_resource_model("User")

    user_scim = scim_client.query(User, user.id)
    assert user_scim.display_name == "Johnny"

    operation = PatchOperation(
        op=PatchOperation.Op.replace_, path="displayName", value="Updated Display Name"
    )
    patch_op = PatchOp[User](operations=[operation])

    request = BulkRequest[User](
        operations=[
            BulkOperation[User](
                method="PATCH",
                path=f"/Users/{user.id}",
                data=patch_op,
            ),
        ]
    )

    response = scim_client.bulk(request)

    assert response.operations[0].status == 200

    backend.reload(user)
    assert user.display_name == "Updated Display Name"
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Users/{user.id}"
    )


def test_bulk_operation_modify_user_not_found(scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")

    operation = PatchOperation(
        op=PatchOperation.Op.replace_, path="displayName", value="Updated Display Name"
    )
    patch_op = PatchOp[User](operations=[operation])

    request = BulkRequest[User](
        operations=[
            BulkOperation[User](
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

    request = BulkRequest[User](
        operations=[
            BulkOperation[User](
                method="PATCH",
                path=f"/Users/{user.id}",
                data=patch_op,
            ),
        ]
    )

    response = scim_client.bulk(request)
    assert response.operations[0].status == 400
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Users/{user.id}"
    )


def test_bulk_operation_modify_user_database_error(scim_client, user):
    scim_client.discover()
    User = scim_client.get_resource_model("User")

    operation = PatchOperation(
        op=PatchOperation.Op.replace_, path="displayName", value="Updated Display Name"
    )
    patch_op = PatchOp[User](operations=[operation])

    request = BulkRequest[User](
        operations=[
            BulkOperation[User](
                method="PATCH",
                path=f"/Users/{user.id}",
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
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Users/{user.id}"
    )


def test_bulk_operation_modify_group(backend, scim_client, foo_group, admin):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")

    group_scim = scim_client.query(Group, foo_group.id)
    assert group_scim.members[0].value == foo_group.members[0].id

    operation = PatchOperation(
        op=PatchOperation.Op.replace_,
        path="members",
        value=[{"value": "admin", "ref": "Users/admin"}],
    )
    patch_op = PatchOp[Group](operations=[operation])

    request = BulkRequest[Group](
        operations=[
            BulkOperation[Group](
                method="PATCH",
                path=f"/Groups/{foo_group.id}",
                data=patch_op,
            ),
        ]
    )

    response = scim_client.bulk(request)

    assert response.operations[0].status == 200
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Groups/{foo_group.id}"
    )
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

    request = BulkRequest[Group](
        operations=[
            BulkOperation[Group](
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

    request = BulkRequest[Group](
        operations=[
            BulkOperation[Group](
                method="PATCH",
                path=f"/Groups/{foo_group.id}",
                data=patch_op,
            ),
        ]
    )

    response = scim_client.bulk(request)
    assert response.operations[0].status == 400
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Groups/{foo_group.id}"
    )


def test_bulk_operation_modify_group_database_error(scim_client, foo_group, admin):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")

    operation = PatchOperation(
        op=PatchOperation.Op.replace_,
        path="members",
        value=[{"value": "admin", "ref": "Users/admin"}],
    )
    patch_op = PatchOp[Group](operations=[operation])

    request = BulkRequest[Group](
        operations=[
            BulkOperation[Group](
                method="PATCH",
                path=f"/Groups/{foo_group.id}",
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
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Groups/{foo_group.id}"
    )


def test_bulk_operation_delete_user(backend, scim_client, user):
    scim_client.discover()
    User = scim_client.get_resource_model("User")

    request = BulkRequest[User](
        operations=[
            BulkOperation[User](
                method="DELETE",
                path=f"/Users/{user.id}",
            ),
        ]
    )

    response = scim_client.bulk(request)

    assert response.operations[0].status == 204
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Users/{user.id}"
    )

    user = backend.get(models.User, user_name="user")
    assert user is None


def test_bulk_operation_delete_user_not_found(scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")

    request = BulkRequest[User](
        operations=[
            BulkOperation[User](
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
    User = scim_client.get_resource_model("User")

    request = BulkRequest[User](
        operations=[
            BulkOperation[User](
                method="DELETE",
                path=f"/Users/{user.id}",
            ),
        ]
    )

    with mock.patch(
        "canaille.backends.Backend.instance.delete",
        side_effect=Exception("Database error"),
    ):
        response = scim_client.bulk(request)

    assert response.operations[0].status == 500
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Users/{user.id}"
    )


def test_bulk_operation_delete_group(backend, scim_client, user):
    group = models.Group(members=[user], display_name="to delete")
    backend.save(group)
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")

    request = BulkRequest[Group](
        operations=[
            BulkOperation[Group](
                method="DELETE",
                path=f"/Groups/{group.id}",
            ),
        ]
    )

    response = scim_client.bulk(request)

    assert response.operations[0].status == 204
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Groups/{group.id}"
    )
    assert backend.get(models.Group, id=group.id) is None


def test_bulk_operation_delete_group_not_found(scim_client):
    scim_client.discover()
    Group = scim_client.get_resource_model("Group")

    request = BulkRequest[Group](
        operations=[
            BulkOperation[Group](
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
    Group = scim_client.get_resource_model("Group")

    request = BulkRequest[Group](
        operations=[
            BulkOperation[Group](
                method="DELETE",
                path=f"/Groups/{foo_group.id}",
            ),
        ]
    )

    with mock.patch(
        "canaille.backends.Backend.instance.delete",
        side_effect=Exception("Database error"),
    ):
        response = scim_client.bulk(request)

    assert response.operations[0].status == 500
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Groups/{foo_group.id}"
    )


def test_bulk_operation_stop_after_fail_on_errors_number_reached(scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")

    request = BulkRequest[User](
        fail_on_errors=2,
        operations=[
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwerty",
                data=User(
                    user_name="firstuser",
                    name={"formatted": "First User", "family_name": "User"},
                    active=True,
                ),
            ),
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwertyu",
                data=User(
                    user_name="seconduser",
                    name={"formatted": "Second User", "family_name": "User"},
                    active=True,
                ),
            ),
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwertyui",
                data=User(
                    user_name="thirduser",
                    name={"formatted": "Third User", "family_name": "User"},
                    active=True,
                ),
            ),
        ],
    )

    with mock.patch(
        "canaille.backends.Backend.instance.save",
        side_effect=Exception("Database error"),
    ):
        response = scim_client.bulk(request)

    assert len(response.operations) == 2
    assert response.operations[0].status == 500
    assert response.operations[0].bulk_id == "qwerty"
    assert response.operations[1].status == 500
    assert response.operations[1].bulk_id == "qwertyu"


def test_bulk_too_many_operations(scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")

    request = BulkRequest[User](
        operations=[
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwerty1",
                data=User(
                    user_name="firstuser",
                    name={"formatted": "First User", "family_name": "User"},
                    active=True,
                ),
            ),
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwerty2",
                data=User(
                    user_name="seconduser",
                    name={"formatted": "Second User", "family_name": "User"},
                    active=True,
                ),
            ),
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwerty3",
                data=User(
                    user_name="thirduser",
                    name={"formatted": "Third User", "family_name": "User"},
                    active=True,
                ),
            ),
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwerty4",
                data=User(
                    user_name="fourthuser",
                    name={"formatted": "Fourth User", "family_name": "User"},
                    active=True,
                ),
            ),
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwerty5",
                data=User(
                    user_name="fifthuser",
                    name={"formatted": "Fifth User", "family_name": "User"},
                    active=True,
                ),
            ),
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwerty6",
                data=User(
                    user_name="sixthuser",
                    name={"formatted": "Sixth User", "family_name": "User"},
                    active=True,
                ),
            ),
        ],
    )

    error = scim_client.bulk(
        request.model_dump(scim_ctx=Context.BULK_REQUEST),
        check_request_payload=False,
        raise_scim_errors=False,
    )
    assert isinstance(error, Error)
    assert error.status == 413
    assert error.detail == "The number of operations exceeds the maxOperations (5)"


def test_bulk_request_payload_too_large(scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")

    request = BulkRequest[User](
        operations=[
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwerty1" * 1000,
                data=User(
                    user_name="firstuser",
                    name={"formatted": "First User", "family_name": "User"},
                    active=True,
                ),
            ),
        ],
    )

    error = scim_client.bulk(
        request.model_dump(scim_ctx=Context.BULK_REQUEST),
        check_request_payload=False,
        raise_scim_errors=False,
    )
    assert isinstance(error, Error)
    assert error.status == 413
    assert error.detail == "The payload exceeds the maxPayloadSize (5000 bytes)"


def test_create_group_with_bulk_id(backend, scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    Group = scim_client.get_resource_model("Group")

    request = BulkRequest[User | Group](
        operations=[
            BulkOperation[Group](
                method="POST",
                path="/Groups",
                bulk_id="ytrewq",
                data=Group(
                    display_name="Tour Guides",
                    members=[Group.Members(value="bulkId:qwerty", ref="Users/Alice")],
                ),
            ),
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwerty",
                data=User(
                    user_name="Alice",
                    name={"formatted": "Alice Example", "family_name": "Example"},
                    active=True,
                ),
            ),
        ],
    )

    response = scim_client.bulk(request)
    assert response.operations[0].bulk_id == "ytrewq"
    tour_guides = backend.get(models.Group, display_name="Tour Guides")
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Groups/{tour_guides.id}"
    )
    assert response.operations[1].bulk_id == "qwerty"
    alice = backend.get(models.User, user_name="Alice")
    assert (
        response.operations[1].location
        == f"http://canaille.test/scim/v2/Users/{alice.id}"
    )

    alice = backend.get(models.User, user_name="Alice")
    assert alice is not None
    tour_guides = backend.get(models.Group, display_name="Tour Guides")
    assert tour_guides is not None
    assert tour_guides.members == [alice]

    backend.delete(tour_guides)
    backend.delete(alice)


def test_replace_group_with_bulk_id(backend, scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    Group = scim_client.get_resource_model("Group")

    request = BulkRequest[User | Group](
        operations=[
            BulkOperation[Group](
                method="POST",
                path="/Groups",
                bulk_id="ytrewq",
                data=Group(
                    display_name="Tour Guides",
                    members=[Group.Members(value="bulkId:qwerty", ref="Users/Alice")],
                ),
            ),
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwerty",
                data=User(
                    user_name="Alice",
                    name={"formatted": "Alice Example", "family_name": "Example"},
                    active=True,
                ),
            ),
        ],
    )

    scim_client.bulk(request)
    tour_guides = backend.get(models.Group, display_name="Tour Guides")

    request = BulkRequest[User | Group](
        operations=[
            BulkOperation[Group](
                method="PUT",
                path=f"/Groups/{tour_guides.id}",
                data=Group(
                    display_name="Tour Guides",
                    members=[Group.Members(value="bulkId:qwerty", ref="Users/Bob")],
                ),
            ),
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwerty",
                data=User(
                    user_name="Bob",
                    name={"formatted": "Bob Example", "family_name": "Example"},
                    active=True,
                ),
            ),
        ],
    )

    scim_client.bulk(request)

    alice = backend.get(models.User, user_name="Alice")
    assert alice is not None
    bob = backend.get(models.User, user_name="Bob")
    assert bob is not None
    tour_guides = backend.get(models.Group, display_name="Tour Guides")
    assert tour_guides is not None
    assert tour_guides.members == [bob]

    backend.delete(tour_guides)
    backend.delete(alice)
    backend.delete(bob)


def test_replace_group_with_invalid_bulk_id(backend, scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    Group = scim_client.get_resource_model("Group")

    request = BulkRequest[User | Group](
        operations=[
            BulkOperation[Group](
                method="POST",
                path="/Groups",
                bulk_id="ytrewq",
                data=Group(
                    display_name="Tour Guides",
                    members=[Group.Members(value="bulkId:qwerty", ref="Users/Alice")],
                ),
            ),
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwerty",
                data=User(
                    user_name="Alice",
                    name={"formatted": "Alice Example", "family_name": "Example"},
                    active=True,
                ),
            ),
        ],
    )

    scim_client.bulk(request)
    tour_guides = backend.get(models.Group, display_name="Tour Guides")

    request = BulkRequest[User | Group](
        operations=[
            BulkOperation[Group](
                method="PUT",
                path=f"/Groups/{tour_guides.id}",
                data=Group(
                    display_name="Tour Guides",
                    members=[Group.Members(value="bulkId:invalid", ref="Users/Bob")],
                ),
            ),
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwerty",
                data=User(
                    user_name="Bob",
                    name={"formatted": "Bob Example", "family_name": "Example"},
                    active=True,
                ),
            ),
        ],
    )

    response = scim_client.bulk(request)

    assert response.operations[0].status == 409
    tour_guides = backend.get(models.Group, display_name="Tour Guides")
    assert (
        response.operations[0].location
        == f"http://canaille.test/scim/v2/Groups/{tour_guides.id}"
    )

    alice = backend.get(models.User, user_name="Alice")
    bob = backend.get(models.User, user_name="Bob")
    tour_guides = backend.get(models.Group, display_name="Tour Guides")

    backend.delete(tour_guides)
    backend.delete(alice)
    backend.delete(bob)


def test_modify_group_with_bulk_id(backend, scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    Group = scim_client.get_resource_model("Group")

    request = BulkRequest[User | Group](
        operations=[
            BulkOperation[Group](
                method="POST",
                path="/Groups",
                bulk_id="ytrewq",
                data=Group(
                    display_name="Tour Guides",
                    members=[Group.Members(value="bulkId:qwerty", ref="Users/Alice")],
                ),
            ),
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwerty",
                data=User(
                    user_name="Alice",
                    name={"formatted": "Alice Example", "family_name": "Example"},
                    active=True,
                ),
            ),
        ],
    )

    scim_client.bulk(request)
    tour_guides = backend.get(models.Group, display_name="Tour Guides")

    operation = PatchOperation(
        op=PatchOperation.Op.replace_,
        path="members",
        value=[Group.Members(value="bulkId:qwerty", ref="Users/Bob")],
    )
    patch_op = PatchOp[Group](operations=[operation])

    request = BulkRequest[User | Group](
        operations=[
            BulkOperation[Group](
                method="PATCH", path=f"/Groups/{tour_guides.id}", data=patch_op
            ),
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwerty",
                data=User(
                    user_name="Bob",
                    name={"formatted": "Bob Example", "family_name": "Example"},
                    active=True,
                ),
            ),
        ],
    )

    scim_client.bulk(request)

    alice = backend.get(models.User, user_name="Alice")
    assert alice is not None
    bob = backend.get(models.User, user_name="Bob")
    assert bob is not None
    tour_guides = backend.get(models.Group, display_name="Tour Guides")
    assert tour_guides is not None
    assert tour_guides.members == [bob]

    backend.delete(tour_guides)
    backend.delete(alice)
    backend.delete(bob)


def test_create_group_with_invalid_bulk_id(backend, scim_client):
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    Group = scim_client.get_resource_model("Group")

    request = BulkRequest[User | Group](
        operations=[
            BulkOperation[Group](
                method="POST",
                path="/Groups",
                bulk_id="ytrewq",
                data=Group(
                    display_name="Tour Guides",
                    members=[Group.Members(value="bulkId:invalid", ref="Users/Alice")],
                ),
            ),
            BulkOperation[User](
                method="POST",
                path="/Users",
                bulk_id="qwerty",
                data=User(
                    user_name="Alice",
                    name={"formatted": "Alice Example", "family_name": "Example"},
                    active=True,
                ),
            ),
        ],
    )

    response = scim_client.bulk(request)
    assert response.operations[0].status == 409
    assert response.operations[0].location is None
    assert (
        response.operations[0].response.detail
        == "No resource was created with the bulkId invalid"
    )

    alice = backend.get(models.User, user_name="Alice")
    assert alice is not None
    tour_guides = backend.get(models.Group, display_name="Tour Guides")
    assert tour_guides is None

    backend.delete(alice)
