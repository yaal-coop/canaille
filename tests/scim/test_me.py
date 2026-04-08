import datetime
import json

from werkzeug.test import Client

from canaille.app import models
from canaille.core.configuration import Permission
from canaille.scim.casting import make_etag

from .conftest import _scim_headers


def test_get_me(app, backend, user, user_token):
    """GET /Me returns the authenticated user's SCIM representation."""
    client = Client(app)
    response = client.get("/scim/v2/Me", headers=_scim_headers(app, user_token))
    assert response.status_code == 200
    data = response.get_json()
    assert data["userName"] == user.user_name
    assert data["id"] == user.id


def test_get_me_with_client_token_returns_404(app, backend, oidc_token):
    """GET /Me with a client token (no subject) returns 404."""
    client = Client(app)
    response = client.get("/scim/v2/Me", headers=_scim_headers(app, oidc_token))
    assert response.status_code == 404


def test_replace_me(app, backend, user, user_token):
    """PUT /Me replaces the authenticated user's resource."""
    client = Client(app)
    headers = _scim_headers(app, user_token)

    get_response = client.get("/scim/v2/Me", headers=headers)
    payload = get_response.get_json()
    for key in ("id", "meta", "photos", "groups"):
        payload.pop(key, None)
    payload["displayName"] = "Updated via Me"

    response = client.put("/scim/v2/Me", data=json.dumps(payload), headers=headers)
    assert response.status_code == 200
    assert response.get_json()["displayName"] == "Updated via Me"

    backend.reload(user)
    assert user.display_name == "Updated via Me"


def test_patch_me(app, backend, user, user_token):
    """PATCH /Me partially updates the authenticated user's resource."""
    client = Client(app)
    headers = _scim_headers(app, user_token)
    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {"op": "replace", "path": "title", "value": "CTO"},
        ],
    }
    response = client.patch("/scim/v2/Me", data=json.dumps(payload), headers=headers)
    assert response.status_code == 200
    assert response.get_json()["title"] == "CTO"

    backend.reload(user)
    assert user.title == "CTO"


def test_delete_me(app, backend, oidc_client):
    """DELETE /Me deletes the authenticated user's account."""
    from werkzeug.security import gen_salt

    app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"].append(
        Permission.DELETE_ACCOUNT
    )
    user = models.User(
        user_name="deletable",
        family_name="Deletable",
        formatted_name="Deletable User",
        emails=["deletable@test.test"],
    )
    backend.save(user)
    token = models.Token(
        token_id=gen_salt(48),
        access_token=gen_salt(48),
        subject=user,
        audience=[oidc_client],
        client=oidc_client,
        refresh_token=gen_salt(48),
        scope=["openid", "profile"],
        issue_date=datetime.datetime.now(datetime.timezone.utc),
        lifetime=3600,
    )
    backend.save(token)

    client = Client(app)
    response = client.delete("/scim/v2/Me", headers=_scim_headers(app, token))
    assert response.status_code == 204

    assert not backend.get(models.User, user.id)


def test_delete_me_without_permission(app, backend, user, user_token):
    """DELETE /Me without DELETE_ACCOUNT permission returns 403."""
    client = Client(app)
    response = client.delete("/scim/v2/Me", headers=_scim_headers(app, user_token))
    assert response.status_code == 403


def test_replace_me_without_edit_self_permission(app, backend, user, user_token):
    """PUT /Me without EDIT_SELF permission returns 403."""
    app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"].remove(Permission.EDIT_SELF)
    backend.reload(user)
    client = Client(app)
    headers = _scim_headers(app, user_token)

    get_response = client.get("/scim/v2/Me", headers=headers)
    payload = get_response.get_json()
    for key in ("id", "meta", "photos", "groups"):
        payload.pop(key, None)

    response = client.put("/scim/v2/Me", data=json.dumps(payload), headers=headers)
    assert response.status_code == 403


def test_patch_me_without_edit_self_permission(app, backend, user, user_token):
    """PATCH /Me without EDIT_SELF permission returns 403."""
    app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"].remove(Permission.EDIT_SELF)
    backend.reload(user)
    client = Client(app)
    headers = _scim_headers(app, user_token)
    payload = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {"op": "replace", "path": "title", "value": "CTO"},
        ],
    }
    response = client.patch("/scim/v2/Me", data=json.dumps(payload), headers=headers)
    assert response.status_code == 403


def test_get_me_returns_etag(app, backend, user, user_token):
    """GET /Me includes an ETag header."""
    client = Client(app)
    response = client.get("/scim/v2/Me", headers=_scim_headers(app, user_token))
    assert response.status_code == 200
    assert response.headers.get("ETag") == make_etag(user)
