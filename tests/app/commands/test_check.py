from canaille.app.commands import cli


def test_check_command(testclient):
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["check"])
    assert res.exit_code == 0, res.stdout


def test_check_command_fail(testclient):
    testclient.app.config["LDAP"]["URI"] = "ldap://invalid-ldap.com"
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["check"])
    assert res.exit_code == 1, res.stdout
