from canaille.commands import cli


def test_check_command(testclient, mock_smpp):
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["check"])
    assert res.exit_code == 0, res.stdout


def test_check_command_fail(testclient):
    testclient.app.config["CANAILLE"]["SMTP"]["HOST"] = "invalid-domain.com"
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["check"])
    assert res.exit_code == 1, res.stdout


def test_check_command_no_smtp(testclient, mock_smpp):
    testclient.app.config["CANAILLE"]["SMTP"] = None
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["check"])
    assert res.exit_code == 0, res.stdout
