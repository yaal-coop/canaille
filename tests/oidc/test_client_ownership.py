"""Tests for client ownership feature."""

import uuid
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from urllib.parse import parse_qs
from urllib.parse import urlsplit

from joserfc import jwt
from werkzeug.security import gen_salt

from canaille.app import models
from canaille.app.session import UserSession
from canaille.oidc.jose import get_alg_for_key
from canaille.oidc.jose import registry
from canaille.oidc.jose import server_jwks
from canaille.oidc.provider import get_issuer
from tests.htmx import combobox_values
from tests.htmx import pick_in_combobox
from tests.htmx import remove_from_combobox

from . import client_credentials


def test_user_with_manage_own_clients_can_access_client_list(testclient, logged_user):
    """User with manage_own_clients permission can access client list."""
    res = testclient.get("/admin/client", status=200)
    assert res.template == "oidc/client_list.html"


def test_user_with_manage_own_clients_can_create_client(
    testclient, logged_user, backend
):
    """User with manage_own_clients can create a client that they own."""
    res = testclient.get("/admin/client/add")
    data = {
        "client_name": "my-client",
        "contacts-0": "user@test.com",
        "client_uri": "https://myclient.test",
        "redirect_uris-0": "https://myclient.test/callback",
    }
    for k, v in data.items():
        res.forms["clientaddform"][k].force_value(v)

    res = res.forms["clientaddform"].submit(status=302, name="action", value="add")
    res = res.follow(status=200)

    client_id = res.forms["readonly"]["client_id"].value
    client = backend.get(models.Client, client_id=client_id)

    assert client.client_name == "my-client"
    assert logged_user in client.owners

    backend.delete(client)


def test_user_owns_the_clients_they_add(testclient, logged_user):
    """A user who cannot manage all clients is an owner of the clients they add."""
    res = testclient.get("/admin/client/add")
    assert combobox_values(res.forms["clientaddform"], "owners") == [
        f"user:{logged_user.id}"
    ]


def test_user_only_finds_their_groups(testclient, logged_user, admin, backend):
    """A user who cannot manage all clients only finds the groups they own."""
    own_group = models.Group(
        display_name="shared-mine", members=[logged_user], owners=[logged_user]
    )
    other_group = models.Group(display_name="shared-theirs", members=[admin])
    backend.save(own_group)
    backend.save(other_group)

    res = testclient.get("/admin/client/add")
    form = res.forms["clientaddform"]
    form["owners-query"] = "shared"
    res = form.submit("owners-search")
    res.mustcontain(f"group:{own_group.id}", no=[f"group:{other_group.id}"])

    form["owners-query"] = "admin"
    res = form.submit("owners-search")
    res.mustcontain(no=[f"user:{admin.id}"])

    backend.delete(own_group)
    backend.delete(other_group)


def test_user_with_manage_own_clients_can_edit_own_client(
    testclient, logged_user, backend
):
    """User with manage_own_clients can edit a client they own."""
    client = models.Client(
        client_id=gen_salt(24),
        client_name="user-client",
        client_uri="https://client.test",
        redirect_uris=["https://client.test/callback"],
        grant_types=["authorization_code"],
        response_types=["code"],
        scope=["openid", "profile"],
        token_endpoint_auth_method="client_secret_basic",
        owners=[logged_user],
    )
    backend.save(client)

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res.forms["clienteditform"]["client_name"] = "renamed-client"
    res = res.forms["clienteditform"].submit(status=302, name="action", value="edit")

    backend.reload(client)
    assert client.client_name == "renamed-client"

    backend.delete(client)


def test_user_cannot_edit_other_users_client(testclient, logged_user, admin, backend):
    """User with manage_own_clients cannot edit another user's client."""
    client = models.Client(
        client_id=gen_salt(24),
        client_name="admin-client",
        owners=[admin],
    )
    backend.save(client)

    testclient.get(f"/admin/client/edit/{client.client_id}", status=403)

    backend.delete(client)


def test_user_cannot_edit_global_client(testclient, logged_user, backend):
    """User with manage_own_clients cannot edit a global client."""
    client = models.Client(
        client_id=gen_salt(24),
        client_name="global-client",
        owners=[],
    )
    backend.save(client)

    testclient.get(f"/admin/client/edit/{client.client_id}", status=403)

    backend.delete(client)


def test_user_only_sees_own_clients_in_list(
    testclient, logged_user, admin, backend, client
):
    """User with manage_own_clients only sees their own clients in the list."""
    user_client = models.Client(
        client_id=gen_salt(24),
        client_name="user-owned-client",
        owners=[logged_user],
    )
    admin_client = models.Client(
        client_id=gen_salt(24),
        client_name="admin-owned-client",
        owners=[admin],
    )
    backend.save(user_client)
    backend.save(admin_client)

    res = testclient.get("/admin/client", status=200)
    res.mustcontain("user-owned-client")
    res.mustcontain(no="admin-owned-client")
    res.mustcontain(no=client.client_name)

    backend.delete(user_client)
    backend.delete(admin_client)


def test_user_can_delete_own_client(testclient, logged_user, backend):
    """User with manage_own_clients can delete a client they own."""
    client = models.Client(
        client_id=gen_salt(24),
        client_name="to-delete",
        owners=[logged_user],
    )
    backend.save(client)
    client_id = client.client_id

    res = testclient.get(f"/admin/client/edit/{client_id}", status=200)
    res = res.forms["clienteditform"].submit(name="action", value="confirm-delete")
    res = res.form.submit(name="action", value="delete")
    res = res.follow()

    assert not backend.get(models.Client, client_id=client_id)


def test_admin_can_create_global_client(testclient, logged_admin, backend):
    """Admin can create a global client (owners = [])."""
    res = testclient.get("/admin/client/add")
    data = {
        "client_name": "global-client",
        "contacts-0": "admin@test.com",
        "client_uri": "https://global.test",
        "redirect_uris-0": "https://global.test/callback",
    }
    for k, v in data.items():
        res.forms["clientaddform"][k].force_value(v)

    res = res.forms["clientaddform"].submit(status=302, name="action", value="add")
    res = res.follow(status=200)

    client_id = res.forms["readonly"]["client_id"].value
    client = backend.get(models.Client, client_id=client_id)

    assert client.client_name == "global-client"
    assert client.owners == []

    backend.delete(client)


