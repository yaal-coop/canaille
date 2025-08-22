import json

from canaille.scim.endpoints import bp


def test_patch_user_replace_simple_attribute(
    app, backend, oidc_token, user, scim_client
):
    """Test PATCH operation to replace a simple user attribute."""
    patch_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "replace", "path": "title", "value": "Senior Developer"}],
    }
    response = scim_client.client.patch(
        f"{bp.url_prefix}/Users/{user.id}",
        json=patch_data,
        headers={"Authorization": f"Bearer {oidc_token.access_token}"},
    )

    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data["title"] == "Senior Developer"

    backend.reload(user)
    assert user.title == "Senior Developer"


def test_patch_user_add_email(app, backend, oidc_token, user, scim_client):
    """Test PATCH operation to add an email to a user."""
    patch_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "path": "emails",
                "value": [{"value": "newemail@example.com"}],
            }
        ],
    }

    response = scim_client.client.patch(
        f"{bp.url_prefix}/Users/{user.id}",
        json=patch_data,
        headers={"Authorization": f"Bearer {oidc_token.access_token}"},
    )

    assert response.status_code == 200
    response_data = json.loads(response.data)

    emails = response_data.get("emails", [])
    email_values = [email["value"] for email in emails]
    assert "newemail@example.com" in email_values

    backend.reload(user)
    assert "newemail@example.com" in user.emails


def test_patch_user_remove_attribute(app, backend, oidc_token, user, scim_client):
    """Test PATCH operation to remove an attribute from a user."""
    user.title = "Manager"
    backend.save(user)

    patch_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "remove", "path": "title"}],
    }

    response = scim_client.client.patch(
        f"{bp.url_prefix}/Users/{user.id}",
        json=patch_data,
        headers={"Authorization": f"Bearer {oidc_token.access_token}"},
    )

    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert "title" not in response_data or response_data["title"] is None

    backend.reload(user)
    assert user.title is None


def test_patch_user_multiple_operations(app, backend, oidc_token, user, scim_client):
    """Test PATCH with multiple operations in a single request."""
    patch_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {"op": "replace", "path": "title", "value": "CTO"},
            {"op": "add", "path": "preferredLanguage", "value": "en-US"},
        ],
    }

    response = scim_client.client.patch(
        f"{bp.url_prefix}/Users/{user.id}",
        json=patch_data,
        headers={"Authorization": f"Bearer {oidc_token.access_token}"},
    )

    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data["title"] == "CTO"
    assert response_data["preferredLanguage"] == "en-US"

    backend.reload(user)
    assert user.title == "CTO"
    assert user.preferred_language == "en-US"


def test_patch_group_replace_members(
    app, backend, oidc_token, foo_group, user, moderator, scim_client
):
    """Test PATCH operation to replace members in a group."""
    foo_group.members = [user]
    backend.save(foo_group)

    patch_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "replace",
                "path": "members",
                "value": [
                    {
                        "value": moderator.id,
                        "display": moderator.display_name,
                    }
                ],
            }
        ],
    }

    response = scim_client.client.patch(
        f"{bp.url_prefix}/Groups/{foo_group.id}",
        json=patch_data,
        headers={"Authorization": f"Bearer {oidc_token.access_token}"},
    )

    assert response.status_code == 200
    response_data = json.loads(response.data)

    members = response_data.get("members", [])
    member_ids = [member["value"] for member in members]
    assert moderator.identifier in member_ids
    assert user.id not in member_ids

    backend.reload(foo_group)
    member_ids_persisted = [member.identifier for member in foo_group.members]
    assert moderator.identifier in member_ids_persisted
    assert user.identifier not in member_ids_persisted


def test_patch_group_add_invalid_member(
    app, backend, oidc_token, foo_group, user, scim_client
):
    """Test PATCH operation to add a member to a group."""
    foo_group.members = [user]
    backend.save(foo_group)

    patch_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "path": "members",
                "value": [
                    {
                        "value": "invalid",
                        "display": "http://invalid",
                    }
                ],
            }
        ],
    }

    response = scim_client.client.patch(
        f"{bp.url_prefix}/Groups/{foo_group.id}",
        json=patch_data,
        headers={"Authorization": f"Bearer {oidc_token.access_token}"},
    )

    assert response.status_code == 200
    response_data = json.loads(response.data)

    members = response_data.get("members", [])
    member_ids = [member["value"] for member in members]
    assert member_ids == [user.identifier]


def test_patch_group_add_member(
    app, backend, oidc_token, foo_group, user, moderator, scim_client
):
    """Test PATCH operation to add a member to a group."""
    foo_group.members = [user]
    backend.save(foo_group)

    patch_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "add",
                "path": "members",
                "value": [
                    {
                        "value": moderator.id,
                        "display": moderator.display_name,
                    }
                ],
            }
        ],
    }

    response = scim_client.client.patch(
        f"{bp.url_prefix}/Groups/{foo_group.id}",
        json=patch_data,
        headers={"Authorization": f"Bearer {oidc_token.access_token}"},
    )

    assert response.status_code == 200
    response_data = json.loads(response.data)

    members = response_data.get("members", [])
    member_ids = [member["value"] for member in members]
    assert user.identifier in member_ids
    assert moderator.identifier in member_ids

    backend.reload(foo_group)
    member_ids_persisted = [member.identifier for member in foo_group.members]
    assert user.identifier in member_ids_persisted
    assert moderator.identifier in member_ids_persisted


def test_patch_invalid_operation(app, backend, oidc_token, user, scim_client):
    """Test PATCH with an invalid operation type."""
    patch_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "invalid_operation", "path": "title", "value": "Test"}],
    }

    response = scim_client.client.patch(
        f"{bp.url_prefix}/Users/{user.id}",
        json=patch_data,
        headers={"Authorization": f"Bearer {oidc_token.access_token}"},
    )

    assert response.status_code == 400


def test_patch_user_no_modifications(app, backend, oidc_token, user, scim_client):
    """Test PATCH user that results in no modifications."""
    user.title = "Developer"
    backend.save(user)

    patch_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "replace",
                "path": "title",
                "value": "Developer",  # Same as current value
            }
        ],
    }

    response = scim_client.client.patch(
        f"{bp.url_prefix}/Users/{user.id}",
        json=patch_data,
        headers={"Authorization": f"Bearer {oidc_token.access_token}"},
    )

    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data["title"] == "Developer"

    backend.reload(user)
    assert user.title == "Developer"


def test_patch_group_no_modification(
    app, backend, oidc_token, foo_group, user, scim_client
):
    """Test PATCH user that results in no modifications."""
    foo_group.members = [user]
    backend.save(foo_group)

    patch_data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
                "op": "replace",
                "path": "displayName",
                "value": "foo",
            }
        ],
    }

    response = scim_client.client.patch(
        f"{bp.url_prefix}/Groups/{foo_group.id}",
        json=patch_data,
        headers={"Authorization": f"Bearer {oidc_token.access_token}"},
    )

    assert response.status_code == 200
    response_data = json.loads(response.data)

    members = response_data.get("members", [])
    member_ids = [member["value"] for member in members]
    assert user.identifier in member_ids
