import re

from canaille.commands import cli


def test_check_command(cli_runner):
    res = cli_runner.invoke(cli, ["--version"])
    semver_pattern = r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
    assert re.match(rf"Canaille, version {semver_pattern}", res.stdout)
    assert res.exit_code == 0, res.stdout
