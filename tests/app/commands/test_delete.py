from canaille.app import models
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
