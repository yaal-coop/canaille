import pytest
from werkzeug.test import Client

from canaille.core.populate import fake_users

from .conftest import _scim_headers


def test_scim_pagination(app, backend, user, oidc_token):
    users = fake_users(25)
    client = Client(app)
    headers = _scim_headers(app, oidc_token)
    response = client.get("/scim/v2/Users?cursor&count=15", headers=headers)
    assert response.status_code == 200

    response_json = response.get_json()
    print(response_json)
    assert len(response_json["Resources"]) == 15
    assert response_json["totalResults"] == 26
    assert response_json["itemsPerPage"] == 15
    assert "nextCursor" in response_json

    next_cursor = response.get_json()["nextCursor"]

    response = client.get(
        f"/scim/v2/Users?cursor={next_cursor}&count=15",
        headers=headers,
    )
    assert response.status_code == 200

    response_json = response.get_json()
    assert len(response_json["Resources"]) == 11
    assert response_json["totalResults"] == 26
    assert response_json["itemsPerPage"] == 15
    assert response_json["prevCursor"] == next_cursor
    for user in users:
        backend.delete(user)

def test_scim_pagination_with_user_deletion(app, backend, user, oidc_token):
    users = fake_users(25)
    client = Client(app)
    headers = _scim_headers(app, oidc_token)
    response = client.get("/scim/v2/Users?cursor&count=15", headers=headers)
    assert response.status_code == 200

    response_json = response.get_json()
    assert len(response_json["Resources"]) == 15
    assert response_json["totalResults"] == 26
    assert response_json["itemsPerPage"] == 15
    assert "nextCursor" in response_json

    next_cursor = response_json["nextCursor"]

    full_order = sorted(
        [user, *users], key=lambda resource: (resource.created, resource.id)
    )
    before_cursor, after_cursor = full_order[:15], full_order[15:]

    to_delete = [
        before_cursor[-1],  # already returned on page 1
        after_cursor[0],  # the resource the cursor itself points to
        after_cursor[-3],
        after_cursor[-2],
        after_cursor[-1],
    ]
    # never delete the authenticated user, whatever position it landed on
    to_delete = [resource for resource in to_delete if resource is not user]
    for resource in to_delete:
        backend.delete(resource)

    deleted_before_cursor = [
        resource for resource in to_delete if resource in before_cursor
    ]
    new_start_index = len(before_cursor) - len(deleted_before_cursor)
    expected_total = 26 - len(to_delete)
    expected_page_len = min(15, expected_total - new_start_index)

    response = client.get(
        f"/scim/v2/Users?cursor={next_cursor}&count=15",
        headers=headers,
    )
    assert response.status_code == 200

    response_json = response.get_json()
    assert response_json["totalResults"] == expected_total
    assert response_json["itemsPerPage"] == 15
    assert len(response_json["Resources"]) == expected_page_len
    assert response_json["prevCursor"] == next_cursor

    for resource in users:
        backend.delete(resource)