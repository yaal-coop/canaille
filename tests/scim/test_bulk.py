from unittest import mock

from scim2_models import BulkOperation
from scim2_models import BulkRequest
from scim2_models import PatchOperation

from canaille.app import models

Op = PatchOperation.Op


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
    scim_client.bulk(request)

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
    scim_client.bulk(request)
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
                data=User(user_name="Alice"),
            ),
        ]
    )
    response = scim_client.bulk(request)
    assert response.operations[0].status == 400


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

    backend.reload(user)
    assert user.display_name == "Changed"
