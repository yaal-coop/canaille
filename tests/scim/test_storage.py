import json

import pytest
from scim2_models import ForbiddenException
from scim2_models import PreconditionFailedException
from scim2_models import UniquenessException
from scim2_server.handler import ScimHandler
from scim2_server.requests import ScimRequest
from scim2_server.service import ScimService
from scim2_server.testing import ScimStorageContract

from canaille.app import models
from canaille.scim.models import EnterpriseUser
from canaille.scim.models import Group
from canaille.scim.models import Name
from canaille.scim.models import User
from canaille.scim.models import get_provider
from canaille.scim.storage import CanailleStorage

LDAP_LIMITS = {
    "test_create_fills_the_identifier_and_the_meta": "LDAP creation dates are precise to the second only",
    "test_create_does_not_change_the_given_resource": "LDAP users need a name",
    "test_search_a_resource_type": "LDAP groups cannot be empty",
    "test_search_at_the_root": "LDAP groups cannot be empty",
    "test_search_at_the_root_on_an_attribute_some_types_lack": "LDAP groups cannot be empty",
}


@pytest.fixture
def storage(oidc_token, clean_backend):
    return CanailleStorage(oidc_token)


@pytest.fixture
def user_type(app):
    return get_provider().resource_types[0]


@pytest.fixture
def group_type(app):
    return get_provider().resource_types[1]


class TestCanailleStorage(ScimStorageContract):
    @pytest.fixture
    def provider(self, app):
        return get_provider()

    @pytest.fixture
    def storage(self, backend, storage):
        """Start from an empty storage, as the contract expects."""
        for model in (models.User, models.Group):
            for instance in backend.query(model):
                backend.delete(instance)
        return storage

    @pytest.fixture(autouse=True)
    def ldap_limits(self, request, backend):
        reason = LDAP_LIMITS.get(request.node.originalname)
        if reason and backend.__class__.__name__ == "LDAPBackend":
            request.applymarker(pytest.mark.xfail(reason=reason, strict=True))

    def create_users(self, storage, user_type, user_model, *user_names):
        """Give the users a name, as LDAP requires one."""
        return [
            storage.create(
                user_type,
                user_model(
                    user_name=user_name,
                    name=Name(formatted=user_name, family_name=user_name),
                ),
            )
            for user_name in user_names
        ]


def make_user(storage, user_type, user_name, **kwargs):
    return storage.create(
        user_type,
        User[EnterpriseUser](
            user_name=user_name,
            name=Name(formatted=user_name, family_name=user_name),
            **kwargs,
        ),
    )


def test_group_members_are_identified_by_id(storage, user, foo_group, group_type):
    """Group members are given by id, and their reference uses the id."""
    group = storage.get(group_type, foo_group.id)

    assert [member.value for member in group.members] == [user.id]
    assert group.members[0].ref == f"Users/{user.id}"


def test_user_groups_reference_uses_the_id(storage, user, foo_group, user_type):
    """The reference to the groups of a user uses the group id."""
    scim_user = storage.get(user_type, user.id)

    assert scim_user.groups[0].ref == f"Groups/{foo_group.id}"


def test_group_members_accept_a_user_name(storage, user_type, group_type):
    """A member given by its user name is still found."""
    alice = make_user(storage, user_type, "alice")

    group = storage.create(
        group_type,
        Group(display_name="admins", members=[Group.Members(value="alice")]),
    )

    assert [member.value for member in group.members] == [alice.id]


def test_create_with_a_taken_group_name(storage, user_type, group_type):
    """A group displayName already taken, whatever its case, raises a 409."""
    alice = make_user(storage, user_type, "alice")
    members = [Group.Members(value=alice.id)]
    storage.create(group_type, Group(display_name="admins", members=members))

    with pytest.raises(UniquenessException):
        storage.create(group_type, Group(display_name="Admins", members=members))


