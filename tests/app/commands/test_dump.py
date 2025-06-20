import json
from unittest import mock

from canaille.commands import cli


def test_dump_stdout(cli_runner, backend, user, foo_group):
    """Test the full database dump command."""
    res = cli_runner.invoke(cli, ["dump"], catch_exceptions=False)
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
                "formatted_address": "1234, some street, 6789 some city, some state",
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
                "locality": "some city",
                "postal_code": "6789",
                "region": "some state",
                "street": "1234, some street",
                "hotp_counter": 1,
                "last_otp_login": mock.ANY,
                "secret_token": mock.ANY,
            },
        ],
    }


def test_dump_stdout_explicit_model(cli_runner, backend, user, foo_group):
    """Test the full database dump command for a single model."""
    res = cli_runner.invoke(cli, ["dump", "user"], catch_exceptions=False)
    assert res.exit_code == 0, res.stdout
    assert json.loads(res.stdout) == {
        "user": [
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
                "locality": "some city",
                "postal_code": "6789",
                "region": "some state",
                "street": "1234, some street",
                "hotp_counter": 1,
                "last_otp_login": mock.ANY,
                "secret_token": mock.ANY,
            }
        ]
    }
