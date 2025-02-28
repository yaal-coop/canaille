import logging
from unittest import mock

from scim2_models import EnterpriseUser
from scim2_models import SearchRequest

from canaille.app import models
from canaille.scim.client import user_from_canaille_to_scim_client
from canaille.scim.models import User as MyUser


def test_scim_client_user_save_and_delete(scim_client_for_trusted_client, backend):
    User = scim_client_for_trusted_client.get_resource_model("User")

    response = scim_client_for_trusted_client.query(User)
    assert not response.resources

    alice = models.User(
        formatted_name="Alice Alice",
        family_name="Alice",
        user_name="alice",
        emails=["john@doe.test", "johhny@doe.test"],
    )
    backend.save(alice)

    response = scim_client_for_trusted_client.query(User)
    assert len(response.resources) == 1
    assert response.resources[0].user_name == "alice"

    backend.delete(alice)
    response = scim_client_for_trusted_client.query(User)
    assert not response.resources


def test_scim_client_group_save_and_delete(
    scim_client_for_trusted_client, backend, user
):
    Group = scim_client_for_trusted_client.get_resource_model("Group")
    User = scim_client_for_trusted_client.get_resource_model("User")

    req = SearchRequest(filter=f'externalId eq "{user.id}"')
    response = scim_client_for_trusted_client.query(User, search_request=req)
    distant_scim_user = response.resources[0] if response.resources else None

    response = scim_client_for_trusted_client.query(Group)
    assert not response.resources

    group = models.Group(
        members=[user],
        display_name="foobar",
    )
    backend.save(group)

    response = scim_client_for_trusted_client.query(Group)
    assert len(response.resources) == 1
    retrieved_group = response.resources[0]
    assert retrieved_group.display_name == "foobar"
    assert retrieved_group.members[0].value == distant_scim_user.id

    backend.delete(group)
    response = scim_client_for_trusted_client.query(Group)
    assert not response.resources


def test_scim_client_group_save_unable_to_retrieve_member_via_scim(
    scim_client_for_trusted_client, backend, user, caplog
):
    Group = scim_client_for_trusted_client.get_resource_model("Group")
    User = scim_client_for_trusted_client.get_resource_model("User")

    req = SearchRequest(filter=f'externalId eq "{user.id}"')
    response = scim_client_for_trusted_client.query(User, search_request=req)
    distant_scim_user = response.resources[0] if response.resources else None

    response = scim_client_for_trusted_client.query(Group)
    assert not response.resources

    group = models.Group(
        members=[user],
        display_name="foobar",
    )
    backend.save(group)

    scim_client_for_trusted_client.delete(User, distant_scim_user.id)

    backend.save(group)

    assert (
        "canaille",
        logging.WARNING,
        "Unable to find user user from group foobar via SCIM",
    ) in caplog.record_tuples

    backend.delete(group)


def test_scim_client_change_user_groups_also_updates_group_members(
    testclient,
    scim_client_for_trusted_client,
    backend,
    user,
    logged_admin,
    bar_group,
):
    Group = scim_client_for_trusted_client.get_resource_model("Group")
    User = scim_client_for_trusted_client.get_resource_model("User")

    req = SearchRequest(filter=f'externalId eq "{user.id}"')
    response = scim_client_for_trusted_client.query(User, search_request=req)
    distant_scim_user = response.resources[0] if response.resources else None

    req = SearchRequest(filter=f'externalId eq "{logged_admin.id}"')
    response = scim_client_for_trusted_client.query(User, search_request=req)
    distant_scim_admin = response.resources[0] if response.resources else None

    user.groups = user.groups + [bar_group]
    backend.save(user)

    response = scim_client_for_trusted_client.query(Group)
    assert len(response.resources) == 1
    retrieved_bar_group = response.resources[0]
    assert retrieved_bar_group.display_name == "bar"
    assert len(retrieved_bar_group.members) == 2
    assert retrieved_bar_group.members[0].value == distant_scim_admin.id
    assert retrieved_bar_group.members[1].value == distant_scim_user.id

    user.groups = []
    backend.save(user)

    response = scim_client_for_trusted_client.query(Group)
    assert len(response.resources) == 1
    retrieved_bar_group = response.resources[0]
    assert retrieved_bar_group.display_name == "bar"
    assert len(retrieved_bar_group.members) == 1
    assert retrieved_bar_group.members[0].value == distant_scim_admin.id