def test_create_without_active_does_not_lock(backend, storage, user_type):
    """A user created without the active attribute is not locked."""
    alice = make_user(storage, user_type, "alice")

    assert not backend.get(models.User, id=alice.id).locked


def test_search_at_the_root_pages_across_resource_types(
    backend, storage, user_type, group_type
):
    """A page at the root can hold the last users and the first groups."""
    alice = make_user(storage, user_type, "alice")
    members = [Group.Members(value=alice.id)]
    storage.create(group_type, Group(display_name="admins", members=members))
    users = backend.count(models.User)
    groups = backend.count(models.Group)

    total, resources = storage.search(
        [user_type, group_type],
        TestCanailleStorage.search_request(
            [User[EnterpriseUser], Group], start_index=users, count=2
        ),
    )

    assert total == users + groups
    assert [r.meta.resource_type for r in resources] == ["User", "Group"]


def test_subject_cannot_modify_fields_out_of_the_write_acl(
    app, backend, user, user_token, user_type, clean_backend
):
    """A user cannot modify their own fields that the WRITE ACL does not list."""
    app.config["CANAILLE"]["ACL"]["DEFAULT"]["WRITE"].remove("title")
    backend.reload(user)
    storage = CanailleStorage(user_token)
    scim_user = storage.get(user_type, user.id)
    scim_user.title = "CEO"

    with pytest.raises(ForbiddenException):
        storage.update(user_type, scim_user)
    backend.reload(user)
    assert user.title == "Dr."


def test_subject_can_modify_fields_of_the_write_acl(
    backend, user, user_token, user_type, clean_backend
):
    """A user can modify their own fields that the WRITE ACL lists."""
    storage = CanailleStorage(user_token)
    scim_user = storage.get(user_type, user.id)
    scim_user.display_name = "Jo"

    storage.update(user_type, scim_user)

    backend.reload(user)
    assert user.display_name == "Jo"


def test_write_acl_only_applies_to_the_subject(app, backend, user, storage, user_type):
    """A client can modify the fields that the WRITE ACL of the user does not list."""
    app.config["CANAILLE"]["ACL"]["DEFAULT"]["WRITE"].remove("title")
    backend.reload(user)
    scim_user = storage.get(user_type, user.id)
    scim_user.title = "CEO"

    storage.update(user_type, scim_user)

    backend.reload(user)
    assert user.title == "CEO"


def test_replace_without_password_keeps_the_password(
    app, backend, user, storage, user_type
):
    """A PUT without a password does not change the password."""
    handler = ScimHandler(ScimService(get_provider()), storage)
    body = {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
        ],
        "userName": "user",
        "name": {"formatted": "John Doe", "familyName": "Doe", "givenName": "John"},
        "active": True,
    }

    response = handler.handle(
        ScimRequest(
            method="PUT",
            base_url="https://canaille.test/scim/v2",
            path=f"/Users/{user.id}",
            headers={"Content-Type": "application/scim+json"},
            body=json.dumps(body).encode(),
        )
    )

    assert int(response.status) == 200
    backend.reload(user)
    assert user.formatted_name == "John Doe"
    assert backend.check_user_password(user, "correct horse battery staple")[0]


def test_update_with_a_wrong_version(storage, user_type):
    """An update raises a 412 when the expected version is not the stored one."""
    alice = make_user(storage, user_type, "alice")

    with pytest.raises(PreconditionFailedException):
        storage.update(user_type, alice, expected_version='W/"wrong"')


def test_search_at_the_root_stops_before_the_groups(
    backend, storage, user_type, group_type
):
    """A page that ends among the users holds no group."""
    make_user(storage, user_type, "alice")

    _, resources = storage.search(
        [user_type, group_type],
        TestCanailleStorage.search_request(
            [User[EnterpriseUser], Group], start_index=1, count=1
        ),
    )

    assert [r.meta.resource_type for r in resources] == ["User"]