def test_admin_can_assign_owner_to_client(testclient, logged_admin, user, backend):
    """Admin can create a client with a specific owner."""
    res = testclient.get("/admin/client/add")
    data = {
        "client_name": "user-owned-by-admin",
        "contacts-0": "admin@test.com",
        "client_uri": "https://owned.test",
        "redirect_uris-0": "https://owned.test/callback",
    }
    for k, v in data.items():
        res.forms["clientaddform"][k].force_value(v)

    res = pick_in_combobox(
        res.forms["clientaddform"], "owners", "John", f"user:{user.id}"
    )
    res = res.forms["clientaddform"].submit(status=302, name="action", value="add")
    res = res.follow(status=200)

    client_id = res.forms["readonly"]["client_id"].value
    client = backend.get(models.Client, client_id=client_id)

    assert client.owners == [user]

    backend.delete(client)


def test_admin_can_change_client_owners(testclient, logged_admin, user, admin, backend):
    """Admin can change the owners of an existing client."""
    client = models.Client(
        client_id=gen_salt(24),
        client_name="change-owner-test",
        client_uri="https://test.example",
        redirect_uris=["https://test.example/callback"],
        grant_types=["authorization_code"],
        response_types=["code"],
        scope=["openid", "profile"],
        token_endpoint_auth_method="client_secret_basic",
        owners=[admin],
    )
    backend.save(client)

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res = remove_from_combobox(
        res.forms["clienteditform"], "owners", f"user:{admin.id}"
    )
    res = pick_in_combobox(
        res.forms["clienteditform"], "owners", "John", f"user:{user.id}"
    )
    res = res.forms["clienteditform"].submit(status=302, name="action", value="edit")

    backend.reload(client)
    assert client.owners == [user]

    backend.delete(client)


def test_owner_displayed_after_save(testclient, logged_admin, user, backend):
    """Owner should be correctly displayed in the form after saving."""
    client = models.Client(
        client_id=gen_salt(24),
        client_name="display-owner-test",
        client_uri="https://test.example",
        redirect_uris=["https://test.example/callback"],
        grant_types=["authorization_code"],
        response_types=["code"],
        scope=["openid", "profile"],
        token_endpoint_auth_method="client_secret_basic",
        owners=[],
    )
    backend.save(client)

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res = pick_in_combobox(
        res.forms["clienteditform"], "owners", "John", f"user:{user.id}"
    )
    res = res.forms["clienteditform"].submit(status=302, name="action", value="edit")

    res = res.follow(status=200)
    assert combobox_values(res.forms["clienteditform"], "owners") == [f"user:{user.id}"]
    res.mustcontain("John (johnny) Doe")

    backend.delete(client)


def test_admin_sees_all_clients_in_list(
    testclient, logged_admin, user, backend, client
):
    """Admin sees all clients in the list (owned and global)."""
    user_client = models.Client(
        client_id=gen_salt(24),
        client_name="user-client-in-list",
        owners=[user],
    )
    global_client = models.Client(
        client_id=gen_salt(24),
        client_name="global-client-in-list",
        owners=[],
    )
    backend.save(user_client)
    backend.save(global_client)

    res = testclient.get("/admin/client", status=200)
    res.mustcontain("user-client-in-list")
    res.mustcontain("global-client-in-list")
    res.mustcontain(client.client_name)

    backend.delete(user_client)
    backend.delete(global_client)


def test_owner_can_use_owned_client(testclient, logged_user, backend):
    """Client owner can initiate authorization with their client."""
    client = models.Client(
        client_id=gen_salt(24),
        client_secret=gen_salt(48),
        client_name="owned-client-auth",
        redirect_uris=["https://owned.test/callback"],
        owners=[logged_user],
        grant_types=["authorization_code"],
        response_types=["code"],
        scope=["openid", "profile"],
    )
    backend.save(client)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            redirect_uri="https://owned.test/callback",
            nonce="somenonce",
        ),
        status=200,
    )
    assert res.template == "oidc/authorize.html"

    backend.delete(client)


def test_non_owner_cannot_use_owned_client(testclient, logged_user, admin, backend):
    """Non-owner cannot initiate authorization with an owned client.

    They are not redirected to the client, as its owner chose its redirection URIs.
    """
    client = models.Client(
        client_id=gen_salt(24),
        client_secret=gen_salt(48),
        client_name="restricted-client",
        redirect_uris=["https://restricted.test/callback"],
        owners=[admin],
        grant_types=["authorization_code"],
        response_types=["code"],
        scope=["openid", "profile"],
    )
    backend.save(client)

    testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            redirect_uri="https://restricted.test/callback",
            nonce="somenonce",
            state="foobar",
        ),
        status=403,
    )
    assert not backend.query(models.AuthorizationCode, client=client)

    backend.delete(client)


def test_any_user_can_use_global_client(testclient, logged_user, backend):
    """Any user with USE_OIDC permission can use a global client."""
    client = models.Client(
        client_id=gen_salt(24),
        client_secret=gen_salt(48),
        client_name="global-for-all",
        redirect_uris=["https://global.test/callback"],
        owners=[],
        grant_types=["authorization_code"],
        response_types=["code"],
        scope=["openid", "profile"],
    )
    backend.save(client)

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid profile",
            redirect_uri="https://global.test/callback",
            nonce="somenonce",
        ),
        status=200,
    )
    assert res.template == "oidc/authorize.html"

    backend.delete(client)


def test_dynamic_registration_creates_global_client(testclient, backend):
    """Test dynamic client registration creates global client (owners=[])."""
    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    client_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    exp = now + timedelta(hours=1)

    jwt_payload = {
        "iss": get_issuer(),
        "sub": client_id,
        "aud": get_issuer(),
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "scope": "client:register",
    }

    token = jwt.encode({"alg": alg}, jwt_payload, jwk_key, registry=registry)

    payload = {
        "redirect_uris": ["https://global-reg.test/callback"],
        "client_name": "Global Registered Client",
    }
    headers = {"Authorization": f"Bearer {token}"}

    res = testclient.post_json("/oauth/register", payload, headers=headers, status=201)
    created_client = backend.get(models.Client, client_id=res.json["client_id"])

    assert created_client.owners == []

    backend.delete(created_client)


def test_owner_deletion_deletes_the_client(testclient, backend):
    """Deleting the last owner of a client deletes the client."""
    owner_user = models.User(
        user_name="temp-owner",
        formatted_name="Temp Owner",
        family_name="Owner",
        emails=["temp@owner.test"],
        password="password",
    )
    backend.save(owner_user)

    client = models.Client(
        client_id=gen_salt(24),
        client_name="orphan-client",
        owners=[owner_user],
    )
    backend.save(client)

    backend.delete(owner_user)

    assert not backend.get(models.Client, client_id=client.client_id)