def test_scim_client_user_creation_and_deletion_also_updates_their_groups(
    testclient,
    scim_client_for_trusted_client,
    backend,
    foo_group,
    bar_group,
    user,
    admin,
    logged_admin,
):
    testclient.app.config["CANAILLE"]["ENABLE_REGISTRATION"] = True
    testclient.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] = False

    Group = scim_client_for_trusted_client.get_resource_model("Group")
    User = scim_client_for_trusted_client.get_resource_model("User")

    req = SearchRequest(filter=f'externalId eq "{user.id}"')
    response = scim_client_for_trusted_client.query(User, search_request=req)
    distant_scim_user = response.resources[0] if response.resources else None

    req = SearchRequest(filter=f'externalId eq "{admin.id}"')
    response = scim_client_for_trusted_client.query(User, search_request=req)
    distant_scim_admin = response.resources[0] if response.resources else None

    response = scim_client_for_trusted_client.query(Group)
    assert len(response.resources) == 2
    retrieved_foo_group = response.resources[0]
    assert retrieved_foo_group.display_name == "foo"
    assert len(retrieved_foo_group.members) == 1
    assert retrieved_foo_group.members[0].value == distant_scim_user.id
    retrieved_bar_group = response.resources[1]
    assert retrieved_bar_group.display_name == "bar"
    assert len(retrieved_bar_group.members) == 1
    assert retrieved_bar_group.members[0].value == distant_scim_admin.id

    alice = models.User(
        formatted_name="Alice Alice",
        family_name="Alice",
        user_name="alice",
        emails=["john@doe.test", "johhny@doe.test"],
    )
    alice.groups = [bar_group, foo_group]
    backend.save(alice)

    req = SearchRequest(filter=f'externalId eq "{alice.id}"')
    response = scim_client_for_trusted_client.query(User, search_request=req)
    distant_scim_alice = response.resources[0] if response.resources else None

    response = scim_client_for_trusted_client.query(Group)
    assert len(response.resources) == 2
    retrieved_foo_group = response.resources[0]
    assert retrieved_foo_group.display_name == "foo"
    assert len(retrieved_foo_group.members) == 2
    assert retrieved_foo_group.members[0].value == distant_scim_user.id
    assert retrieved_foo_group.members[1].value == distant_scim_alice.id
    retrieved_bar_group = response.resources[1]
    assert retrieved_bar_group.display_name == "bar"
    assert len(retrieved_bar_group.members) == 2
    assert retrieved_bar_group.members[0].value == distant_scim_admin.id
    assert retrieved_bar_group.members[1].value == distant_scim_alice.id

    backend.delete(alice)

    response = scim_client_for_trusted_client.query(Group)
    assert len(response.resources) == 2
    retrieved_foo_group = response.resources[0]
    assert retrieved_foo_group.display_name == "foo"
    assert len(retrieved_foo_group.members) == 1
    assert retrieved_foo_group.members[0].value == distant_scim_user.id
    retrieved_bar_group = response.resources[1]
    assert retrieved_bar_group.display_name == "bar"
    assert len(retrieved_bar_group.members) == 1
    assert retrieved_bar_group.members[0].value == distant_scim_admin.id


def test_save_user_when_client_doesnt_support_scim(backend, user, consent, caplog):
    backend.save(user)
    assert (
        "canaille",
        logging.INFO,
        "SCIM protocol not supported by client Client",
    ) in caplog.record_tuples


