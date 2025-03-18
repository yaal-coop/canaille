import json

from canaille.app import models
from canaille.commands import cli


def test_restore_stdin(testclient, backend):
    """Test the full database dump command."""
    payload = {
        "group": [
            {
                "created": "2025-01-01T12:00:00+00:00",
                "display_name": "foo",
                "id": "cef66b33-2762-423e-b0c3-2fb6ab13abfa",
                "last_modified": "2025-01-01T12:00:00+00:00",
                "members": [
                    "e52b36b5-6a94-4395-b3a8-0f72d9140bfa",
                ],
            },
        ],
        "user": [
            {
                "created": "2025-01-02T12:00:00+00:00",
                "display_name": "Johnny",
                "emails": [
                    "john@doe.test",
                ],
                "family_name": "Doe",
                "formatted_address": "1235, somewhere",
                "formatted_name": "John (johnny) Doe",
                "given_name": "John",
                "groups": ["cef66b33-2762-423e-b0c3-2fb6ab13abfa"],
                "id": "e52b36b5-6a94-4395-b3a8-0f72d9140bfa",
                "last_modified": "2025-01-02T12:00:00+00:00",
                "password": "$pbkdf2-sha512$25000$Nsa4VwoBgHBOKaUUImSMsQ$/Ynkpp1RQILSMBUfKxxMZpG/2oYcFNJxFGMZ0xoHSIbIGkkqeo.VgY71r3Gl8tepUJRmNnaW7if0C5pRHue/Zw",
                "phone_numbers": [
                    "555-000-000",
                ],
                "preferred_language": "en",
                "profile_url": "https://john.test",
                "user_name": "user",
            },
        ],
    }

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(
        cli, ["restore"], catch_exceptions=False, input=json.dumps(payload)
    )
    assert res.exit_code == 0, res.stdout

    user = backend.get(models.User)
    assert user.user_name == "user"
    assert user.family_name == "Doe"

    group = backend.get(models.Group)
    assert group.display_name == "foo"

    assert user.groups == [group]
    assert group.members == [user]

    backend.delete(group)
    backend.delete(user)


def test_restore_stdin_no_input(testclient, backend):
    """Test the restore command without input."""
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["restore"], catch_exceptions=False)
    assert res.exit_code == 1, res.stdout


def test_restore_stdin_empty_input(testclient, backend):
    """Test the restore command with an empty input."""
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["restore"], catch_exceptions=False, input="")
    assert res.exit_code == 1, res.stdout


def test_restore_stdin_invalid_input(testclient, backend):
    """Test the restore command with an invalid input."""
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["restore"], catch_exceptions=False, input="invalid")
    assert res.exit_code == 1, res.stdout