def test_owner_deletion_keeps_the_client_with_other_owners(
    testclient, backend, user, admin
):
    """Deleting an owner of a client with other owners keeps the client."""
    owner_user = models.User(
        user_name="temp-owner",
        formatted_name="Temp Owner",
        family_name="Owner",
        emails=["temp@owner.test"],
        password="password",
    )
    backend.save(owner_user)

    client = models.Client(
        client_id=gen_salt(24),
        client_name="shared-client",
        owners=[owner_user, admin],
    )
    backend.save(client)

    backend.delete(owner_user)

    client = backend.get(models.Client, client_id=client.client_id)
    assert client.owners == [admin]

    backend.delete(client)


def test_group_owner_deletion_deletes_the_client(testclient, backend, user):
    """Deleting the last owner group of a client deletes the client."""
    group = models.Group(display_name="temp-group", members=[user])
    backend.save(group)

    client = models.Client(
        client_id=gen_salt(24),
        client_name="group-client",
        owners=[group],
    )
    backend.save(client)

    backend.delete(group)

    assert not backend.get(models.Client, client_id=client.client_id)


def test_user_cannot_see_registration_token(testclient, logged_user):
    """Regular user should not see registration token on client add page."""
    res = testclient.get("/admin/client/add")
    assert "registration-token" not in res.text


def test_user_cannot_see_management_token(testclient, logged_user, backend):
    """Regular user should not see management token on client edit page."""
    client = models.Client(
        client_id=gen_salt(24),
        client_name="no-mgmt-token",
        owners=[logged_user],
    )
    backend.save(client)

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    assert "management-token" not in res.text

    backend.delete(client)


def test_admin_sees_registration_token(testclient, logged_admin):
    """Admin should see registration token on client add page."""
    res = testclient.get("/admin/client/add")
    assert "registration-token" in res.text


def test_admin_sees_management_token(testclient, logged_admin, client):
    """Admin should see management token on client edit page."""
    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    assert "management-token" in res.text


def test_is_editable_by_method(backend, user, admin):
    """Test the is_editable_by method of Client model."""
    user_client = models.Client(
        client_id=gen_salt(24),
        client_name="user-client",
        owners=[user],
    )
    admin_client = models.Client(
        client_id=gen_salt(24),
        client_name="admin-client",
        owners=[admin],
    )
    global_client = models.Client(
        client_id=gen_salt(24),
        client_name="global-client",
        owners=[],
    )
    backend.save(user_client)
    backend.save(admin_client)
    backend.save(global_client)

    assert user_client.is_editable_by(user)
    assert not admin_client.is_editable_by(user)
    assert not global_client.is_editable_by(user)
    assert user_client.is_editable_by(admin)
    assert admin_client.is_editable_by(admin)
    assert global_client.is_editable_by(admin)

    backend.delete(user_client)
    backend.delete(admin_client)
    backend.delete(global_client)


def test_is_editable_by_without_manage_own_clients_permission(
    testclient, backend, user
):
    """Test that is_editable_by returns False when user lacks manage_own_clients permission."""
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"].remove(
        "manage_own_clients"
    )
    backend.reload(user)

    client = models.Client(
        client_id=gen_salt(24),
        client_name="test-client",
        owners=[user],
    )
    backend.save(client)

    assert not client.is_editable_by(user)

    backend.delete(client)


def test_is_usable_by_method(backend, user, admin):
    """Test the is_usable_by method of Client model."""
    user_client = models.Client(
        client_id=gen_salt(24),
        client_name="user-client",
        owners=[user],
    )
    admin_client = models.Client(
        client_id=gen_salt(24),
        client_name="admin-client",
        owners=[admin],
    )
    global_client = models.Client(
        client_id=gen_salt(24),
        client_name="global-client",
        owners=[],
    )
    backend.save(user_client)
    backend.save(admin_client)
    backend.save(global_client)

    assert user_client.is_usable_by(user)
    assert not admin_client.is_usable_by(user)
    assert global_client.is_usable_by(user)
    assert admin_client.is_usable_by(admin)
    assert global_client.is_usable_by(admin)
    assert not user_client.is_usable_by(admin)

    backend.delete(user_client)
    backend.delete(admin_client)
    backend.delete(global_client)


def test_user_without_permission_cannot_access_client_list(testclient, logged_user):
    """User without manage_oidc or manage_own_clients cannot access client list."""
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = ["use_oidc"]
    logged_user._permissions = None
    testclient.get("/admin/client", status=403)


def test_user_without_permission_cannot_add_client(testclient, logged_user):
    """User without manage_oidc or manage_own_clients cannot add a client."""
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"] = ["use_oidc"]
    logged_user._permissions = None
    testclient.get("/admin/client/add", status=403)


def test_is_usable_by_without_use_oidc_permission(backend, user):
    """Test that is_usable_by returns False when user lacks USE_OIDC permission."""
    from werkzeug.security import gen_salt

    client = models.Client(
        client_id=gen_salt(24),
        client_name="test-client",
        owners=[],
    )
    backend.save(client)

    user._permissions = set()

    assert not client.is_usable_by(user)

    backend.delete(client)


def test_group_owner_allows_group_owner_to_edit(backend, user, admin):
    """Test that the owner of a group can edit a client owned by that group."""
    # Remove manage_oidc to test group ownership logic
    user._permissions = {"use_oidc", "manage_own_clients", "manage_own_groups"}
    admin._permissions = {"use_oidc", "manage_own_clients", "manage_own_groups"}

    group = models.Group(display_name="test-group-edit", members=[admin], owners=[user])
    backend.save(group)

    client = models.Client(
        client_id=gen_salt(24),
        client_name="group-owned-client",
        owners=[group],
    )
    backend.save(client)

    assert client.is_editable_by(user)
    assert not client.is_editable_by(admin)

    backend.delete(client)
    backend.delete(group)


def test_group_owner_allows_member_to_use(backend, user, admin):
    """Test that a member of a group can use a client owned by that group."""
    group = models.Group(display_name="test-group-use", members=[user], owners=[admin])
    backend.save(group)
    backend.reload(user)
    backend.reload(admin)

    # Remove manage_oidc to test group ownership logic (after reload which resets _permissions)
    user._permissions = {"use_oidc", "manage_own_clients"}
    admin._permissions = {"use_oidc", "manage_own_clients"}

    client = models.Client(
        client_id=gen_salt(24),
        client_name="group-owned-client",
        owners=[group],
    )
    backend.save(client)

    assert client.is_usable_by(user)
    assert not client.is_usable_by(admin)

    backend.delete(client)
    backend.delete(group)


