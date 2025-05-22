from canaille.commands import cli


def test_install(cli_runner):
    """Tests that the install command is successfull.

    More detailed tests should be run by backends.
    """
    res = cli_runner.invoke(cli, ["install"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
