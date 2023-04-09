from canaille.commands import cli
from canaille.core.models import Group
from canaille.core.models import User
from canaille.core.populate import fake_users


def test_populate_users(testclient, slapd_connection):
    runner = testclient.app.test_cli_runner()

    assert len(User.query()) == 0
    res = runner.invoke(cli, ["populate", "--nb", "10", "users"])
    assert res.exit_code == 0, res.stdout
    assert len(User.query()) == 10
    for user in User.query():
        user.delete()


def test_populate_groups(testclient, slapd_connection):
    fake_users(10)
    runner = testclient.app.test_cli_runner()

    assert len(Group.query()) == 0
    res = runner.invoke(cli, ["populate", "--nb", "10", "groups"])
    assert res.exit_code == 0, res.stdout
    assert len(Group.query()) == 10

    for group in Group.query():
        group.delete()

    for user in User.query():
        user.delete()