def test_group_owner_semantic_distinction(backend, user, admin):
    """Test that group owner can edit but not use, member can use but not edit."""
    group = models.Group(
        display_name="test-group-semantic", members=[admin], owners=[user]
    )
    backend.save(group)
    backend.reload(user)
    backend.reload(admin)

    # Remove manage_oidc to test group ownership logic (after reload which resets _permissions)
    user._permissions = {"use_oidc", "manage_own_clients", "manage_own_groups"}
    admin._permissions = {"use_oidc", "manage_own_clients", "manage_own_groups"}

    client = models.Client(
        client_id=gen_salt(24),
        client_name="group-owned-client",
        owners=[group],
    )
    backend.save(client)

    # user owns the group: can edit, cannot use (not a member)
    assert client.is_editable_by(user)
    assert not client.is_usable_by(user)

    # admin is member of the group: can use, cannot edit (not the group owner)
    assert not client.is_editable_by(admin)
    assert client.is_usable_by(admin)

    backend.delete(client)
    backend.delete(group)


def test_mixed_user_and_group_owners(backend, user, admin):
    """Test client with both user and group owners."""
    group = models.Group(
        display_name="admin-group-mixed", members=[admin], owners=[admin]
    )
    backend.save(group)
    backend.reload(user)
    backend.reload(admin)

    # Remove manage_oidc to test group ownership logic (after reload which resets _permissions)
    user._permissions = {"use_oidc", "manage_own_clients", "manage_own_groups"}
    admin._permissions = {"use_oidc", "manage_own_clients", "manage_own_groups"}

    client = models.Client(
        client_id=gen_salt(24),
        client_name="mixed-owners-client",
        owners=[user, group],
    )
    backend.save(client)

    # user is direct owner: can edit and use
    assert client.is_editable_by(user)
    assert client.is_usable_by(user)

    # admin is group owner and member: can edit (group owner) and use (group member)
    assert client.is_editable_by(admin)
    assert client.is_usable_by(admin)

    backend.delete(client)
    backend.delete(group)


def test_owner_suggestions_tell_users_and_groups_apart(
    testclient, logged_admin, backend, admin
):
    """A user and a group with the same name are suggested separately."""
    ambiguous_user = models.User(
        user_name="ambiguous",
        formatted_name="ambiguous",
        family_name="User",
        emails=["ambiguous@user.test"],
        password="password",
    )
    backend.save(ambiguous_user)
    ambiguous_group = models.Group(display_name="ambiguous", members=[admin])
    backend.save(ambiguous_group)

    res = testclient.get("/admin/client/add")
    data = {
        "client_name": "test-ambiguous",
        "contacts-0": "admin@test.com",
        "client_uri": "https://ambiguous.test",
        "redirect_uris-0": "https://ambiguous.test/callback",
    }
    for k, v in data.items():
        res.forms["clientaddform"][k].force_value(v)

    form = res.forms["clientaddform"]
    form["owners-query"] = "ambiguous"
    res = form.submit("owners-search")
    res.mustcontain("ambiguous (ambiguous@user.test)", "ambiguous (group)")

    res = res.forms["clientaddform"].submit(
        "owners-suggestions", value=f"group:{ambiguous_group.id}"
    )
    res = res.forms["clientaddform"].submit(status=302, name="action", value="add")
    res = res.follow(status=200)

    client_id = res.forms["readonly"]["client_id"].value
    client = backend.get(models.Client, client_id=client_id)
    assert client.owners == [ambiguous_group]

    backend.delete(client)
    backend.delete(ambiguous_user)
    backend.delete(ambiguous_group)


def test_non_owner_cannot_use_password_grant(testclient, user, admin, client, backend):
    """A user who cannot use a client gets no token through the password grant.

    The error is the same with a right and a wrong password.
    """
    client.owners = [admin]
    backend.save(client)

    responses = [
        testclient.post(
            "/oauth/token",
            params=dict(
                grant_type="password",
                username="user",
                password=password,
                scope="openid profile",
            ),
            headers={"Authorization": f"Basic {client_credentials(client)}"},
            status=400,
        ).json
        for password in ("correct horse battery staple", "wrong password")
    ]
    assert responses[0] == responses[1]
    assert not backend.query(models.Token, client=client, subject=user)


def test_removed_owner_cannot_refresh_token(testclient, admin, client, token, backend):
    """A user who cannot use a client anymore cannot refresh their tokens."""
    client.owners = [admin]
    backend.save(client)

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="refresh_token",
            refresh_token=token.refresh_token,
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json["error"] == "invalid_grant"


def test_user_client_list_pages_only_count_own_clients(
    testclient, logged_user, admin, backend
):
    """The pages of the client list of a user only count the clients they own."""
    clients = [
        models.Client(client_id=gen_salt(24), client_name=gen_salt(24), owners=[admin])
        for _ in range(26)
    ]
    for client in clients:
        backend.save(client)

    res = testclient.get("/admin/client")
    testclient.post(
        "/admin/client",
        {"csrf_token": res.forms["tableform"]["csrf_token"].value, "page": "2"},
        status=404,
    )

    for client in clients:
        backend.delete(client)


def test_owners_displayed_to_user(testclient, logged_user, bar_group, backend):
    """A user who is not an administrator sees the user and group owners."""
    client = models.Client(
        client_id=gen_salt(24),
        client_name="shared-client",
        redirect_uris=["https://shared.test/callback"],
        owners=[logged_user, bar_group],
    )
    backend.save(client)

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    assert combobox_values(res.forms["clienteditform"], "owners") == [
        f"user:{logged_user.id}",
        f"group:{bar_group.id}",
    ]
    res.mustcontain(logged_user.formatted_name, "bar (group)")

    backend.delete(client)


def test_owner_deletion_without_oidc_keeps_the_client(
    testclient, backend, user, monkeypatch
):
    """Without OIDC, deleting an owner does not touch the clients."""
    client = models.Client(
        client_id=gen_salt(24),
        client_name="owned-client",
        owners=[user],
    )
    backend.save(client)

    monkeypatch.setitem(testclient.app.config["CANAILLE_OIDC"], "ENABLE_OIDC", False)
    backend.delete(user)

    client = backend.get(models.Client, client_id=client.client_id)
    assert client.owners == []
    backend.delete(client)


