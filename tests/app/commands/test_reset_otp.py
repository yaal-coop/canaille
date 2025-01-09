import json
import logging
from unittest import mock

import pytest

from canaille.commands import cli


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_reset_otp_by_id(testclient, backend, caplog, user_otp, otp_method):
    """Reset one-time password authentication for a user by its id."""

    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    old_token = user_otp.secret_token
    assert old_token is not None
    assert user_otp.last_otp_login is not None

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(
        cli,
        [
            "reset-otp",
            user_otp.id,
        ],
    )
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
        "given_name": "John",
        "id": user_otp.id,
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
    }
    assert (
        "canaille",
        logging.SECURITY,
        "Reset one-time password authentication from CLI for user",
    ) in caplog.record_tuples
    backend.reload(user_otp)
    assert user_otp.secret_token is not None
    assert user_otp.secret_token != old_token
    assert user_otp.last_otp_login is None
    if otp_method == "HOTP":
        assert user_otp.hotp_counter == 1


def test_reset_otp_unknown_id(testclient):
    """Error case for trying to reset one-time password authentication for an invalid user."""

    runner = testclient.app.test_cli_runner()
    res = runner.invoke(
        cli,
        [
            "reset-otp",
            "invalid",
        ],
    )
    assert res.exit_code == 1, res.stdout
    assert res.stdout == "Error: No user with id 'invalid'\n"
