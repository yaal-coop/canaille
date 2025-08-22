import json
import unittest.mock
from unittest import mock

from canaille.backends import Backend
from canaille.commands import cli


def test_set_string_by_id(cli_runner, backend, user):
    """Set a string attribute to a model identifier by its id."""
    res = cli_runner.invoke(cli, ["set", "user", user.id, "--given-name", "foobar"])
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout) == {
        "created": mock.ANY,
        "display_name": "Johnny",
        "emails": [
            "john@doe.test",
        ],
        "family_name": "Doe",
        "formatted_address": "1234, some street, 6789 some city, some state",
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
        "locality": "some city",
        "postal_code": "6789",
        "region": "some state",
        "street": "1234, some street",
        "hotp_counter": 1,
        "last_otp_login": mock.ANY,
        "secret_token": mock.ANY,
    }
    backend.reload(user)
    assert user.given_name == "foobar"


def test_set_string_by_identifier(cli_runner, backend, user):
    """Set a string attribute to a model identifier by its identifier."""
    res = cli_runner.invoke(cli, ["set", "user", "user", "--given-name", "foobar"])
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout) == {
        "created": mock.ANY,
        "display_name": "Johnny",
        "emails": [
            "john@doe.test",
        ],
        "family_name": "Doe",
        "formatted_address": "1234, some street, 6789 some city, some state",
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
        "locality": "some city",
        "postal_code": "6789",
        "region": "some state",
        "street": "1234, some street",
        "hotp_counter": 1,
        "last_otp_login": mock.ANY,
        "secret_token": mock.ANY,
    }
    backend.reload(user)
    assert user.given_name == "foobar"


def test_set_multiple(cli_runner, backend, user):
    """Test setting several emails."""
    res = cli_runner.invoke(
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
        "formatted_address": "1234, some street, 6789 some city, some state",
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
        "locality": "some city",
        "postal_code": "6789",
        "region": "some state",
        "street": "1234, some street",
        "hotp_counter": 1,
        "last_otp_login": mock.ANY,
        "secret_token": mock.ANY,
    }
    backend.reload(user)
    assert user.emails == [
        "foo@example.test",
        "bar@example.test",
    ]


def test_set_unknown_id(cli_runner, backend):
    """Error case for trying to set a value for an invalid object."""
    res = cli_runner.invoke(cli, ["set", "user", "invalid", "--given-name", "foobar"])
    assert res.exit_code == 1, res.stdout
    assert res.stderr == "Error: No user with id 'invalid'\n"


def test_set_remove_simple_attribute(cli_runner, backend, user, admin):
    """Test to remove a non multiple attribute."""
    assert user.formatted_address is not None

    res = cli_runner.invoke(cli, ["set", "user", user.id, "--formatted-address", ""])
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
        "locality": "some city",
        "postal_code": "6789",
        "region": "some state",
        "street": "1234, some street",
        "hotp_counter": 1,
        "last_otp_login": mock.ANY,
        "secret_token": mock.ANY,
    }
    backend.reload(user)
    assert user.formatted_address is None


def test_set_remove_multiple_attribute(cli_runner, backend, user, admin, foo_group):
    """Test to remove a non multiple attribute."""
    foo_group.members = [user, admin]
    backend.save(foo_group)
    assert user.groups == [foo_group]

    res = cli_runner.invoke(cli, ["set", "user", user.id, "--groups", ""])
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout) == {
        "created": mock.ANY,
        "display_name": "Johnny",
        "emails": [
            "john@doe.test",
        ],
        "family_name": "Doe",
        "formatted_name": "John (johnny) Doe",
        "formatted_address": "1234, some street, 6789 some city, some state",
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
        "locality": "some city",
        "postal_code": "6789",
        "region": "some state",
        "street": "1234, some street",
        "hotp_counter": 1,
        "last_otp_login": mock.ANY,
        "secret_token": mock.ANY,
    }
    backend.reload(user)
    assert user.groups == []


def test_set_quiet(cli_runner, backend, user):
    """Test that --quiet suppresses output."""
    res = cli_runner.invoke(
        cli, ["set", "user", user.id, "--given-name", "foobar", "--quiet"]
    )
    assert res.exit_code == 0, res.stdout
    assert res.stdout == ""
    backend.reload(user)
    assert user.given_name == "foobar"


def test_set_ignore_errors_unknown_id(cli_runner, backend):
    """Test that errors are ignored with --ignore-errors for unknown id."""
    res = cli_runner.invoke(
        cli, ["set", "user", "invalid", "--given-name", "foobar", "--ignore-errors"]
    )
    assert res.exit_code == 0
    assert res.stdout == ""


def test_set_ignore_errors_save_failure(cli_runner, backend, user):
    """Test that save errors are ignored with --ignore-errors."""

    def mock_save(*args, **kwargs):
        raise Exception("Simulated save error")

    with unittest.mock.patch.object(Backend.instance, "save", side_effect=mock_save):
        res = cli_runner.invoke(cli, ["set", "user", user.id, "--given-name", "foobar"])
        assert res.exit_code != 0
        assert "Simulated save error" in str(res.output)

    with unittest.mock.patch.object(Backend.instance, "save", side_effect=mock_save):
        res = cli_runner.invoke(
            cli, ["set", "user", user.id, "--given-name", "foobar", "--ignore-errors"]
        )
        assert res.exit_code == 0
        assert res.stdout == ""
