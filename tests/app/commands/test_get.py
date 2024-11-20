import json
from unittest import mock

from canaille.commands import cli


def test_get_list_models(testclient, backend, user):
    """Nominal case test for model get command."""

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["get"])
    assert res.exit_code == 0, res.stdout
    models = ("user", "group")
    for model in models:
        assert model in res.stdout


def test_get(testclient, backend, user):
    """Nominal case test for model get command."""

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["get", "user"])
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
            "password": "***",
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
    res = runner.invoke(cli, ["get", "user", "--groups", foo_group.id])
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
            "password": "***",
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
    res = runner.invoke(cli, ["get", "user", "--created", user.created.isoformat()])
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
            "password": "***",
            "phone_numbers": [
                "555-000-000",
            ],
            "preferred_language": "en",
            "profile_url": "https://john.test",
            "user_name": "user",
        },
    ]
