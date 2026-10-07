import datetime
import json

import pytest
from werkzeug.security import gen_salt
from werkzeug.test import Client

from canaille.app import models
from canaille.core.configuration import Permission
from canaille.scim.client import get_or_create_token

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


def test_user_token_with_manage_users_cannot_list_users(app, backend, user, user_token):
    """A user token is refused on /Users, even with MANAGE_USERS permission."""
    app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"].append(
        Permission.MANAGE_USERS
    )
    backend.reload(user)
    client = Client(app)
    response = client.get("/scim/v2/Users", headers=_scim_headers(app, user_token))
    assert response.status_code == 403


def test_user_token_with_manage_users_cannot_read_another_user(
    app, backend, user, admin, user_token
):
    """A user token is refused on another user, even with MANAGE_USERS permission."""
    app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"].append(
        Permission.MANAGE_USERS
    )
    backend.reload(user)
    client = Client(app)
    response = client.get(
        f"/scim/v2/Users/{admin.id}", headers=_scim_headers(app, user_token)
    )
    assert response.status_code == 403


def test_user_token_can_read_its_own_user(app, backend, user, user_token):
    """A user token reads its own user on /Users/{id}, as on /Me."""
    client = Client(app)
    response = client.get(
        f"/scim/v2/Users/{user.id}", headers=_scim_headers(app, user_token)
    )
    assert response.status_code == 200
    assert response.json["id"] == user.id


def test_user_token_follows_the_write_acl_on_its_own_user(
    app, backend, user, user_token
):
    """A user cannot modify on /Users/{id} a field that the WRITE ACL does not list."""
    app.config["CANAILLE"]["ACL"]["DEFAULT"]["WRITE"].remove("title")
    backend.reload(user)
    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "replace", "path": "title", "value": "CEO"}],
    }
    response = Client(app).patch(
        f"/scim/v2/Users/{user.id}",
        data=json.dumps(payload),
        headers=_scim_headers(app, user_token),
    )
    assert response.status_code == 403
    backend.reload(user)
    assert user.title != "CEO"


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


def test_user_token_with_manage_all_groups_cannot_list_groups(
    app, backend, user, user_token
):
    """A user token is refused on /Groups, even with MANAGE_ALL_GROUPS permission."""
    app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"].append(
        Permission.MANAGE_ALL_GROUPS
    )
    backend.reload(user)
    client = Client(app)
    response = client.get("/scim/v2/Groups", headers=_scim_headers(app, user_token))
    assert response.status_code == 403


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


def test_client_token_with_scim_write_can_access_all_endpoints(
    app, backend, user, oidc_token
):
    """A client token with the scim:write scope can access users and groups."""
    client = Client(app)
    headers = _scim_headers(app, oidc_token)
    response = client.get("/scim/v2/Users", headers=headers)
    assert response.status_code == 200
    response = client.get("/scim/v2/Groups", headers=headers)
    assert response.status_code == 200


@pytest.fixture
def make_token(backend, oidc_client):
    tokens = []

    def make(scope, subject=None):
        token = models.Token(
            token_id=gen_salt(48),
            access_token=gen_salt(48),
            subject=subject,
            audience=[oidc_client],
            client=oidc_client,
            refresh_token=gen_salt(48),
            scope=scope,
            issue_date=datetime.datetime.now(datetime.UTC),
            lifetime=3600,
        )
        backend.save(token)
        tokens.append(token)
        return token

    yield make
    for token in tokens:
        backend.delete(token)


def _patch_me(app, token, operations):
    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": operations,
    }
    return Client(app).patch(
        "/scim/v2/Me", data=json.dumps(payload), headers=_scim_headers(app, token)
    )


def test_client_token_without_scim_scope_is_refused(app, backend, make_token):
    """A client token without a SCIM scope gets 403 on /Users and /Groups."""
    token = make_token(["openid", "profile"])
    client = Client(app)
    headers = _scim_headers(app, token)
    assert client.get("/scim/v2/Users", headers=headers).status_code == 403
    assert client.get("/scim/v2/Groups", headers=headers).status_code == 403


def test_provisioning_token_is_refused(app, backend, oidc_client):
    """The token Canaille sends to clients for provisioning gives no access to its SCIM API."""
    token = get_or_create_token(oidc_client)
    client = Client(app)
    response = client.get("/scim/v2/Users", headers=_scim_headers(app, token))
    assert response.status_code == 403


def test_client_token_with_users_read_scope(app, backend, make_token):
    """The scim:users:read scope allows reading users only."""
    token = make_token(["scim:users:read"])
    client = Client(app)
    headers = _scim_headers(app, token)
    assert client.get("/scim/v2/Users", headers=headers).status_code == 200
    assert client.get("/scim/v2/Groups", headers=headers).status_code == 403
    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "newuser",
    }
    response = client.post("/scim/v2/Users", data=json.dumps(payload), headers=headers)
    assert response.status_code == 403


def test_client_token_with_groups_write_scope_can_read_groups(app, backend, make_token):
    """The scim:groups:write scope also allows reading groups."""
    token = make_token(["scim:groups:write"])
    client = Client(app)
    headers = _scim_headers(app, token)
    assert client.get("/scim/v2/Groups", headers=headers).status_code == 200
    assert client.get("/scim/v2/Users", headers=headers).status_code == 403


