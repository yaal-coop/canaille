from werkzeug.test import Client

from .conftest import _scim_headers


def test_group_members_reference_is_a_url(app, backend, user, foo_group, oidc_token):
    """The members of a group reference the URL of their user."""
    response = Client(app).get(
        f"/scim/v2/Groups/{foo_group.id}", headers=_scim_headers(app, oidc_token)
    )

    assert response.status_code == 200
    member = response.get_json()["members"][0]
    assert member["$ref"] == f"http://canaille.test/scim/v2/Users/{user.id}"


def test_user_groups_reference_is_a_url(app, backend, user, foo_group, oidc_token):
    """The groups of a user reference the URL of their group."""
    response = Client(app).get(
        f"/scim/v2/Users/{user.id}", headers=_scim_headers(app, oidc_token)
    )

    assert response.status_code == 200
    group = response.get_json()["groups"][0]
    assert group["$ref"] == f"http://canaille.test/scim/v2/Groups/{foo_group.id}"