def test_owned_client_cannot_use_client_credentials(testclient, user, client, backend):
    """An owned client gets no token through the client credentials grant."""
    client.owners = [user]
    backend.save(client)

    res = testclient.post(
        "/oauth/token",
        params=dict(grant_type="client_credentials", scope="openid"),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json["error"] == "unauthorized_client"


def test_owned_client_grant_types(backend, user, client):
    """Owned clients cannot use the grants that issue tokens without a user consent."""
    assert client.check_grant_type("client_credentials")
    assert client.check_grant_type("urn:ietf:params:oauth:grant-type:jwt-bearer")

    client.owners = [user]

    assert not client.check_grant_type("client_credentials")
    assert not client.check_grant_type("urn:ietf:params:oauth:grant-type:jwt-bearer")
    assert client.check_grant_type("authorization_code")
    assert client.check_grant_type("password")


def test_user_cannot_pick_forbidden_grant_types(testclient, logged_user, backend):
    """A user cannot pick the client credentials and JWT bearer grants."""
    client = models.Client(
        client_id=gen_salt(24),
        client_name="owned-client",
        client_uri="https://owned.test",
        redirect_uris=["https://owned.test/callback"],
        grant_types=["authorization_code"],
        response_types=["code"],
        scope=["openid"],
        token_endpoint_auth_method="client_secret_basic",
        owners=[logged_user],
    )
    backend.save(client)

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    choices = [
        value for value, *_ in res.forms["clienteditform"]["grant_types"].options
    ]
    assert "authorization_code" in choices
    assert "client_credentials" not in choices
    assert "urn:ietf:params:oauth:grant-type:jwt-bearer" not in choices

    backend.delete(client)


def test_admin_cannot_give_forbidden_grant_types_to_owned_client(
    testclient, logged_admin, user, backend
):
    """An administrator cannot give the client credentials grant to an owned client."""
    client = models.Client(
        client_id=gen_salt(24),
        client_name="owned-client",
        client_uri="https://owned.test",
        redirect_uris=["https://owned.test/callback"],
        grant_types=["authorization_code"],
        response_types=["code"],
        scope=["openid"],
        token_endpoint_auth_method="client_secret_basic",
        owners=[user],
    )
    backend.save(client)

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res.forms["clienteditform"]["grant_types"] = [
        "authorization_code",
        "client_credentials",
    ]
    res = res.forms["clienteditform"].submit(status=200, name="action", value="edit")
    assert (
        "error",
        "The client has not been edited. Please check your information.",
    ) in res.flashes

    backend.reload(client)
    assert client.grant_types == ["authorization_code"]

    backend.delete(client)


def test_owned_client_is_never_trusted(testclient, backend, user):
    """An owned client always displays the consent page, even on a trusted domain."""
    client = models.Client(
        client_id=gen_salt(24),
        client_name="owned-client",
        client_uri="https://owned.localhost",
        redirect_uris=["https://owned.localhost/callback"],
    )
    assert client.trusted

    client.owners = [user]
    assert not client.trusted


def test_unknown_owner_is_rejected(testclient, logged_admin, backend):
    """Owner values that match no user nor group are refused."""
    res = testclient.get("/admin/client/add")
    form = res.forms["clientaddform"]
    res = testclient.post(
        "/admin/client/add",
        [
            ("csrf_token", form.get("csrf_token", index=0).value),
            ("client_name", "unknown-owner"),
            ("client_uri", "https://unknown.test"),
            ("redirect_uris-0", "https://unknown.test/callback"),
            ("owners-value", "user:unknown"),
            ("owners-value", "robot:unknown"),
            ("action", "add"),
        ],
        status=200,
    )
    assert (
        "error",
        "The client has not been added. Please check your information.",
    ) in res.flashes
    res.mustcontain("user:unknown")
    assert not backend.query(models.Client, client_name="unknown-owner")


def form_data(form, *extra):
    """Return the values that ``form`` sends, without its buttons, plus ``extra``."""
    return [
        *(
            (field.name, field.value)
            for name, fields in form.fields.items()
            for field in fields
            if name and field.value is not None and name != "action"
        ),
        *extra,
    ]


def user_owned_client(backend, owners):
    client = models.Client(
        client_id=gen_salt(24),
        client_name="shared-client",
        client_uri="https://shared.test",
        redirect_uris=["https://shared.test/callback"],
        grant_types=["authorization_code"],
        response_types=["code"],
        scope=["openid"],
        token_endpoint_auth_method="client_secret_basic",
        owners=owners,
    )
    backend.save(client)
    return client


def test_user_can_share_a_client_with_their_group(testclient, logged_user, backend):
    """A user can share a client they own with a group they own."""
    group = models.Group(
        display_name="mine", members=[logged_user], owners=[logged_user]
    )
    backend.save(group)
    client = user_owned_client(backend, [logged_user])

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res = pick_in_combobox(
        res.forms["clienteditform"], "owners", "mine", f"group:{group.id}"
    )
    res = res.forms["clienteditform"].submit(status=302, name="action", value="edit")

    backend.reload(client)
    assert client.owners == [logged_user, group]

    backend.delete(client)
    backend.delete(group)


def test_user_can_leave_a_client_owned_by_their_group(testclient, logged_user, backend):
    """A user can stop being an owner when a group they own still owns the client."""
    group = models.Group(
        display_name="mine", members=[logged_user], owners=[logged_user]
    )
    backend.save(group)
    client = user_owned_client(backend, [logged_user, group])

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res = remove_from_combobox(
        res.forms["clienteditform"], "owners", f"user:{logged_user.id}"
    )
    res = res.forms["clienteditform"].submit(status=302, name="action", value="edit")

    backend.reload(client)
    assert client.owners == [group]

    backend.delete(client)
    backend.delete(group)


def test_user_cannot_lose_the_edition_of_a_client(testclient, logged_user, backend):
    """A user cannot remove the last owner that lets them edit the client."""
    client = user_owned_client(backend, [logged_user])

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res = remove_from_combobox(
        res.forms["clienteditform"], "owners", f"user:{logged_user.id}"
    )
    res = res.forms["clienteditform"].submit(status=200, name="action", value="edit")
    res.mustcontain("You would not be able to edit this client anymore.")

    backend.reload(client)
    assert client.owners == [logged_user]

    backend.delete(client)


def test_user_cannot_add_other_users(testclient, logged_user, admin, backend):
    """A user cannot add another user as an owner, even with a forged value."""
    client = user_owned_client(backend, [logged_user])

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res = testclient.post(
        f"/admin/client/edit/{client.client_id}",
        form_data(
            res.forms["clienteditform"],
            ("owners-value", f"user:{admin.id}"),
            ("action", "edit"),
        ),
        status=200,
    )
    res.mustcontain(
        "You can only add the groups you own, and remove yourself or the groups you own."
    )

    backend.reload(client)
    assert client.owners == [logged_user]

    backend.delete(client)


def test_user_cannot_remove_other_owners(testclient, logged_user, admin, backend):
    """A user cannot remove an owner they do not control."""
    client = user_owned_client(backend, [logged_user, admin])

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res = remove_from_combobox(
        res.forms["clienteditform"], "owners", f"user:{admin.id}"
    )
    res = res.forms["clienteditform"].submit(status=200, name="action", value="edit")
    res.mustcontain(
        "You can only add the groups you own, and remove yourself or the groups you own."
    )

    backend.reload(client)
    assert client.owners == [logged_user, admin]

    backend.delete(client)


def test_owners_description_for_users(testclient, logged_user):
    """The owners field does not mention global clients to the users who cannot make one."""
    res = testclient.get("/admin/client/add")
    res.mustcontain(
        "You and the groups you own that own this client.",
        no=["Leave empty for a global client"],
    )


def test_owners_description_for_administrators(testclient, logged_admin):
    """The owners field tells the administrators how to make a global client."""
    res = testclient.get("/admin/client/add")
    res.mustcontain("Leave empty for a global client")


def test_admin_can_pick_the_audience(testclient, logged_admin, trusted_client, backend):
    """An administrator can add any client to the audience of a client."""
    client = user_owned_client(backend, [])
    client.audience = [client]
    backend.save(client)

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res = pick_in_combobox(
        res.forms["clienteditform"], "audience", "other", trusted_client.id
    )
    res = res.forms["clienteditform"].submit(status=302, name="action", value="edit")

    backend.reload(client)
    assert client.audience == [client, trusted_client]

    backend.delete(client)


def test_user_only_finds_the_clients_they_can_edit(
    testclient, logged_user, trusted_client, backend
):
    """A user only finds the clients they can edit for the audience."""
    client = user_owned_client(backend, [logged_user])
    other = user_owned_client(backend, [logged_user])
    other.client_name = "shared-other"
    backend.save(other)

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    form = res.forms["clienteditform"]
    form["audience-query"] = "other"
    res = form.submit("audience-search")
    res.mustcontain(other.id, no=[trusted_client.id])

    backend.delete(client)
    backend.delete(other)


def test_user_cannot_add_other_clients_to_the_audience(
    testclient, logged_user, trusted_client, backend
):
    """A user cannot add a client they cannot edit to the audience, even with a forged value."""
    client = user_owned_client(backend, [logged_user])

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res = testclient.post(
        f"/admin/client/edit/{client.client_id}",
        form_data(
            res.forms["clienteditform"],
            ("audience-value", trusted_client.id),
            ("action", "edit"),
        ),
        status=200,
    )
    res.mustcontain("You can only add or remove the clients you can edit.")

    backend.reload(client)
    assert trusted_client not in client.audience

    backend.delete(client)


def test_user_cannot_remove_other_clients_from_the_audience(
    testclient, logged_user, trusted_client, backend
):
    """A user cannot remove a client they cannot edit from the audience."""
    client = user_owned_client(backend, [logged_user])
    client.audience = [trusted_client]
    backend.save(client)

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res = remove_from_combobox(
        res.forms["clienteditform"], "audience", trusted_client.id
    )
    res = res.forms["clienteditform"].submit(status=200, name="action", value="edit")
    res.mustcontain("You can only add or remove the clients you can edit.")

    backend.reload(client)
    assert client.audience == [trusted_client]

    backend.delete(client)


def test_unknown_audience_is_rejected(testclient, logged_admin, backend):
    """An audience value that matches no client is refused."""
    client = user_owned_client(backend, [])

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res = testclient.post(
        f"/admin/client/edit/{client.client_id}",
        form_data(
            res.forms["clienteditform"],
            ("audience-value", "unknown"),
            ("action", "edit"),
        ),
        status=200,
    )
    res.mustcontain("unknown")
    assert (
        "error",
        "The client has not been edited. Please check your information.",
    ) in res.flashes

    backend.delete(client)


def test_removed_owner_tokens_are_refused_at_userinfo(
    testclient, admin, client, token, backend
):
    """The access tokens of a user who cannot use a client anymore are refused."""
    testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token.access_token}"},
        status=200,
    )

    client.owners = [admin]
    backend.save(client)

    res = testclient.get(
        "/oauth/userinfo",
        headers={"Authorization": f"Bearer {token.access_token}"},
        status=401,
    )
    assert res.json["error"] == "invalid_token"


