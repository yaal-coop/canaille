import datetime
import json
import unittest.mock
from unittest import mock

from canaille.app import models
from canaille.backends import Backend
from canaille.commands import cli


def test_create(cli_runner, backend, foo_group):
    """Nominal case test for model create command."""
    res = cli_runner.invoke(
        cli,
        [
            "create",
            "user",
            "--formatted-name",
            "Johnny",
            "--emails",
            "foo@example.test",
            "--emails",
            "bar@example.test",
            "--given-name",
            "John",
            "--family-name",
            "Doe",
            "--user-name",
            "johnny",
            "--groups",
            foo_group.id,
            "--lock-date",
            "2050-01-01T10:10:10+00:00",
        ],
    )
    assert res.exit_code == 0, res.stdout
    output = json.loads(res.stdout)
    assert output == {
        "formatted_name": "Johnny",
        "created": mock.ANY,
        "last_modified": mock.ANY,
        "emails": [
            "foo@example.test",
            "bar@example.test",
        ],
        "family_name": "Doe",
        "given_name": "John",
        "id": mock.ANY,
        "user_name": "johnny",
        "groups": [foo_group.id],
        "lock_date": "2050-01-01T10:10:10+00:00",
    }
    user = backend.get(models.User, output["id"])
    backend.reload(foo_group)
    assert user.groups == [foo_group]
    assert user.lock_date == datetime.datetime(
        2050, 1, 1, 10, 10, 10, tzinfo=datetime.timezone.utc
    )
    backend.delete(user)


def test_create_quiet(cli_runner, backend, foo_group):
    """Test that --quiet produce no input."""
    res = cli_runner.invoke(
        cli,
        [
            "create",
            "user",
            "--quiet",
            "--formatted-name",
            "Johnny",
            "--emails",
            "foo@example.test",
            "--emails",
            "bar@example.test",
            "--given-name",
            "John",
            "--family-name",
            "Doe",
            "--user-name",
            "johnny",
            "--groups",
            foo_group.id,
            "--lock-date",
            "2050-01-01T10:10:10+00:00",
        ],
    )
    assert res.exit_code == 0, res.stdout
    assert res.stdout == ""
    user = backend.get(models.User, user_name="johnny")
    backend.reload(foo_group)
    assert user.groups == [foo_group]
    assert user.lock_date == datetime.datetime(
        2050, 1, 1, 10, 10, 10, tzinfo=datetime.timezone.utc
    )
    backend.delete(user)


def test_ignore_errors(cli_runner, backend, monkeypatch):
    """Test that error cases are ignored with --ignore-errors."""

    def mock_save(*args, **kwargs):
        raise Exception("Simulated save error")

    with unittest.mock.patch.object(Backend.instance, "save", side_effect=mock_save):
        res = cli_runner.invoke(
            cli,
            [
                "create",
                "user",
                "--formatted-name",
                "Test User",
                "--family-name",
                "User",
                "--user-name",
                "testuser",
            ],
        )
        assert res.exit_code != 0

    with unittest.mock.patch.object(Backend.instance, "save", side_effect=mock_save):
        res = cli_runner.invoke(
            cli,
            [
                "create",
                "user",
                "--ignore-errors",
                "--formatted-name",
                "Test User",
                "--family-name",
                "User",
                "--user-name",
                "testuser",
            ],
        )
        assert res.exit_code == 0
        assert res.stdout == ""
