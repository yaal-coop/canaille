from scim2_models import BulkOperation
from scim2_models import BulkRequest
from scim2_models import PatchOperation

from canaille.app import models

Op = PatchOperation.Op


def test_bulk(app, backend, scim_client):
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

    alice = backend.get(models.User, user_name="Alice")
    assert alice is not None
    assert alice.user_name == "Alice"

    backend.delete(alice)


# def test_bulk_groups(app, backend, scim_client):
#     alice = backend.get(models.User, user_name="Alice")
#     assert alice is None

#     scim_client.discover()
#     Group = scim_client.get_resource_model("Group")
#     request = BulkRequest(
#         operations=[
#             BulkOperation(
#                 method="POST",
#                 path="/Groups",
#                 bulk_id="qwerty",
#                 data=Group(display_name="Le Groupe"),
#             ),
#         ]
#     )
#     response = scim_client.bulk(request)

#     # alice = backend.get(models.User, user_name="Alice")
#     # assert alice is not None
#     # assert alice.user_name == "Alice"

#     # backend.delete(alice)