def test_removed_owner_tokens_are_inactive(testclient, admin, client, token, backend):
    """The introspection tells the tokens of a user who cannot use a client anymore are inactive."""
    client.owners = [admin]
    backend.save(client)

    res = testclient.post(
        "/oauth/introspect",
        params={"token": token.access_token},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )
    assert res.json == {"active": False}


def test_query_clients_by_owners(testclient, backend, user, admin, foo_group):
    """Clients can be queried by one owner, or by any owner of a list."""
    user_client = user_owned_client(backend, [user])
    group_client = user_owned_client(backend, [foo_group])
    admin_client = user_owned_client(backend, [admin])

    assert backend.query(models.Client, owners=user) == [user_client]
    assert backend.query(models.Client, owners=foo_group) == [group_client]
    assert set(backend.query(models.Client, owners=[user, foo_group])) == {
        user_client,
        group_client,
    }

    for client in (user_client, group_client, admin_client):
        backend.delete(client)


def test_user_cannot_create_access_tokens(testclient, logged_user, backend):
    """A user who cannot manage all clients cannot create tokens without a user."""
    client = user_owned_client(backend, [logged_user])

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    assert "new-access-token" not in res.text

    testclient.post(
        f"/admin/client/edit/{client.client_id}",
        form_data(res.forms["clienteditform"], ("action", "new-access-token")),
        status=403,
    )
    assert not backend.query(models.Token, client=client)

    backend.delete(client)


def test_token_without_user_of_an_owned_client_is_revoked(backend, user, client):
    """Tokens without a user are refused for clients with owners."""
    token = models.Token(
        token_id=gen_salt(48),
        access_token=gen_salt(48),
        client=client,
        scope=["openid"],
        issue_date=datetime.now(UTC),
        lifetime=3600,
    )
    assert not token.is_revoked()

    client.owners = [user]
    assert token.is_revoked()


