from canaille.app import models
from canaille.commands import cli
from canaille.core.populate import fake_users


def test_populate_users(testclient, backend):
    runner = testclient.app.test_cli_runner()

    assert len(models.User.query()) == 0
    res = runner.invoke(cli, ["populate", "--nb", "10", "users"])
    assert res.exit_code == 0, res.stdout
    assert len(models.User.query()) == 10
    for user in models.User.query():
        user.delete()


def test_populate_groups(testclient, backend):
    fake_users(10)
    runner = testclient.app.test_cli_runner()

    assert len(models.Group.query()) == 0
    res = runner.invoke(cli, ["populate", "--nb", "10", "groups"])
    assert res.exit_code == 0, res.stdout
    assert len(models.Group.query()) == 10

    for group in models.Group.query():
        group.delete()

    for user in models.User.query():
        user.delete()
