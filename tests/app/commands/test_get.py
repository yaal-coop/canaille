import datetime
import json
from unittest import mock

from canaille.backends import ModelEncoder
from canaille.commands import cli


def test_serialize(user):
    """Test ModelSerializer with basic types."""
    assert json.dumps({"foo": "bar"}, cls=ModelEncoder) == '{"foo": "bar"}'

    assert (
        json.dumps({"foo": datetime.datetime(1970, 1, 1)}, cls=ModelEncoder)
        == '{"foo": "1970-01-01T00:00:00"}'
    )


def test_get_list_models(testclient, backend, user):
    """Nominal case test for model get command."""

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["get"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    models = ("user", "group")
    for model in models:
        assert model in res.stdout


def test_get(testclient, backend, user):
    """Nominal case test for model get command."""

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["get", "user"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout) == [
        {
            "created": mock.ANY,
            "display_name": "Johnny",
            "emails": [
                "john@doe.test",
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
        },
    ]


def test_get_model_filter(testclient, backend, user, admin, foo_group):
    """Test model get filter."""

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(
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
            "groups": [foo_group.id],
        },
    ]


def test_get_datetime_filter(testclient, backend, user):
    """Test model get filter."""

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(
        cli,
        ["get", "user", "--created", user.created.isoformat()],
        catch_exceptions=False,
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
        },
    ]


def test_get_all(testclient, backend, user, foo_group):
    """Test the full database dump command."""

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["get", "--all"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout) == {
        "authorizationcode": [],
        "client": [],
        "consent": [],
        "group": [
            {
                "created": mock.ANY,
                "display_name": "foo",
                "id": foo_group.id,
                "last_modified": mock.ANY,
                "members": [
                    user.id,
                ],
            },
        ],
        "token": [],
        "user": [
            {
                "created": mock.ANY,
                "display_name": "Johnny",
                "emails": [
                    "john@doe.test",
                ],
                "family_name": "Doe",
                "formatted_address": "1235, somewhere",
                "formatted_name": "John (johnny) Doe",
                "given_name": "John",
                "groups": [foo_group.id],
                "id": user.id,
                "last_modified": mock.ANY,
                "password": mock.ANY,
                "phone_numbers": [
                    "555-000-000",
                ],
                "preferred_language": "en",
                "profile_url": "https://john.test",
                "user_name": "user",
            },
        ],
    }
