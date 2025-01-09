import json
from unittest import mock

from canaille.commands import cli


def test_set_string_by_id(testclient, backend, user):
    """Set a string attribute to a model identifier by its id."""

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["set", "user", user.id, "--given-name", "foobar"])
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout) == {
        "created": mock.ANY,
        "display_name": "Johnny",
        "emails": [
            "john@doe.test",
        ],
        "family_name": "Doe",
        "formatted_address": "1235, somewhere",
        "formatted_name": "John (johnny) Doe",
        "given_name": "foobar",
        "id": user.id,
        "last_modified": mock.ANY,
        "password": mock.ANY,
        "phone_numbers": [
            "555-000-000",
        ],
        "preferred_language": "en",
        "profile_url": "https://john.test",
        "user_name": "user",
    }
    backend.reload(user)
    assert user.given_name == "foobar"


def test_set_string_by_identifier(testclient, backend, user):
    """Set a string attribute to a model identifier by its identifier."""

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["set", "user", "user", "--given-name", "foobar"])
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout) == {
        "created": mock.ANY,
        "display_name": "Johnny",
        "emails": [
            "john@doe.test",
        ],
        "family_name": "Doe",
        "formatted_address": "1235, somewhere",
        "formatted_name": "John (johnny) Doe",
        "given_name": "foobar",
        "id": user.id,
        "last_modified": mock.ANY,
        "password": mock.ANY,
        "phone_numbers": [
            "555-000-000",
        ],
        "preferred_language": "en",
        "profile_url": "https://john.test",
        "user_name": "user",
    }
    backend.reload(user)
    assert user.given_name == "foobar"


def test_set_multiple(testclient, backend, user):
    """Test setting several emails."""

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(
        cli,
        [
            "set",
            "user",
            user.id,
            "--emails",
            "foo@example.test",
            "--emails",
            "bar@example.test",
        ],
    )
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout) == {
        "created": mock.ANY,
        "display_name": "Johnny",
        "emails": [
            "foo@example.test",
            "bar@example.test",
        ],
        "family_name": "Doe",
        "formatted_address": "1235, somewhere",
        "formatted_name": "John (johnny) Doe",
        "given_name": "John",
        "id": user.id,
        "last_modified": mock.ANY,
        "password": mock.ANY,
        "phone_numbers": [
            "555-000-000",
        ],
        "preferred_language": "en",
        "profile_url": "https://john.test",
        "user_name": "user",
    }
    backend.reload(user)
    assert user.emails == [
        "foo@example.test",
        "bar@example.test",
    ]


def test_set_unknown_id(testclient, backend):
    """Error case for trying to set a value for an invalid object."""

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["set", "user", "invalid", "--given-name", "foobar"])
    assert res.exit_code == 1, res.stdout
    assert res.stdout == "Error: No user with id 'invalid'\n"


def test_set_remove_simple_attribute(testclient, backend, user, admin):
    """Test to remove a non multiple attribute."""
    assert user.formatted_address is not None

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["set", "user", user.id, "--formatted-address", ""])
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout) == {
        "created": mock.ANY,
        "display_name": "Johnny",
        "emails": [
            "john@doe.test",
        ],
        "family_name": "Doe",
        "formatted_name": "John (johnny) Doe",
        "given_name": "John",
        "id": user.id,
        "last_modified": mock.ANY,
        "password": mock.ANY,
        "phone_numbers": [
            "555-000-000",
        ],
        "preferred_language": "en",
        "profile_url": "https://john.test",
        "user_name": "user",
    }
    backend.reload(user)
    assert user.formatted_address is None


def test_set_remove_multiple_attribute(testclient, backend, user, admin, foo_group):
    """Test to remove a non multiple attribute."""
    foo_group.members = [user, admin]
    backend.save(foo_group)
    assert user.groups == [foo_group]

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["set", "user", user.id, "--groups", ""])
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout) == {
        "created": mock.ANY,
        "display_name": "Johnny",
        "emails": [
            "john@doe.test",
        ],
        "family_name": "Doe",
        "formatted_name": "John (johnny) Doe",
        "formatted_address": "1235, somewhere",
        "given_name": "John",
        "id": user.id,
        "last_modified": mock.ANY,
        "password": mock.ANY,
        "phone_numbers": [
            "555-000-000",
        ],
        "preferred_language": "en",
        "profile_url": "https://john.test",
        "user_name": "user",
    }
    backend.reload(user)
    assert user.groups == []
