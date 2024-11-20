from canaille.app import models
from canaille.commands import cli


def test_delete_by_id(testclient, backend):
    """Remove a model identified by its id."""
    user = models.User(
        formatted_name="Foo bar",
        family_name="Bar",
        emails=["foobar@example.test"],
        user_name="foobar",
    )
    backend.save(user)

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["delete", "user", user.id])
    assert res.exit_code == 0, res.stdout

    assert not backend.get(models.User, user_name="foobar")


def test_delete_by_identifier(testclient, backend):
    """Remove a model identified by its identifier."""
    user = models.User(
        formatted_name="Foo bar",
        family_name="Bar",
        emails=["foobar@example.test"],
        user_name="foobar",
    )
    backend.save(user)

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["delete", "user", "foobar"])
    assert res.exit_code == 0, res.stdout

    assert not backend.get(models.User, user_name="foobar")


def test_delete_unknown_id(testclient, backend):
    """Error case for trying to set a value for an invalid object."""

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["delete", "user", "invalid"])
    assert res.exit_code == 1, res.stdout
    assert res.stdout == "Error: No user with id 'invalid'\n"
