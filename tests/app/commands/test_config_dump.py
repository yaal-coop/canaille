import os
import pathlib

import pytest

from canaille.commands import cli


def test_export_current_config(testclient, cli_runner, backend, tmp_path):
    """Export the current application config in a file."""
    if "memory" not in backend.__class__.__module__:
        pytest.skip()

    toml_export = tmp_path / "config.toml"
    toml_expected = (
        pathlib.Path(__file__).parent.parent / "fixtures" / "current-app-config.toml"
    )

    testclient.app.config["SECRET_KEY"] = "very-secret"
    testclient.app.config["CANAILLE"]["SMTP"]["PORT"] = 25
    testclient.app.config["CANAILLE_OIDC"]["ACTIVE_JWKS"] = None

    res = cli_runner.invoke(
        cli, ["config", "dump", "--path", str(toml_export)], catch_exceptions=False
    )
    assert res.exit_code == 0, res.stdout

    with open(toml_export) as fd:
        actual_content = fd.read()

    with open(toml_expected) as fd:
        expected_content = fd.read()

    assert actual_content == expected_content


def test_export_env_config(testclient, cli_runner, tmp_path, backend):
    """Export the current application config in a file which pass is passed in the CONFIG env var."""
    if "memory" not in backend.__class__.__module__:
        pytest.skip()

    toml_export = tmp_path / "config.toml"
    toml_expected = (
        pathlib.Path(__file__).parent.parent / "fixtures" / "current-app-config.toml"
    )

    testclient.app.config["SECRET_KEY"] = "very-secret"
    testclient.app.config["CANAILLE"]["SMTP"]["PORT"] = 25
    testclient.app.config["CANAILLE_OIDC"]["ACTIVE_JWKS"] = None

    os.environ["CONFIG"] = str(toml_export)

    res = cli_runner.invoke(cli, ["config", "dump"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout

    with open(toml_expected) as fd:
        expected_content = fd.read()

    assert res.stdout == expected_content

    del os.environ["CONFIG"]
