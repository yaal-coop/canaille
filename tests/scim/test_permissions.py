import json

from werkzeug.test import Client

from canaille.core.configuration import Permission

from .conftest import _scim_headers


def test_user_token_without_manage_users_cannot_list_users(
    app, backend, user, user_token
):
    """A user token without MANAGE_USERS permission gets a SCIM 403 error on /Users."""
    client = Client(app)
    response = client.get("/scim/v2/Users", headers=_scim_headers(app, user_token))
    assert response.status_code == 403
    data = response.get_json()
    assert data["status"] == "403"


def test_user_token_with_manage_users_can_list_users(app, backend, user, user_token):
    """A user token with MANAGE_USERS permission can access /Users."""
    app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"].append(
        Permission.MANAGE_USERS
    )
    backend.reload(user)
    client = Client(app)
    response = client.get("/scim/v2/Users", headers=_scim_headers(app, user_token))
    assert response.status_code == 200


def test_user_token_with_manage_users_can_read_single_user(
    app, backend, user, user_token
):
    """A user token with MANAGE_USERS permission can read a specific user."""
    app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"].append(
        Permission.MANAGE_USERS
    )
    backend.reload(user)
    client = Client(app)
    response = client.get(
        f"/scim/v2/Users/{user.id}", headers=_scim_headers(app, user_token)
    )
    assert response.status_code == 200


def test_user_token_without_manage_users_cannot_create_user(
    app, backend, user, user_token
):
    """A user token without MANAGE_USERS permission gets 403 on POST /Users."""
    client = Client(app)
    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "newuser",
    }
    response = client.post(
        "/scim/v2/Users",
        data=json.dumps(payload),
        headers=_scim_headers(app, user_token),
    )
    assert response.status_code == 403


def test_user_token_without_manage_users_cannot_delete_user(
    app, backend, user, admin, user_token
):
    """A user token without MANAGE_USERS permission gets 403 on DELETE /Users/{id}."""
    client = Client(app)
    response = client.delete(
        f"/scim/v2/Users/{admin.id}", headers=_scim_headers(app, user_token)
    )
    assert response.status_code == 403


def test_user_token_without_manage_all_groups_cannot_list_groups(
    app, backend, user, user_token
):
    """A user token without MANAGE_ALL_GROUPS permission gets 403 on /Groups."""
    client = Client(app)
    response = client.get("/scim/v2/Groups", headers=_scim_headers(app, user_token))
    assert response.status_code == 403


def test_user_token_with_manage_all_groups_can_list_groups(
    app, backend, user, user_token
):
    """A user token with MANAGE_ALL_GROUPS permission can access /Groups."""
    app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"].append(
        Permission.MANAGE_ALL_GROUPS
    )
    backend.reload(user)
    client = Client(app)
    response = client.get("/scim/v2/Groups", headers=_scim_headers(app, user_token))
    assert response.status_code == 200


def test_user_token_without_manage_users_cannot_search(app, backend, user, user_token):
    """A user token without MANAGE_USERS permission gets 403 on /.search."""
    client = Client(app)
    payload = {"schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"]}
    response = client.post(
        "/scim/v2/.search",
        data=json.dumps(payload),
        headers=_scim_headers(app, user_token),
    )
    assert response.status_code == 403


def test_user_token_can_access_service_provider_config(app, backend, user, user_token):
    """Any authenticated user token can access discovery endpoints."""
    client = Client(app)
    response = client.get(
        "/scim/v2/ServiceProviderConfig", headers=_scim_headers(app, user_token)
    )
    assert response.status_code == 200


def test_user_token_can_access_schemas(app, backend, user, user_token):
    """Any authenticated user token can access the Schemas endpoint."""
    client = Client(app)
    response = client.get("/scim/v2/Schemas", headers=_scim_headers(app, user_token))
    assert response.status_code == 200


def test_user_token_can_access_resource_types(app, backend, user, user_token):
    """Any authenticated user token can access the ResourceTypes endpoint."""
    client = Client(app)
    response = client.get(
        "/scim/v2/ResourceTypes", headers=_scim_headers(app, user_token)
    )
    assert response.status_code == 200


def test_client_token_can_access_all_endpoints(app, backend, user, oidc_token):
    """Client tokens bypass permission checks and have full access."""
    client = Client(app)
    headers = _scim_headers(app, oidc_token)
    response = client.get("/scim/v2/Users", headers=headers)
    assert response.status_code == 200
    response = client.get("/scim/v2/Groups", headers=headers)
    assert response.status_code == 200