def test_user_can_add_consentable_scopes(testclient, logged_user, backend):
    """A user can add the scopes that users consent to."""
    client = user_owned_client(backend, [logged_user])

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res.forms["clienteditform"]["scope"] = "openid profile email scim:me"
    res.forms["clienteditform"].submit(status=302, name="action", value="edit")

    backend.reload(client)
    assert client.scope == ["openid", "profile", "email", "scim:me"]

    backend.delete(client)


def test_user_cannot_add_privileged_scopes(testclient, logged_user, backend):
    """A user cannot add the scopes that no user consents to."""
    client = user_owned_client(backend, [logged_user])

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res.mustcontain("You can pick among: address email groups openid phone profile")
    res.forms["clienteditform"]["scope"] = "openid scim:write scim:read"
    res = res.forms["clienteditform"].submit(status=200, name="action", value="edit")
    res.mustcontain("You cannot add the scim:read, scim:write scopes.")

    backend.reload(client)
    assert client.scope == ["openid"]

    backend.delete(client)


def test_user_keeps_the_scopes_an_administrator_added(testclient, logged_user, backend):
    """A user can edit a client that has scopes they could not add."""
    client = user_owned_client(backend, [logged_user])
    client.scope = ["openid", "scim:read"]
    backend.save(client)

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res.forms["clienteditform"]["client_name"] = "renamed"
    res.forms["clienteditform"].submit(status=302, name="action", value="edit")

    backend.reload(client)
    assert client.client_name == "renamed"
    assert client.scope == ["openid", "scim:read"]

    backend.delete(client)


def test_admin_can_add_any_scope(testclient, logged_admin, user, backend):
    """An administrator can add any scope to an owned client."""
    client = user_owned_client(backend, [user])

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res.forms["clienteditform"]["scope"] = "openid scim:read"
    res.forms["clienteditform"].submit(status=302, name="action", value="edit")

    backend.reload(client)
    assert client.scope == ["openid", "scim:read"]

    backend.delete(client)


def test_user_finds_the_client_pages_in_the_menu(testclient, logged_user):
    """A user who can manage their clients sees the menu entry, but not the tokens."""
    res = testclient.get("/consent", status=200)
    res.mustcontain('href="/admin/client/"')

    res = testclient.get("/admin/client", status=200)
    res.mustcontain(no='href="/admin/token/"')


def test_admin_finds_the_token_pages(testclient, logged_admin):
    """An administrator sees the tokens tab."""
    res = testclient.get("/admin/client", status=200)
    res.mustcontain('href="/admin/token/"')


def test_removed_owner_cannot_exchange_their_code(
    testclient, user, admin, client, backend
):
    """A user who cannot use a client anymore gets no token for their authorization code."""
    code = models.AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code=gen_salt(48),
        client=client,
        subject=user,
        redirect_uri="https://client.test/redirect1",
        response_type="code",
        scope=["openid", "profile"],
        issue_date=datetime.now(UTC),
        lifetime=300,
    )
    backend.save(code)
    client.owners = [admin]
    backend.save(client)

    res = testclient.post(
        "/oauth/token",
        params=dict(
            grant_type="authorization_code",
            code=code.code,
            redirect_uri=code.redirect_uri,
        ),
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json["error"] == "invalid_grant"
    assert not backend.query(models.Token, client=client, subject=user)

    backend.delete(code)


def test_admin_cannot_create_access_tokens_for_owned_clients(
    testclient, logged_admin, user, backend
):
    """Tokens without a user are refused for owned clients, so they cannot be created."""
    client = user_owned_client(backend, [user])

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    assert "new-access-token" not in res.text

    testclient.post(
        f"/admin/client/edit/{client.client_id}",
        form_data(res.forms["clienteditform"], ("action", "new-access-token")),
        status=403,
    )
    assert not backend.query(models.Token, client=client)

    backend.delete(client)


def test_group_deletion_deletes_the_clients_of_the_group(
    testclient, logged_user, backend
):
    """Deleting a group deletes the clients it is the last owner of.

    This also applies when the user cannot edit those clients.
    """
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"].remove(
        "manage_own_clients"
    )
    backend.reload(logged_user)
    group = models.Group(
        display_name="mine", members=[logged_user], owners=[logged_user]
    )
    backend.save(group)
    client = user_owned_client(backend, [group])

    res = testclient.get(f"/groups/{group.id}", status=200)
    res = res.forms["editgroupform"].submit(name="action", value="confirm-delete")
    res.form.submit(name="action", value="delete", status=302)

    assert not backend.get(models.Group, id=group.id)
    assert not backend.get(models.Client, id=client.id)


def test_user_cannot_add_themself_back(testclient, logged_user, backend):
    """A user who left a client owned by their group cannot become an owner again.

    Otherwise they would keep the edition of the client after losing the group.
    """
    group = models.Group(
        display_name="mine", members=[logged_user], owners=[logged_user]
    )
    backend.save(group)
    client = user_owned_client(backend, [group])

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    res = testclient.post(
        f"/admin/client/edit/{client.client_id}",
        form_data(
            res.forms["clienteditform"],
            ("owners-value", f"user:{logged_user.id}"),
            ("action", "edit"),
        ),
        status=200,
    )
    res.mustcontain(
        "You can only add the groups you own, and remove yourself or the groups you own."
    )

    backend.reload(client)
    assert client.owners == [group]

    backend.delete(client)
    backend.delete(group)


def test_duplicate_owners_are_merged(testclient, logged_user, backend):
    """An owner sent twice is saved once."""
    client = user_owned_client(backend, [logged_user])

    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    testclient.post(
        f"/admin/client/edit/{client.client_id}",
        form_data(
            res.forms["clienteditform"],
            ("owners-value", f"user:{logged_user.id}"),
            ("action", "edit"),
        ),
        status=302,
    )

    backend.reload(client)
    assert client.owners == [logged_user]

    backend.delete(client)


def test_non_owner_is_not_redirected_on_errors(testclient, logged_user, admin, backend):
    """Invalid requests do not redirect a user who cannot use the client to it."""
    client = user_owned_client(backend, [admin])

    for params in (
        dict(code_challenge="challenge", code_challenge_method="invalid"),
        dict(prompt="invalid"),
    ):
        testclient.get(
            "/oauth/authorize",
            params=dict(
                response_type="code",
                client_id=client.client_id,
                scope="openid",
                redirect_uri="https://shared.test/callback",
                **params,
            ),
            status=403,
        )

    backend.delete(client)


