from werkzeug.test import Client

from .conftest import _scim_headers


def test_search_with_a_filter(app, backend, user, admin, oidc_token):
    """A search with a filter returns the matching users only."""
    client = Client(app)
    response = client.get(
        "/scim/v2/Users",
        query_string={"filter": 'userName eq "USER"'},
        headers=_scim_headers(app, oidc_token),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["totalResults"] == 1
    assert [r["id"] for r in data["Resources"]] == [user.id]


def test_search_sorted(app, backend, user, admin, oidc_token):
    """A sorted search orders the users before paging them."""
    client = Client(app)
    response = client.get(
        "/scim/v2/Users",
        query_string={"sortBy": "userName", "sortOrder": "descending", "count": "1"},
        headers=_scim_headers(app, oidc_token),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["totalResults"] == 2
    assert [r["userName"] for r in data["Resources"]] == ["user"]
