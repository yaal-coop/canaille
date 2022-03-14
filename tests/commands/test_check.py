from canaille.commands import cli


def test_check_command(testclient):
    runner = testclient.app.test_cli_runner()
    result = runner.invoke(cli, ["check"])

    assert not result.exception


def test_check_command_fail(testclient):
    testclient.app.config["LDAP"]["URI"] = "ldap://invalid-ldap.com"
    runner = testclient.app.test_cli_runner()
    result = runner.invoke(cli, ["check"])

    assert result.exception
    assert "Could not connect to the LDAP server" in result.stdout
