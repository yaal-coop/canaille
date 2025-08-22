import unittest.mock

from canaille.app import models
from canaille.backends import Backend
from canaille.commands import cli


def test_delete_all_with_confirmation(cli_runner, backend):
    """Remove all models by default."""
    user = models.User(
        formatted_name="Foo bar",
        family_name="Bar",
        emails=["foobar@example.test"],
        user_name="foobar",
    )
    backend.save(user)

    res = cli_runner.invoke(cli, ["delete", "user"], input="Y")
    assert res.exit_code == 0, res.stdout
    assert "1 item(s) deleted." in res.stdout.splitlines()

    assert not backend.get(models.User, user_name="foobar")


def test_delete_all_without_confirmation(cli_runner, backend):
    """Refuse to remove all models by default."""
    user = models.User(
        formatted_name="Foo bar",
        family_name="Bar",
        emails=["foobar@example.test"],
        user_name="foobar",
    )
    backend.save(user)

    res = cli_runner.invoke(cli, ["delete", "user"], input="N")
    assert res.exit_code == 0, res.stdout
    assert "1 item(s) deleted." not in res.stdout.splitlines()

    assert backend.get(models.User, user_name="foobar")
    backend.delete(user)


def test_delete_all_without_confirmation_prompt(cli_runner, backend):
    """Remove all models by default."""
    user = models.User(
        formatted_name="Foo bar",
        family_name="Bar",
        emails=["foobar@example.test"],
        user_name="foobar",
    )
    backend.save(user)

    res = cli_runner.invoke(cli, ["delete", "user", "--noconfirm"])
    assert res.exit_code == 0, res.stdout
    assert "1 item(s) deleted." in res.stdout.splitlines()

    assert not backend.get(models.User, user_name="foobar")


def test_delete_by_id(cli_runner, backend):
    """Remove a model identified by its id."""
    user = models.User(
        formatted_name="Foo bar",
        family_name="Bar",
        emails=["foobar@example.test"],
        user_name="foobar",
    )
    backend.save(user)

    res = cli_runner.invoke(cli, ["delete", "user", "--id", user.id, "--noconfirm"])
    assert res.exit_code == 0, res.stdout
    assert "1 item(s) deleted." in res.stdout.splitlines()

    assert not backend.get(models.User, user_name="foobar")


def test_delete_unknown_id(cli_runner, backend):
    """Error case for trying to set a value for an invalid object."""
    res = cli_runner.invoke(cli, ["delete", "user", "--id", "invalid", "--noconfirm"])
    assert res.exit_code == 0, res.stdout
    assert "0 item(s) deleted." in res.stdout.splitlines()


def test_delete_ignore_errors_query_failure(cli_runner, backend):
    """Test that query errors are ignored with --ignore-errors."""

    def mock_query(*args, **kwargs):
        raise Exception("Simulated query error")

    with unittest.mock.patch.object(Backend.instance, "query", side_effect=mock_query):
        res = cli_runner.invoke(cli, ["delete", "user", "--noconfirm"])
        assert res.exit_code != 0
        assert "Simulated query error" in str(res.output)

    with unittest.mock.patch.object(Backend.instance, "query", side_effect=mock_query):
        res = cli_runner.invoke(
            cli, ["delete", "user", "--noconfirm", "--ignore-errors"]
        )
        assert res.exit_code == 0
        assert res.stdout == ""


def test_delete_ignore_errors_partial_failure(cli_runner, backend):
    """Test that --ignore-errors skips items that fail to delete."""
    users = []
    for i in range(3):
        user = models.User(
            formatted_name=f"Test User {i}",
            family_name=f"TestUser{i}",
            emails=[f"testuser{i}@example.test"],
            user_name=f"testuser{i}",
        )
        backend.save(user)
        users.append(user)

    original_delete = Backend.instance.delete

    def mock_delete(obj):
        if obj.user_name == "testuser1":
            raise Exception("Cannot delete testuser1")
        return original_delete(obj)

    with unittest.mock.patch.object(
        Backend.instance, "delete", side_effect=mock_delete
    ):
        res = cli_runner.invoke(cli, ["delete", "user", "--noconfirm"])
        assert res.exit_code != 0
        assert "Cannot delete testuser1" in str(res.output)

    total_users = len(backend.query(models.User))
    expected_deleted = total_users - 1

    with unittest.mock.patch.object(
        Backend.instance, "delete", side_effect=mock_delete
    ):
        res = cli_runner.invoke(
            cli, ["delete", "user", "--noconfirm", "--ignore-errors"]
        )
        assert res.exit_code == 0
        assert f"{expected_deleted} item(s) deleted." in res.stdout

    remaining = backend.get(models.User, user_name="testuser1")
    if remaining:
        backend.delete(remaining)
