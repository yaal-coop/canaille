import pytest
from werkzeug.test import Client

from .conftest import _scim_headers


def test_scim_pagination(app, backend, user, oidc_token, admin, moderator):
    client = Client(app)
    headers = _scim_headers(app, oidc_token)
    response = client.get("/scim/v2/Users?cursor&count=2", headers=headers)
    assert response.status_code == 200

    response_json = response.get_json()
    print(response_json)
    assert len(response_json["Resources"]) == 2
    assert response_json["totalResults"] == 3
    assert response_json["itemsPerPage"] == 2
    assert "nextCursor" in response_json

    next_cursor = response.get_json()["nextCursor"]

    response = client.get(
        f"/scim/v2/Users?cursor={next_cursor}&count=2",
        headers=headers,
    )
    assert response.status_code == 200

    response_json = response.get_json()
    assert len(response_json["Resources"]) == 1
    assert response_json["totalResults"] == 3
    assert response_json["itemsPerPage"] == 2
    assert response_json["prevCursor"] == next_cursor