def test_save_group_when_client_doesnt_support_scim(
    backend, bar_group, consent, caplog
):
    backend.save(bar_group)
    assert (
        "canaille",
        logging.INFO,
        "SCIM protocol not supported by client Client",
    ) in caplog.record_tuples


@mock.patch("scim2_client.engines.httpx.SyncSCIMClient.create")
def test_failed_scim_user_creation(
    scim_mock,
    testclient,
    scim_client_for_trusted_client,
    backend,
    caplog,
):
    scim_mock.side_effect = mock.Mock(side_effect=Exception())

    alice = models.User(
        formatted_name="Alice Alice",
        family_name="Alice",
        user_name="alice",
        emails=["john@doe.test", "johhny@doe.test"],
    )
    backend.save(alice)

    assert (
        "canaille",
        logging.WARNING,
        "SCIM User alice creation for client Some client failed",
    ) in caplog.record_tuples

    backend.delete(alice)


@mock.patch("scim2_client.engines.httpx.SyncSCIMClient.replace")
def test_failed_scim_user_update(
    scim_mock,
    testclient,
    scim_client_for_trusted_client,
    backend,
    caplog,
    user,
):
    scim_mock.side_effect = mock.Mock(side_effect=Exception())

    backend.save(user)

    assert (
        "canaille",
        logging.WARNING,
        "SCIM User user update for client Some client failed",
    ) in caplog.record_tuples


@mock.patch("scim2_client.engines.httpx.SyncSCIMClient.delete")
def test_failed_scim_user_delete(
    scim_mock,
    testclient,
    scim_client_for_trusted_client,
    backend,
    caplog,
    user,
):
    scim_mock.side_effect = mock.Mock(side_effect=Exception())

    backend.delete(user)

    assert (
        "canaille",
        logging.WARNING,
        "SCIM User user delete for client Some client failed",
    ) in caplog.record_tuples


@mock.patch("scim2_client.engines.httpx.SyncSCIMClient.create")
def test_failed_scim_group_creation(
    scim_mock,
    testclient,
    scim_client_for_trusted_client,
    backend,
    caplog,
    user,
):
    scim_mock.side_effect = mock.Mock(side_effect=Exception())

    group = models.Group(
        members=[user],
        display_name="foobar",
    )
    backend.save(group)

    assert (
        "canaille",
        logging.WARNING,
        "SCIM Group foobar creation for client Some client failed",
    ) in caplog.record_tuples

    backend.delete(group)


@mock.patch("scim2_client.engines.httpx.SyncSCIMClient.replace")
def test_failed_scim_group_update(
    scim_mock,
    testclient,
    scim_client_for_trusted_client,
    backend,
    caplog,
    bar_group,
):
    scim_mock.side_effect = mock.Mock(side_effect=Exception())

    backend.save(bar_group)

    assert (
        "canaille",
        logging.WARNING,
        "SCIM Group bar update for client Some client failed",
    ) in caplog.record_tuples


@mock.patch("scim2_client.engines.httpx.SyncSCIMClient.delete")
def test_failed_scim_group_delete(
    scim_mock,
    testclient,
    scim_client_for_trusted_client,
    backend,
    caplog,
    user,
):
    scim_mock.side_effect = mock.Mock(side_effect=Exception())

    group = models.Group(
        members=[user],
        display_name="foobar",
    )
    backend.save(group)

    backend.delete(group)

    assert (
        "canaille",
        logging.WARNING,
        "SCIM Group foobar delete for client Some client failed",
    ) in caplog.record_tuples


def test_user_from_canaille_to_scim_client_without_enterprise_user_extension(
    scim_client_for_trusted_client, user
):
    User = scim_client_for_trusted_client.get_resource_model("User")

    scim_user = user_from_canaille_to_scim_client(user, User, None)
    assert isinstance(scim_user, User)
    assert not isinstance(scim_user, MyUser[EnterpriseUser])
    assert EnterpriseUser not in scim_user
