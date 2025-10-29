from canaille.commands import cli


def test_help_command(cli_runner):
    """Test that --help command works and lists available commands."""
    res = cli_runner.invoke(cli, ["--help"])
    assert res.exit_code == 0, res.stdout
    assert "Canaille management utilities" in res.stdout
