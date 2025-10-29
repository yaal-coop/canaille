import pytest

from canaille.app import models
from canaille.commands import cli
from canaille.core.populate import fake_groups
from canaille.core.populate import fake_users


def test_populate_users(cli_runner, backend):
    """Test that the populate users command creates the specified number of users."""
    assert len(backend.query(models.User)) == 0
    res = cli_runner.invoke(cli, ["populate", "--nb", "10", "users"])
    assert res.exit_code == 0, res.stdout
    assert len(backend.query(models.User)) == 10
    for user in backend.query(models.User):
        backend.delete(user)


def test_populate_users_with_avatars(testclient, backend):
    """Test that users are created with avatars."""
    if "ldap" in backend.__class__.__module__:
        pytest.skip()

    users = fake_users(5)
    assert len(users) == 5

    for user in users:
        assert user.photo is not None
        assert isinstance(user.photo, bytes)
        assert user.photo.startswith(b"<svg")
        assert len(user.photo) > 1000

    for user in users:
        backend.delete(user)


def test_populate_groups(cli_runner, backend):
    """Test that the populate groups command creates the specified number of groups."""
    fake_users(10)

    assert len(backend.query(models.Group)) == 0
    res = cli_runner.invoke(cli, ["populate", "--nb", "10", "groups"])
    assert res.exit_code == 0, res.stdout
    assert len(backend.query(models.Group)) == 10

    for group in backend.query(models.Group):
        backend.delete(group)

    for user in backend.query(models.User):
        backend.delete(user)


def test_populate_groups_without_users(cli_runner, backend):
    """Test that groups can be populated without adding users to them."""
    if "ldap" in backend.__class__.__module__:
        pytest.skip()
    assert fake_groups(nb_users_max=0)
