from canaille.commands import cli


def test_install(testclient):
    """Tests that the install command is successfull.

    More detailed tests should be run by backends.
    """
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["install"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
