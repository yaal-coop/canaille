from canaille.commands import cli


def test_check_command(testclient):
    runner = testclient.app.test_cli_runner()
    runner.invoke(cli, ["check"])


def test_check_command_fail(testclient):
    testclient.app.config["LDAP"]["URI"] = "ldap://invalid-ldap.com"
    runner = testclient.app.test_cli_runner()
    runner.invoke(cli, ["check"])
