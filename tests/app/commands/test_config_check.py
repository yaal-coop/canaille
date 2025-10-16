from canaille.commands import cli


def test_check_command(cli_runner):
    """Test that config check command succeeds with valid configuration."""
    res = cli_runner.invoke(cli, ["config", "check"])
    assert res.exit_code == 0, res.stdout


def test_check_command_fail(testclient, cli_runner):
    """Test that config check command fails when SMTP host is invalid."""
    testclient.app.config["CANAILLE"]["SMTP"]["HOST"] = "invalid-domain.com"

    res = cli_runner.invoke(cli, ["config", "check"])
    assert res.exit_code == 1, res.stdout


def test_check_command_no_smtp(testclient, cli_runner):
    """Test that config check command succeeds when SMTP is not configured."""
    testclient.app.config["CANAILLE"]["SMTP"] = None

    res = cli_runner.invoke(cli, ["config", "check"])
    assert res.exit_code == 0, res.stdout
