import json

from werkzeug.test import Client

from canaille.scim.casting import make_etag


def _auth_headers(app, oidc_token):
    return {
        "Authorization": f"Bearer {oidc_token.access_token}",
        "Host": app.config["SERVER_NAME"],
        "Content-Type": "application/scim+json",
    }


def _get_user_payload(client, app, user, oidc_token):
    """Fetch the SCIM representation of a user to use as PUT payload."""
    response = client.get(
        f"/scim/v2/Users/{user.id}",
        headers=_auth_headers(app, oidc_token),
    )
    payload = response.get_json()
    for key in ("id", "meta", "photos", "groups"):
        payload.pop(key, None)
    return payload


def test_get_user_returns_etag_header(app, backend, user, oidc_token):
    """GET on a user resource includes an ETag header in the response."""
    client = Client(app)
    headers = _auth_headers(app, oidc_token)
    response = client.get(f"/scim/v2/Users/{user.id}", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("ETag")
    assert response.headers["ETag"] == make_etag(user)


def test_put_user_with_matching_etag(app, backend, user, oidc_token):
    """PUT with a correct If-Match ETag succeeds."""
    client = Client(app)
    headers = _auth_headers(app, oidc_token)
    payload = _get_user_payload(client, app, user, oidc_token)
    payload["displayName"] = "Updated Name"
    headers["If-Match"] = make_etag(user)
    response = client.put(
        f"/scim/v2/Users/{user.id}",
        data=json.dumps(payload),
        headers=headers,
    )
    assert response.status_code == 200
    assert response.get_json()["displayName"] == "Updated Name"


def test_put_user_with_wildcard_if_match(app, backend, user, oidc_token):
    """PUT with If-Match: * bypasses ETag comparison."""
    client = Client(app)
    headers = _auth_headers(app, oidc_token)
    payload = _get_user_payload(client, app, user, oidc_token)
    headers["If-Match"] = "*"
    response = client.put(
        f"/scim/v2/Users/{user.id}",
        data=json.dumps(payload),
        headers=headers,
    )
    assert response.status_code == 200


def test_put_user_with_mismatched_etag(app, backend, user, oidc_token):
    """PUT with an incorrect If-Match ETag returns 412 Precondition Failed."""
    client = Client(app)
    headers = _auth_headers(app, oidc_token)
    payload = _get_user_payload(client, app, user, oidc_token)
    headers["If-Match"] = 'W/"0000000000000000"'
    response = client.put(
        f"/scim/v2/Users/{user.id}",
        data=json.dumps(payload),
        headers=headers,
    )
    assert response.status_code == 412


def test_put_user_without_if_match(app, backend, user, oidc_token):
    """PUT without If-Match header proceeds without ETag verification."""
    client = Client(app)
    headers = _auth_headers(app, oidc_token)
    payload = _get_user_payload(client, app, user, oidc_token)
    response = client.put(
        f"/scim/v2/Users/{user.id}",
        data=json.dumps(payload),
        headers=headers,
    )
    assert response.status_code == 200
