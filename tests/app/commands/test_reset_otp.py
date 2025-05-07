import json
import logging
from unittest import mock

import pytest

from canaille.commands import cli


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_reset_otp_by_id(testclient, cli_runner, backend, caplog, user, otp_method):
    """Reset one-time passcode authentication for a user by its id."""
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    old_token = user.secret_token
    assert old_token is not None

    res = cli_runner.invoke(
        cli,
        [
            "reset-otp",
            user.id,
        ],
    )
    assert res.exit_code == 0, res.stderr
    assert json.loads(res.stdout) == {
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
        "hotp_counter": 1,
        "secret_token": mock.ANY,
        "locality": "some city",
        "postal_code": "6789",
        "region": "some state",
        "street": "1234, some street",
        "last_otp_login": "2020-01-01T00:00:00+00:00",
    }
    assert (
        "canaille",
        logging.SECURITY,
        "Reset one-time passcode authentication from CLI for user",
    ) in caplog.record_tuples
    backend.reload(user)
    assert user.secret_token is not None
    assert user.secret_token != old_token
    if otp_method == "HOTP":
        assert user.hotp_counter == 1


def test_reset_otp_unknown_id(cli_runner):
    """Error case for trying to reset one-time passcode authentication for an invalid user."""
    res = cli_runner.invoke(
        cli,
        [
            "reset-otp",
            "invalid",
        ],
    )
    assert res.exit_code == 1, res.stdout
    assert res.stderr == "Error: No user with id 'invalid'\n"
