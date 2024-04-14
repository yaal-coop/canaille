from canaille.app import models
from canaille.commands import cli
from canaille.core.populate import fake_users


def test_populate_users(testclient, backend):
    runner = testclient.app.test_cli_runner()

    assert len(backend.query(models.User)) == 0
    res = runner.invoke(cli, ["populate", "--nb", "10", "users"])
    assert res.exit_code == 0, res.stdout
    assert len(backend.query(models.User)) == 10
    for user in backend.query(models.User):
        backend.delete(user)


def test_populate_groups(testclient, backend):
    fake_users(10)
    runner = testclient.app.test_cli_runner()

    assert len(backend.query(models.Group)) == 0
    res = runner.invoke(cli, ["populate", "--nb", "10", "groups"])
    assert res.exit_code == 0, res.stdout
    assert len(backend.query(models.Group)) == 10

    for group in backend.query(models.Group):
        backend.delete(group)

    for user in backend.query(models.User):
        backend.delete(user)
