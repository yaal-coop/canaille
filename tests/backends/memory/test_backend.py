from canaille.commands import cli


def test_install_does_nothing(testclient):
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["install"])
    assert res.exit_code == 0, res.stdout
