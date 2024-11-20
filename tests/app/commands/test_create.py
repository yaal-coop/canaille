import datetime
import json
from unittest import mock

from canaille.app import models
from canaille.commands import cli


def test_create(testclient, backend, foo_group):
    """Nominal case test for model create command."""

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(
        cli,
        [
            "create",
            "user",
            "--formatted-name",
            "Johnny",
            "--emails",
            "foo@example.test",
            "--emails",
            "bar@example.test",
            "--given-name",
            "John",
            "--family-name",
            "Doe",
            "--user-name",
            "johnny",
            "--groups",
            foo_group.id,
            "--lock-date",
            "2050-01-01T10:10:10+00:00",
        ],
    )
    assert res.exit_code == 0, res.stdout
    output = json.loads(res.stdout)
    assert output == {
        "formatted_name": "Johnny",
        "created": mock.ANY,
        "last_modified": mock.ANY,
        "emails": [
            "foo@example.test",
            "bar@example.test",
        ],
        "family_name": "Doe",
        "given_name": "John",
        "id": mock.ANY,
        "user_name": "johnny",
        "groups": [foo_group.id],
        "lock_date": "2050-01-01T10:10:10+00:00",
    }
    user = backend.get(models.User, output["id"])
    backend.reload(foo_group)
    assert user.groups == [foo_group]
    assert user.lock_date == datetime.datetime(
        2050, 1, 1, 10, 10, 10, tzinfo=datetime.timezone.utc
    )
    backend.delete(user)
