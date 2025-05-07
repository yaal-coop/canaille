import datetime
import logging

import pytest
import time_machine

from canaille.app import mask_email
from canaille.core.auth import AuthenticationSession
from canaille.core.mails import send_one_time_password_mail
from canaille.core.models import OTP_VALIDITY
from canaille.core.models import SEND_NEW_OTP_DELAY


@pytest.fixture
def configuration(configuration):
    configuration["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["email"]
    return configuration


def test_no_auth_session_not_logged_in(testclient, user):
    """Non-logged users should not be able to access the email auth form if an authentication session has not been properly started."""
    res = testclient.get("/auth/email", status=302)
    assert res.location == "/login"
    assert res.flashes == [
        ("warning", "Cannot remember the login you attempted to sign in with.")
    ]


def test_no_auth_session_logged_in(testclient, logged_user):
    """Logged users should not be able to access the email auth form if an authentication session has not been properly started."""
    res = testclient.get("/auth/email", status=302)
    assert res.location == "/"


def test_not_email_step(testclient, user):
    """Users reaching the email passcode form while this is not the right auth step in their flow should be redirected there."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["password", "email"],
        ).serialize()

    res = testclient.get("/auth/email", status=302)
    assert res.location == "/auth/password"


def test_signin_with_email_otp(smtpd, testclient, backend, user, caplog):
    with testclient.session_transaction() as session:
        assert not session.get("sessions")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    assert (
        "canaille",
        logging.SECURITY,
        "Sent one-time passcode for user to john@doe.test",
    ) in caplog.record_tuples

    backend.reload(user)

    assert len(smtpd.messages) == 1
    email_content = str(smtpd.messages[0].get_payload()[0]).replace("=\n", "")
    assert user.one_time_password in email_content

    res.form["otp"] = user.one_time_password
    res = res.form.submit(status=302, name="action", value="confirm")

    assert (
        "success",
        "Connection successful. Welcome Johnny",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Successful email code authentication for user",
    ) in caplog.record_tuples

    res = res.follow()
    assert (
        "canaille",
        logging.SECURITY,
        "Successful authentication for user",
    ) in caplog.record_tuples


def test_signin_wrong_email_otp(testclient, user, caplog):
    with testclient.session_transaction() as session:
        assert not session.get("sessions")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    assert (
        "canaille",
        logging.SECURITY,
        "Sent one-time passcode for user to john@doe.test",
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
        "Failed email code authentication for user",
    ) in caplog.record_tuples


def test_expired_email_otp(testclient, user, caplog):
    """Good expired passcode should be refused."""
    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False) as traveller:
        with testclient.session_transaction() as session:
            assert not session.get("sessions")

        res = testclient.get("/login", status=200)

        res.form["login"] = "user"
        res = res.form.submit(status=302)
        res = res.follow(status=200)

        otp = user.generate_sms_or_mail_otp()
        send_one_time_password_mail(user.preferred_email, otp)
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
            "Failed email code authentication for user",
        ) in caplog.record_tuples


def test_send_new_mail_otp_too_early(smtpd, testclient, backend, user, caplog):
    """Check that clicking on the resend button too early should not send a new mail."""
    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False):
        res = testclient.get("/login", status=200)
        res.form["login"] = "user"
        res = res.form.submit(status=302)
        res = res.follow(status=200)
        assert len(smtpd.messages) == 1

        res = res.form.submit(status=302, name="action", value="resend")

        assert (
            "danger",
            f"Too many attempts. Please try again in {SEND_NEW_OTP_DELAY} seconds.",
        ) in res.flashes
        assert len(smtpd.messages) == 1
        res = res.follow(status=200)


def test_send_new_mail_otp_on_time(smtpd, testclient, backend, user, caplog):
    """Check that clicking on the resend button after an adequate delay send a new code."""
    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False):
        res = testclient.get("/login", status=200)
        res.form["login"] = "user"
        res = res.form.submit(status=302)
        res = res.follow(status=200)
        assert len(smtpd.messages) == 1

    with time_machine.travel("2020-01-01 01:00:11+00:00", tick=False):
        res = res.form.submit(status=302, name="action", value="resend")

        assert len(smtpd.messages) == 2
        email_content = str(smtpd.messages[1].get_payload()[0]).replace("=\n", "")

        backend.reload(user)
        assert user.one_time_password in email_content
        assert (
            "success",
            "The new verification code have been sent.",
        ) in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Sent one-time passcode for user to john@doe.test",
        ) in caplog.record_tuples

        assert res.location == "/auth/email"


def test_send_new_mail_invalid_user(smtpd, testclient, backend, user, caplog):
    """Invalid users should be shown the re-send button, but it should do nothing."""
    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False):
        res = testclient.get("/login", status=200)
        res.form["login"] = "invalid"
        res = res.form.submit(status=302)
        res = res.follow(status=200)
        assert len(smtpd.messages) == 0

    with time_machine.travel("2020-01-01 01:00:11+00:00", tick=False):
        res = res.form.submit(status=302, name="action", value="resend")

        assert len(smtpd.messages) == 0
        assert (
            "success",
            "The new verification code have been sent.",
        ) in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Sent one-time passcode for user to john@doe.test",
        ) not in caplog.record_tuples


def test_send_new_email_error(smtpd, testclient, backend, user, caplog):
    """Handle SMS sending errors."""
    testclient.app.config["CANAILLE"]["SMTP"]["HOST"] = "invalid.test"

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
            "Could not send email: [Errno -2] Name or service not known",
        ) in caplog.record_tuples


def test_mask_email():
    email = "foo@bar.com"
    assert mask_email(email) == "f#####o@bar.com"

    email = "hello"
    assert mask_email(email) is None
