from canaille.commands import cli
from canaille.models import Group
from canaille.models import User


def test_populate_users(testclient, slapd_connection):
    runner = testclient.app.test_cli_runner()

    assert len(User.all()) == 0
    res = runner.invoke(cli, ["populate", "--nb", "10", "users"])
    assert res.exit_code == 0, res.stderr
    assert len(User.all()) == 10


def test_populate_groups(testclient, slapd_connection):
    runner = testclient.app.test_cli_runner()

    assert len(Group.all()) == 0
    res = runner.invoke(cli, ["populate", "--nb", "10", "groups"])
    assert res.exit_code == 0, res.stderr
    assert len(Group.all()) == 10
