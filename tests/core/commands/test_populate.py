import pytest

from canaille.app import models
from canaille.commands import cli
from canaille.core.populate import fake_groups
from canaille.core.populate import fake_users


def test_populate_users(cli_runner, backend):
    assert len(backend.query(models.User)) == 0
    res = cli_runner.invoke(cli, ["populate", "--nb", "10", "users"])
    assert res.exit_code == 0, res.stdout
    assert len(backend.query(models.User)) == 10
    for user in backend.query(models.User):
        backend.delete(user)


def test_populate_groups(cli_runner, backend):
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
    if "ldap" in backend.__class__.__module__:
        pytest.skip()
    assert fake_groups(nb_users_max=0)