def test_client_token_with_scim_read_scope(app, backend, make_token):
    """The scim:read scope allows reading users and groups, but not writing."""
    token = make_token(["scim:read"])
    client = Client(app)
    headers = _scim_headers(app, token)
    assert client.get("/scim/v2/Users", headers=headers).status_code == 200
    assert client.get("/scim/v2/Groups", headers=headers).status_code == 200
    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "displayName": "newgroup",
    }
    response = client.post("/scim/v2/Groups", data=json.dumps(payload), headers=headers)
    assert response.status_code == 403


def test_search_only_returns_the_readable_resource_types(
    app, backend, user, foo_group, make_token
):
    """A search with the scim:users:read scope only returns users."""
    token = make_token(["scim:users:read"])
    payload = {"schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"]}
    response = Client(app).post(
        "/scim/v2/.search", data=json.dumps(payload), headers=_scim_headers(app, token)
    )
    assert response.status_code == 200
    resource_types = {r["meta"]["resourceType"] for r in response.json["Resources"]}
    assert resource_types == {"User"}


def test_bulk_refuses_the_operations_out_of_the_scope(app, backend, user, make_token):
    """In a bulk request, an operation on a resource type out of the scope fails alone."""
    token = make_token(["scim:users:write"])
    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"],
        "Operations": [
            {
                "method": "POST",
                "path": "/Users",
                "bulkId": "user",
                "data": {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
                    "userName": "bulkuser",
                    "name": {"familyName": "Bulk", "formatted": "Bulk User"},
                    "emails": [{"value": "bulk@example.test"}],
                    "active": True,
                },
            },
            {
                "method": "POST",
                "path": "/Groups",
                "bulkId": "group",
                "data": {
                    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
                    "displayName": "bulkgroup",
                    "members": [{"value": user.id}],
                },
            },
        ],
    }
    response = Client(app).post(
        "/scim/v2/Bulk", data=json.dumps(payload), headers=_scim_headers(app, token)
    )
    assert response.status_code == 200
    statuses = [operation["status"] for operation in response.json["Operations"]]
    assert statuses == ["201", "403"]
    assert not backend.get(models.Group, display_name="bulkgroup")
    bulk_user = backend.get(models.User, user_name="bulkuser")
    assert bulk_user
    backend.delete(bulk_user)


def test_user_token_without_scim_me_scope_is_refused_on_me(
    app, backend, user, make_token
):
    """A user token without the scim:me scope cannot change the user password."""
    token = make_token(["openid", "profile"], subject=user)
    response = _patch_me(
        app, token, [{"op": "replace", "path": "password", "value": "new-password-123"}]
    )
    assert response.status_code == 403
    assert not backend.check_user_password(user, "new-password-123")[0]


def test_client_token_with_scim_me_scope_gets_404_on_me(app, backend, make_token):
    """A client token has no user to serve on /Me."""
    token = make_token(["scim:me"])
    response = Client(app).get("/scim/v2/Me", headers=_scim_headers(app, token))
    assert response.status_code == 404


def test_locked_user_token_is_refused(app, backend, user, user_token):
    """The token of a locked user is refused."""
    user.lock_date = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)
    backend.save(user)
    response = Client(app).get("/scim/v2/Me", headers=_scim_headers(app, user_token))
    assert response.status_code == 401


def test_me_cannot_modify_fields_out_of_the_write_acl(app, backend, user, user_token):
    """A user cannot modify on /Me a field that the WRITE ACL does not list."""
    app.config["CANAILLE"]["ACL"]["DEFAULT"]["WRITE"].remove("title")
    backend.reload(user)
    response = _patch_me(
        app, user_token, [{"op": "replace", "path": "title", "value": "CEO"}]
    )
    assert response.status_code == 403
    backend.reload(user)
    assert user.title != "CEO"


def test_me_cannot_change_its_lock_date(app, backend, user, user_token):
    """A user cannot lock their account on /Me when the WRITE ACL does not list lock_date."""
    app.config["CANAILLE"]["ACL"]["DEFAULT"]["WRITE"].remove("lock_date")
    lock_date = datetime.datetime.now(datetime.UTC).replace(
        microsecond=0
    ) + datetime.timedelta(days=30)
    user.lock_date = lock_date
    backend.save(user)
    response = _patch_me(
        app, user_token, [{"op": "replace", "path": "active", "value": False}]
    )
    assert response.status_code == 403
    backend.reload(user)
    assert user.lock_date == lock_date


def test_me_replace_keeps_the_scheduled_expiration(app, backend, user, user_token):
    """A PUT on /Me that changes nothing keeps the scheduled expiration of the account."""
    lock_date = datetime.datetime.now(datetime.UTC).replace(
        microsecond=0
    ) + datetime.timedelta(days=30)
    user.lock_date = lock_date
    backend.save(user)
    client = Client(app)
    headers = _scim_headers(app, user_token)
    payload = client.get("/scim/v2/Me", headers=headers).get_json()
    assert payload["active"] is True
    for key in ("id", "meta", "photos", "groups"):
        payload.pop(key, None)
    payload["displayName"] = "Changed"

    response = client.put("/scim/v2/Me", data=json.dumps(payload), headers=headers)
    assert response.status_code == 200
    backend.reload(user)
    assert user.lock_date == lock_date
