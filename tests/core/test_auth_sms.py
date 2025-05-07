import datetime
import logging
from unittest import mock

import pytest
import smpplib
import time_machine

from canaille.app import mask_phone
from canaille.core.auth import AuthenticationSession
from canaille.core.models import OTP_VALIDITY
from canaille.core.models import SEND_NEW_OTP_DELAY
from canaille.core.sms import send_one_time_password_sms


@pytest.fixture
def configuration(configuration):
    configuration["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["sms"]
    return configuration


def test_no_auth_session_not_logged_in(testclient, user):
    """Non-logged users should not be able to access the sms auth form if an authentication session has not been properly started."""
    res = testclient.get("/auth/sms", status=302)
    assert res.location == "/login"
    assert res.flashes == [
        ("warning", "Cannot remember the login you attempted to sign in with.")
    ]


def test_no_auth_session_logged_in(testclient, logged_user):
    """Logged users should not be able to access the sms auth form if an authentication session has not been properly started."""
    res = testclient.get("/auth/sms", status=302)
    assert res.location == "/"


def test_not_sms_step(testclient, user):
    """Users reaching the sms passcode form while this is not the right auth step in their flow should be redirected there."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["password", "sms"],
        ).serialize()

    res = testclient.get("/auth/sms", status=302)
    assert res.location == "/auth/password"


def test_signin_with_sms_otp(smpp_client, testclient, backend, user, caplog):
    with testclient.session_transaction() as session:
        assert not session.get("sessions")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    assert (
        "canaille",
        logging.SECURITY,
        "Sent one-time passcode for user at 555-000-000",
    ) in caplog.record_tuples

    backend.reload(user)

    smpp_client.send_message.assert_called()
    assert (
        user.one_time_password
        in smpp_client.send_message.call_args.kwargs["short_message"].decode()
    )

    res.form["otp"] = user.one_time_password
    res = res.form.submit(status=302, name="action", value="confirm")

    assert (
        "success",
        "Connection successful. Welcome Johnny",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Successful sms code authentication for user",
    ) in caplog.record_tuples

    res = res.follow()
    assert (
        "canaille",
        logging.SECURITY,
        "Successful authentication for user",
    ) in caplog.record_tuples


def test_signin_wrong_sms_otp(testclient, user, caplog):
    with testclient.session_transaction() as session:
        assert not session.get("sessions")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    assert (
        "canaille",
        logging.SECURITY,
        "Sent one-time passcode for user at 555-000-000",
    ) in caplog.record_tuples

    res.form["otp"] = "123456"
    res = res.form.submit(status=200, name="action", value="confirm")

    assert (
        "error",
        "The passcode you entered is invalid. Please try again",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Failed sms code authentication for user",
    ) in caplog.record_tuples


def test_expired_sms_otp(testclient, user, caplog):
    """Good expired passcode should be refused."""
    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False) as traveller:
        with testclient.session_transaction() as session:
            assert not session.get("sessions")

        res = testclient.get("/login", status=200)

        res.form["login"] = "user"
        res = res.form.submit(status=302)
        res = res.follow(status=200)

        otp = user.generate_sms_or_mail_otp()
        send_one_time_password_sms(user.preferred_email, otp)
        res.form["otp"] = user.one_time_password

        traveller.shift(datetime.timedelta(seconds=OTP_VALIDITY))
        res = res.form.submit(status=200, name="action", value="confirm")

        assert (
            "error",
            "The passcode you entered is invalid. Please try again",
        ) in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Failed sms code authentication for user",
        ) in caplog.record_tuples


def test_send_new_mail_otp_too_early(smpp_client, testclient, backend, user, caplog):
    """Check that clicking on the resend button too early should not send a new mail."""
    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False):
        res = testclient.get("/login", status=200)
        res.form["login"] = "user"
        res = res.form.submit(status=302)
        res = res.follow(status=200)
        assert smpp_client.send_message.call_count == 1

        res = res.form.submit(status=302, name="action", value="resend")

        assert (
            "danger",
            f"Too many attempts. Please try again in {SEND_NEW_OTP_DELAY} seconds.",
        ) in res.flashes
        assert smpp_client.send_message.call_count == 1
        res = res.follow(status=200)


def test_send_new_sms_otp_on_time(smpp_client, testclient, backend, user, caplog):
    """Check that clicking on the resend button after an adequate delay send a new code."""
    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False):
        res = testclient.get("/login", status=200)
        res.form["login"] = "user"
        res = res.form.submit(status=302)
        res = res.follow(status=200)
        assert smpp_client.send_message.call_count == 1

    with time_machine.travel("2020-01-01 01:00:11+00:00", tick=False):
        res = res.form.submit(status=302, name="action", value="resend")

        assert smpp_client.send_message.call_count == 2

        backend.reload(user)
        sms_content = smpp_client.send_message.call_args.kwargs[
            "short_message"
        ].decode()
        assert user.one_time_password in sms_content
        assert (
            "success",
            "The new verification code have been sent.",
        ) in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Sent one-time passcode for user at 555-000-000",
        ) in caplog.record_tuples

        assert res.location == "/auth/sms"


def test_send_new_sms_invalid_user(smpp_client, testclient, backend, user, caplog):
    """Invalid users should be shown the re-send button, but it should do nothing."""
    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False):
        res = testclient.get("/login", status=200)
        res.form["login"] = "invalid"
        res = res.form.submit(status=302)
        res = res.follow(status=200)
        assert not smpp_client.send_message.called

    with time_machine.travel("2020-01-01 01:00:11+00:00", tick=False):
        res = res.form.submit(status=302, name="action", value="resend")

        assert not smpp_client.send_message.called
        assert (
            "success",
            "The new verification code have been sent.",
        ) in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Sent one-time passcode for user at 555-000-000",
        ) not in caplog.record_tuples


def test_send_new_sms_error(smpp_client, testclient, backend, user, caplog):
    """Handle SMS sending errors."""
    smpp_client.connect = mock.Mock(
        side_effect=smpplib.exceptions.ConnectionError("Host unreachable")
    )

    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False):
        res = testclient.get("/login", status=200)
        res.form["login"] = "user"
        res = res.form.submit(status=302)
        res = res.follow(status=200)

    with time_machine.travel("2020-01-01 01:01:00+00:00", tick=False):
        res = res.form.submit(status=302, name="action", value="resend")
        assert (
            "canaille",
            logging.WARNING,
            "Could not send sms: Host unreachable",
        ) in caplog.record_tuples


def test_mask_phone_number():
    phone = "+33123456789"
    assert mask_phone(phone) == "+33#####89"
