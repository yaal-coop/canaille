import logging
import os
from unittest.mock import patch

from flask_webtest import TestApp

from canaille import create_app
from canaille.commands import cli


def test_no_secret_key(configuration, caplog):
    del configuration["SECRET_KEY"]

    os.environ["DEBUG"] = "1"
    from canaille.hypercorn.app import app

    assert (
        "canaille",
        logging.WARNING,
        "Missing 'SECRET_KEY' configuration parameter.",
    ) in caplog.record_tuples

    testclient = TestApp(app)
    res = testclient.get("/login")
    res.mustcontain(
        "Your Canaille instance is not fully configured and not ready for production."
    )
    del os.environ["DEBUG"]


def test_hypercorn_config(cli_runner, monkeypatch, app):
    """Test hypercorn run command with environment variable configuration."""
    app.config["CANAILLE_HYPERCORN"]["WORKERS"] = 4
    app.config["CANAILLE_HYPERCORN"]["BIND"] = "0.0.0.0:8080"

    with patch("canaille.hypercorn.commands.hypercorn_run") as mock_run:
        mock_run.return_value = 0
        result = cli_runner.invoke(cli, ["run"])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        config = mock_run.call_args[0][0]
        assert config.workers == 4
        assert "0.0.0.0:8080" in config.bind


def test_hypercorn_run_env_config(monkeypatch, configuration, backend):
    """Test hypercorn run command with environment variable configuration."""
    monkeypatch.setenv("CANAILLE_HYPERCORN__WORKERS", "4")
    monkeypatch.setenv("CANAILLE_HYPERCORN__BIND", "0.0.0.0:8080")

    app = create_app(configuration, backend=backend)

    with app.app_context():
        runner = app.test_cli_runner(catch_exceptions=False)

        with patch("canaille.hypercorn.commands.hypercorn_run") as mock_run:
            mock_run.return_value = 0
            result = runner.invoke(cli, ["run"])

            assert result.exit_code == 0
            mock_run.assert_called_once()
            config = mock_run.call_args[0][0]
            assert config.workers == 4
            assert "0.0.0.0:8080" in config.bind


def test_hypercorn_run_app_path_set(cli_runner):
    """Test that application_path is correctly set."""
    with patch("canaille.hypercorn.commands.hypercorn_run") as mock_run:
        mock_run.return_value = 0
        result = cli_runner.invoke(cli, ["run"])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        config = mock_run.call_args[0][0]
        assert config.application_path == "canaille.hypercorn.app:app"


def test_hypercorn_cli_options(cli_runner):
    """Test hypercorn run command with CLI options from pydanclick."""
    with patch("canaille.hypercorn.commands.hypercorn_run") as mock_run:
        mock_run.return_value = 0
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--workers",
                "8",
                "--bind",
                "127.0.0.1:9000",
                "--bind",
                "127.0.0.1:9001",
                "--graceful-timeout",
                "30",
                "--keep-alive-timeout",
                "60",
                "--loglevel",
                "DEBUG",
                "--access-log-format",
                "%(h)s %(r)s %(s)s",
            ],
        )

        assert result.exit_code == 0
        mock_run.assert_called_once()
        config = mock_run.call_args[0][0]
        assert config.workers == 8
        assert "127.0.0.1:9000" in config.bind
        assert "127.0.0.1:9001" in config.bind
        assert config.graceful_timeout == 30
        assert config.keep_alive_timeout == 60
        assert config.loglevel == "DEBUG"
        assert config.access_log_format == "%(h)s %(r)s %(s)s"


def test_hypercorn_cli_options_override_env(cli_runner, app):
    """Test that CLI options override environment configuration."""
    app.config["CANAILLE_HYPERCORN"]["WORKERS"] = 4
    app.config["CANAILLE_HYPERCORN"]["LOGLEVEL"] = "INFO"

    with patch("canaille.hypercorn.commands.hypercorn_run") as mock_run:
        mock_run.return_value = 0
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--workers",
                "10",
                "--loglevel",
                "ERROR",
            ],
        )

        assert result.exit_code == 0
        mock_run.assert_called_once()
        config = mock_run.call_args[0][0]
        assert config.workers == 10
        assert config.loglevel == "ERROR"
