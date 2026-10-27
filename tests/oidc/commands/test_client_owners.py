"""Tests for client owner management via CLI."""

import json

from canaille.app import models
from canaille.commands import cli


def test_create_client_with_user_owner(cli_runner, backend, user):
    """Create a client with a user owner."""
    res = cli_runner.invoke(
        cli,
        [
            "create",
            "client",
            "--client-id",
            "test-client",
            "--client-name",
            "Test Client",
            "--owners",
            user.user_name,
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.stdout)
    assert data["client_id"] == "test-client"
    assert data["client_name"] == "Test Client"
    assert len(data["owners"]) == 1
    assert data["owners"][0] == user.id

    client = backend.get(models.Client, client_id="test-client")
    assert client.owners == [user]

    backend.delete(client)


def test_create_client_with_group_owner(cli_runner, backend, user, foo_group):
    """Create a client with a group owner."""
    res = cli_runner.invoke(
        cli,
        [
            "create",
            "client",
            "--client-id",
            "test-client-group",
            "--client-name",
            "Test Client with Group",
            "--owners",
            foo_group.display_name,
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.stdout)
    assert data["client_id"] == "test-client-group"
    assert len(data["owners"]) == 1
    assert data["owners"][0] == foo_group.id

    client = backend.get(models.Client, client_id="test-client-group")
    assert client.owners == [foo_group]

    backend.delete(client)


def test_create_client_with_multiple_owners(cli_runner, backend, user, foo_group):
    """Create a client with both user and group owners."""
    res = cli_runner.invoke(
        cli,
        [
            "create",
            "client",
            "--client-id",
            "test-client-multi",
            "--client-name",
            "Test Client Multi Owners",
            "--owners",
            user.user_name,
            "--owners",
            foo_group.display_name,
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(res.stdout)
    assert len(data["owners"]) == 2

    client = backend.get(models.Client, client_id="test-client-multi")
    assert user in client.owners
    assert foo_group in client.owners

    backend.delete(client)


def test_create_client_with_prefixed_owner(cli_runner, backend, user):
    """Create a client with a prefixed owner identifier."""
    res = cli_runner.invoke(
        cli,
        [
            "create",
            "client",
            "--client-id",
            "test-client-prefix",
            "--client-name",
            "Test Client Prefixed",
            "--owners",
            f"user:{user.user_name}",
        ],
    )
    assert res.exit_code == 0, res.output

    client = backend.get(models.Client, client_id="test-client-prefix")
    assert client.owners == [user]

    backend.delete(client)


def test_create_client_ambiguous_owner(cli_runner, backend, admin):
    """Error when owner identifier is ambiguous."""
    # Create user and group with same identifier
    ambiguous_user = models.User(
        user_name="ambiguous",
        formatted_name="Ambiguous User",
        family_name="User",
        emails=["ambiguous@test.example"],
    )
    backend.save(ambiguous_user)

    ambiguous_group = models.Group(display_name="ambiguous", members=[admin])
    backend.save(ambiguous_group)

    res = cli_runner.invoke(
        cli,
        [
            "create",
            "client",
            "--client-id",
            "test-client-ambiguous",
            "--client-name",
            "Test Client Ambiguous",
            "--owners",
            "ambiguous",
        ],
    )
    assert res.exit_code != 0
    assert "Ambiguous identifier" in res.output

    backend.delete(ambiguous_user)
    backend.delete(ambiguous_group)


def test_create_client_disambiguate_with_prefix(cli_runner, backend, admin):
    """Use prefix to disambiguate ambiguous owner identifier."""
    ambiguous_user = models.User(
        user_name="ambiguous2",
        formatted_name="Ambiguous User 2",
        family_name="User",
        emails=["ambiguous2@test.example"],
    )
    backend.save(ambiguous_user)

    ambiguous_group = models.Group(display_name="ambiguous2", members=[admin])
    backend.save(ambiguous_group)

    # Use user prefix
    res = cli_runner.invoke(
        cli,
        [
            "create",
            "client",
            "--client-id",
            "test-client-user",
            "--client-name",
            "Test Client User",
            "--owners",
            "user:ambiguous2",
        ],
    )
    assert res.exit_code == 0, res.output
    client = backend.get(models.Client, client_id="test-client-user")
    assert client.owners == [ambiguous_user]
    backend.delete(client)

    # Use group prefix
    res = cli_runner.invoke(
        cli,
        [
            "create",
            "client",
            "--client-id",
            "test-client-grp",
            "--client-name",
            "Test Client Group",
            "--owners",
            "group:ambiguous2",
        ],
    )
    assert res.exit_code == 0, res.output
    client = backend.get(models.Client, client_id="test-client-grp")
    assert client.owners == [ambiguous_group]
    backend.delete(client)

    backend.delete(ambiguous_user)
    backend.delete(ambiguous_group)


def test_create_client_unknown_owner(cli_runner, backend):
    """Error when owner does not exist."""
    res = cli_runner.invoke(
        cli,
        [
            "create",
            "client",
            "--client-id",
            "test-client-unknown",
            "--client-name",
            "Test Client Unknown",
            "--owners",
            "nonexistent",
        ],
    )
    assert res.exit_code != 0
    assert "not found" in res.output


def test_set_client_owners(cli_runner, backend, user, foo_group, client):
    """Set owners on an existing client."""
    assert client.owners == []

    res = cli_runner.invoke(
        cli,
        [
            "set",
            "client",
            client.client_id,
            "--owners",
            user.user_name,
            "--owners",
            foo_group.display_name,
        ],
    )
    assert res.exit_code == 0, res.output

    backend.reload(client)
    assert user in client.owners
    assert foo_group in client.owners


def test_create_client_prefixed_unknown_owner(cli_runner, backend):
    """Error when prefixed owner does not exist."""
    res = cli_runner.invoke(
        cli,
        [
            "create",
            "client",
            "--client-id",
            "test-client-prefixed-unknown",
            "--client-name",
            "Test Client Prefixed Unknown",
            "--owners",
            "user:nonexistent",
        ],
    )
    assert res.exit_code != 0
    assert "user 'nonexistent' not found" in res.output
