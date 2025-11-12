import datetime
import json
import unittest.mock
from unittest import mock

import pytest

from canaille.backends import Backend
from canaille.backends import ModelEncoder
from canaille.commands import cli


def test_serialize(user):
    """Test ModelSerializer with basic types."""
    assert json.dumps({"foo": "bar"}, cls=ModelEncoder) == '{"foo": "bar"}'

    assert (
        json.dumps({"foo": datetime.datetime(1970, 1, 1)}, cls=ModelEncoder)
        == '{"foo": "1970-01-01T00:00:00"}'
    )

    with pytest.raises(TypeError):
        json.dumps({"foo": object()}, cls=ModelEncoder)


def test_get_list_models(cli_runner, backend, user):
    """Nominal case test for model get command."""
    res = cli_runner.invoke(cli, ["get"], catch_exceptions=False)
    assert res.exit_code == 2, res.stderr
    models = ("user", "group")
    for model in models:
        assert model in res.stderr


def test_get(cli_runner, backend, user):
    """Nominal case test for model get command."""
    res = cli_runner.invoke(cli, ["get", "user"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout) == [
        {
            "created": mock.ANY,
            "display_name": "Johnny",
            "emails": [
                "john@doe.test",
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
        },
    ]


def test_get_model_filter(cli_runner, backend, user, admin, foo_group):
    """Test model get filter."""
    res = cli_runner.invoke(
        cli, ["get", "user", "--groups", foo_group.id], catch_exceptions=False
    )
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout) == [
        {
            "created": mock.ANY,
            "display_name": "Johnny",
            "emails": [
                "john@doe.test",
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
            "groups": [foo_group.id],
            "locality": "some city",
            "postal_code": "6789",
            "region": "some state",
            "street": "1234, some street",
            "hotp_counter": 1,
            "last_otp_login": mock.ANY,
            "secret_token": mock.ANY,
        },
    ]


def test_get_datetime_filter(cli_runner, backend, user):
    """Test model get filter."""
    res = cli_runner.invoke(
        cli,
        ["get", "user", "--created", user.created.isoformat()],
    )
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout) == [
        {
            "created": mock.ANY,
            "display_name": "Johnny",
            "emails": [
                "john@doe.test",
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
        },
    ]


def test_get_ignore_errors(cli_runner, backend):
    """Test that errors are ignored with --ignore-errors."""

    def mock_query(*args, **kwargs):
        raise Exception("Simulated query error")

    with unittest.mock.patch.object(Backend.instance, "query", side_effect=mock_query):
        res = cli_runner.invoke(cli, ["get", "user"])
        assert res.exit_code != 0
        assert "Simulated query error" in str(res.output)

    with unittest.mock.patch.object(Backend.instance, "query", side_effect=mock_query):
        res = cli_runner.invoke(cli, ["get", "user", "--ignore-errors"])
        assert res.exit_code == 0
        assert res.stdout == ""
