import datetime
import json
from unittest import mock

import pytest
from scim2_client.engines.werkzeug import TestSCIMClient
from scim2_models import Error
from werkzeug.security import gen_salt
from werkzeug.test import Client

from canaille.app import models
from canaille.scim.endpoints import bp


def test_authentication_failure(app, scim_provider):
    """Test authentication with an invalid token."""
    scim_client = TestSCIMClient(
        Client(app),
        scim_prefix=bp.url_prefix,
        environ={
            "headers": {
                "Authorization": "Bearer invalid",
                "Host": app.config["SERVER_NAME"],
            }
        },
        provider=scim_provider,
    )
    User = scim_client.get_resource_model("User")
    error = scim_client.query(User, raise_scim_errors=False)
    assert isinstance(error, Error)
    assert not error.scim_type
    assert error.status == 401


def test_authentication_with_an_user_token_without_permission(
    app, backend, oidc_client, user, scim_provider
):
    """Test that a user token without MANAGE_USERS permission is rejected on /Users."""
    scim_token = models.Token(
        token_id=gen_salt(48),
        access_token=gen_salt(48),
        subject=user,
        audience=[oidc_client],
        client=oidc_client,
        refresh_token=gen_salt(48),
        scope=["openid", "profile"],
        issue_date=datetime.datetime.now(datetime.UTC),
        lifetime=3600,
    )
    backend.save(scim_token)

    scim_client = TestSCIMClient(
        Client(app),
        scim_prefix=bp.url_prefix,
        environ={
            "headers": {
                "Authorization": f"Bearer {scim_token.access_token}",
                "Host": app.config["SERVER_NAME"],
            }
        },
        provider=scim_provider,
    )
    User = scim_client.get_resource_model("User")
    error = scim_client.query(User, raise_scim_errors=False)
    assert isinstance(error, Error)
    assert error.status == 403


def test_missing_field(app, backend, scim_client):
    """Test that SCIM API returns a 400 error when extra fields are provided in the request."""
    scim_client.discover()
    error = scim_client.create(
        {"foo": "bar"},
        url="/Users",
        check_request_payload=False,
        raise_scim_errors=False,
    )
    assert isinstance(error, Error)
    assert error.detail == "Extra inputs are not permitted: foo"
    assert error.status == 400


def test_query_user_with_empty_profile_url(app, backend, scim_client):
    """Test that querying users does not crash when a user has an empty profile_url."""
    from canaille.app import models

    scim_client.discover()
    User = scim_client.get_resource_model("User")

    u = models.User(
        user_name="noprofile",
        emails=["noprofile@test.test"],
        family_name="noprofile",
        formatted_name="noprofile",
        profile_url="",
    )
    backend.save(u)

    response = scim_client.query(User)
    assert any(r.user_name == "noprofile" for r in response.resources)
    assert all(
        r.profile_url is None for r in response.resources if r.user_name == "noprofile"
    )

    backend.delete(u)


def test_invalid_payload(app, backend, scim_client):
    """Test that SCIM API returns an invalidValue error when creating a user with an empty payload."""
    # TODO: push this test in scim2-tester
    scim_client.discover()
    User = scim_client.get_resource_model("User")
    error = scim_client.create(
        User,
        {"schemas": [User.__schema__]},
        check_request_payload=False,
        url="/Users",
        raise_scim_errors=False,
    )
    assert isinstance(error, Error)
    assert error.scim_type == "invalidValue"
    assert error.status == 400


@pytest.mark.parametrize(
    "path", ["/ServiceProviderConfig", "/ResourceTypes", "/Schemas"]
)
def test_discovery_needs_no_token(app, path):
    """The discovery endpoints answer without a token."""
    response = Client(app).get(
        f"/scim/v2{path}", headers={"Host": app.config["SERVER_NAME"]}
    )
    assert response.status_code == 200


def test_resources_need_a_token(app):
    """The resources need a token, and the 401 response tells how to get one."""
    response = Client(app).get(
        "/scim/v2/Users", headers={"Host": app.config["SERVER_NAME"]}
    )
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"].startswith("Bearer")


def test_internal_error(app, backend, oidc_token, caplog):
    """An unexpected error gives a 500 SCIM error, and is logged."""
    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "alice",
        "name": {"formatted": "Alice", "familyName": "Alice"},
        "active": True,
    }
    with mock.patch(
        "canaille.backends.Backend.instance.save",
        side_effect=Exception("Database error"),
    ):
        response = Client(app).post(
            "/scim/v2/Users",
            data=json.dumps(payload),
            headers={
                "Authorization": f"Bearer {oidc_token.access_token}",
                "Host": app.config["SERVER_NAME"],
                "Content-Type": "application/scim+json",
            },
        )
    assert response.status_code == 500
    assert response.json["detail"] == "Internal server error"
    assert "Database error" in caplog.text