def test_user_cannot_renew_registration_tokens(testclient, logged_user, backend):
    """A user who cannot manage all clients cannot renew the registration tokens."""
    res = testclient.get("/admin/client/add", status=200)
    testclient.post(
        "/admin/client/add",
        form_data(res.forms["clientaddform"], ("action", "new-registration-token")),
        status=403,
    )

    client = user_owned_client(backend, [logged_user])
    res = testclient.get(f"/admin/client/edit/{client.client_id}", status=200)
    testclient.post(
        f"/admin/client/edit/{client.client_id}",
        form_data(res.forms["clienteditform"], ("action", "new-management-token")),
        status=403,
    )

    backend.delete(client)


def test_non_owner_can_select_another_account(testclient, user, admin, backend):
    """A user who cannot use a client can switch to an account that can."""
    client = user_owned_client(backend, [admin])
    consent = models.Consent(
        consent_id=str(uuid.uuid4()), client=client, subject=admin, scope=["openid"]
    )
    backend.save(consent)

    with testclient.session_transaction() as sess:
        sess["sessions"] = [
            UserSession(user=user, last_login_datetime=datetime.now(UTC)).serialize(),
            UserSession(
                user=admin, last_login_datetime=datetime.now(UTC) - timedelta(minutes=1)
            ).serialize(),
        ]

    params = dict(
        response_type="code",
        client_id=client.client_id,
        scope="openid",
        nonce="somenonce",
        redirect_uri="https://shared.test/callback",
    )
    testclient.get("/oauth/authorize", params=params, status=403)

    res = testclient.get(
        "/oauth/authorize", params=dict(params, prompt="select_account"), status=302
    )
    res = res.follow()
    assert res.template == "core/login.html"

    res = testclient.get(f"/login/{admin.user_name}", status=302).follow()
    assert "code" in parse_qs(urlsplit(res.location).query)

    backend.delete(consent)
    backend.delete(client)


def test_non_owner_cannot_select_their_own_account(
    testclient, logged_user, admin, backend
):
    """A user who cannot use a client cannot go through with their own account.

    They are not redirected to the client, even when the request is invalid.
    """
    client = user_owned_client(backend, [admin])

    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid",
            nonce="somenonce",
            redirect_uri="https://shared.test/callback",
            prompt="select_account",
            code_challenge="challenge",
            code_challenge_method="invalid",
        ),
        status=302,
    ).follow()
    assert res.template == "core/login.html"
    testclient.get(f"/login/{logged_user.user_name}", status=302).follow(status=403)
    assert not backend.query(models.AuthorizationCode, client=client)

    backend.delete(client)


def test_owned_client_logout_needs_confirmation(
    testclient, logged_user, client, id_token, backend
):
    """Users confirm the logout before being redirected to an owned client."""
    client.owners = [logged_user]
    backend.save(client)

    post_logout_redirect_url = "https://client.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": id_token,
            "client_id": client.client_id,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=200,
    )
    res = res.form.submit(name="answer", value="logout", status=302)
    assert res.location == f"{post_logout_redirect_url}?state=foobar"


def test_owned_client_logout_without_session(
    testclient, user, client, id_token, backend
):
    """Logged out users are not redirected to an owned client."""
    client.owners = [user]
    backend.save(client)

    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": id_token,
            "client_id": client.client_id,
            "post_logout_redirect_uri": "https://client.test/disconnected",
        },
        status=302,
    )
    assert not res.location.startswith("https://client.test")


def test_group_owner_without_manage_own_groups(testclient, logged_user, backend):
    """A group owner without MANAGE_OWN_GROUPS gets no rights on the clients of the group."""
    testclient.app.config["CANAILLE"]["ACL"]["DEFAULT"]["PERMISSIONS"].remove(
        "manage_own_groups"
    )
    backend.reload(logged_user)
    group = models.Group(
        display_name="mine", members=[logged_user], owners=[logged_user]
    )
    backend.save(group)
    client = user_owned_client(backend, [group])

    assert not client.is_editable_by(logged_user)
    testclient.get(f"/admin/client/edit/{client.client_id}", status=403)
    res = testclient.get("/admin/client", status=200)
    res.mustcontain(no=client.client_id)

    own_client = user_owned_client(backend, [logged_user])
    res = testclient.get(f"/admin/client/edit/{own_client.client_id}", status=200)
    form = res.forms["clienteditform"]
    form["owners-query"] = "mine"
    res = form.submit("owners-search")
    res.mustcontain(no=f"group:{group.id}")

    res = testclient.post(
        f"/admin/client/edit/{own_client.client_id}",
        form_data(
            res.forms["clienteditform"],
            ("owners-value", f"group:{group.id}"),
            ("action", "edit"),
        ),
        status=200,
    )
    backend.reload(own_client)
    assert own_client.owners == [logged_user]

    backend.delete(own_client)
    backend.delete(client)
    backend.delete(group)


def test_non_owner_is_refused_before_unsupported_response_types(
    testclient, logged_user, admin, backend
):
    """An unsupported response type does not redirect a user who cannot use the client."""
    client = user_owned_client(backend, [admin])
    testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="unsupported",
            client_id=client.client_id,
            scope="openid",
            nonce="somenonce",
            redirect_uri="https://shared.test/callback",
        ),
        status=403,
    )
    backend.delete(client)


def test_select_account_in_request_object(
    testclient, logged_user, admin, client, client_jwk, backend
):
    """A user who cannot use a client can select another account from a request object."""
    client.owners = [admin]
    backend.save(client)
    request_obj = jwt.encode(
        {"alg": "RS256"},
        dict(
            response_type="code",
            client_id=client.client_id,
            scope="openid",
            nonce="somenonce",
            redirect_uri=client.redirect_uris[0],
            prompt="select_account",
        ),
        client_jwk,
    )
    res = testclient.get(
        "/oauth/authorize",
        params=dict(client_id=client.client_id, request=request_obj),
        status=302,
    ).follow()
    assert res.template == "core/login.html"


def test_unsupported_response_type_for_logged_out_users(testclient, client):
    """Logged out users are redirected to the client for unsupported response types."""
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="unsupported",
            client_id=client.client_id,
            scope="openid",
            nonce="somenonce",
            redirect_uri=client.redirect_uris[0],
        ),
        status=302,
    )
    assert res.location.startswith(client.redirect_uris[0])
    assert parse_qs(urlsplit(res.location).query)["error"] == [
        "unsupported_response_type"
    ]
