import datetime
import logging

import pytest
import time_machine

from canaille.app import models
from canaille.core.models import HOTP_LOOK_AHEAD_WINDOW


def test_otp_disabled(testclient):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = None
    with testclient.session_transaction() as session:
        session["remaining_otp_methods"] = ["TOTP"]
        session["attempt_login_with_correct_password"] = "id"
    testclient.get("/setup-mfa", status=404)
    testclient.get("/verify-mfa", status=404)


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_signin_and_out_with_otp(testclient, user_otp, caplog, otp_method):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert "user" == session.get("attempt_login")

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)
    assert (
        "info",
        "Please enter the one-time password from your authenticator app.",
    ) in res.flashes
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert "attempt_login" not in session
        assert "user" == session.get("attempt_login_with_correct_password")

    res = testclient.get("/verify-mfa")
    res.form["otp"] = user_otp.generate_otp()
    res = res.form.submit(status=302)

    assert (
        "success",
        "Connection successful. Welcome John (johnny) Doe",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Succeed login attempt for user from unknown IP",
    ) in caplog.record_tuples
    res = res.follow(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert [user_otp.id] == session.get("user_id")
        assert "attempt_login" not in session
        assert "attempt_login_with_correct_password" not in session

    res = testclient.get("/login", status=302)

    res = testclient.get("/logout")
    assert (
        "success",
        "You have been disconnected. See you next time John (johnny) Doe",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Logout user from unknown IP",
    ) in caplog.record_tuples
    res = res.follow(status=302)
    res = res.follow(status=200)


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_signin_wrong_otp(testclient, user_otp, caplog, otp_method):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["otp"] = 111111
    res = res.form.submit()

    assert (
        "error",
        "The one-time password you entered is invalid. Please try again",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Failed login attempt (wrong OTP) for user from unknown IP",
    ) in caplog.record_tuples


def test_signin_expired_totp(testclient, user_otp, caplog):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = "TOTP"

    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False) as traveller:
        with testclient.session_transaction() as session:
            assert not session.get("user_id")

        res = testclient.get("/login", status=200)

        res.form["login"] = "user"
        res = res.form.submit(status=302)
        res = res.follow(status=200)

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(status=302)
        res = res.follow(status=200)

        res.form["otp"] = user_otp.generate_otp()
        traveller.shift(datetime.timedelta(seconds=30))
        res = res.form.submit()

        assert (
            "error",
            "The one-time password you entered is invalid. Please try again",
        ) in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Failed login attempt (wrong OTP) for user from unknown IP",
        ) in caplog.record_tuples


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_new_user_setup_otp(testclient, backend, caplog, otp_method):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    u = models.User(
        formatted_name="Otp User",
        family_name="Otp",
        user_name="otp",
        emails=["john@doe.test"],
        password="correct horse battery staple",
    )
    backend.save(u)

    assert u.secret_token is not None
    if otp_method == "HOTP":
        assert u.hotp_counter == 1

    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/login", status=200)

    res.form["login"] = "otp"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)

    assert res.location == "/setup-mfa"
    assert (
        "info",
        "You have not enabled multi-factor authentication. Please enable it first to login.",
    ) in res.flashes
    res = testclient.get("/setup-mfa", status=200)
    assert u.secret_token == res.form["secret"].value

    res = testclient.get("/verify-mfa", status=200)
    res.form["otp"] = u.generate_otp()
    res = res.form.submit(status=302)

    assert (
        "success",
        "Connection successful. Welcome Otp User",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Succeed login attempt for otp from unknown IP",
    ) in caplog.record_tuples
    res = res.follow(status=302)
    res = res.follow(status=200)
    with testclient.session_transaction() as session:
        assert [u.id] == session.get("user_id")
        assert "attempt_login" not in session
        assert "attempt_login_with_correct_password" not in session

    res = testclient.get("/login", status=302)

    backend.delete(u)


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_verify_otp_page_without_signin_in_redirects_to_login_page(
    testclient, user_otp, otp_method
):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    res = testclient.get("/verify-mfa", status=302)
    assert res.location == "/login"
    assert res.flashes == [
        ("warning", "Cannot remember the login you attempted to sign in with")
    ]


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_setup_otp_page_without_signin_in_redirects_to_login_page(
    testclient, user_otp, otp_method
):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    res = testclient.get("/setup-mfa", status=302)
    assert res.location == "/login"
    assert res.flashes == [
        ("warning", "Cannot remember the login you attempted to sign in with")
    ]


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_verify_otp_page_already_logged_in(testclient, logged_user_otp, otp_method):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    res = testclient.get("/verify-mfa", status=302)
    assert res.location == "/profile/user"


def test_signin_multiple_attempts_doesnt_desynchronize_hotp(
    testclient, user_otp, caplog
):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = "HOTP"

    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert "user" == session.get("attempt_login")

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert "attempt_login" not in session
        assert "user" == session.get("attempt_login_with_correct_password")

    res = testclient.get("/verify-mfa")
    for _x in range(3):
        res.form["otp"] = "111111"
        res = res.form.submit(status=302).follow()
    res.form["otp"] = user_otp.generate_otp()
    res = res.form.submit(status=302)

    assert (
        "success",
        "Connection successful. Welcome John (johnny) Doe",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Succeed login attempt for user from unknown IP",
    ) in caplog.record_tuples
    res = res.follow(status=302)
    res = res.follow(status=200)


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_setup_otp_page_already_logged_in(testclient, logged_user_otp, otp_method):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    res = testclient.get("/setup-mfa", status=302)
    assert res.location == "/profile/user"


def test_signin_inside_hotp_look_ahead_window(testclient, backend, user_otp, caplog):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = "HOTP"

    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    assert user_otp.hotp_counter == 1

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert "user" == session.get("attempt_login")

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert "attempt_login" not in session
        assert "user" == session.get("attempt_login_with_correct_password")

    res = testclient.get("/verify-mfa")

    res.form["otp"] = user_otp.generate_otp(HOTP_LOOK_AHEAD_WINDOW)
    res = res.form.submit(status=302)

    assert (
        "success",
        "Connection successful. Welcome John (johnny) Doe",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Succeed login attempt for user from unknown IP",
    ) in caplog.record_tuples
    res = res.follow(status=302)
    res = res.follow(status=200)

    user = backend.get(models.User, id=user_otp.id)
    assert user.hotp_counter == HOTP_LOOK_AHEAD_WINDOW + 2


def test_signin_outside_hotp_look_ahead_window(testclient, backend, user_otp, caplog):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = "HOTP"

    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    assert user_otp.hotp_counter == 1

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert "user" == session.get("attempt_login")

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert "attempt_login" not in session
        assert "user" == session.get("attempt_login_with_correct_password")

    res = testclient.get("/verify-mfa")

    res.form["otp"] = user_otp.generate_otp(HOTP_LOOK_AHEAD_WINDOW + 1)
    res = res.form.submit(status=302)

    assert (
        "error",
        "The one-time password you entered is invalid. Please try again",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Failed login attempt (wrong OTP) for user from unknown IP",
    ) in caplog.record_tuples

    user = backend.get(models.User, id=user_otp.id)
    assert user.hotp_counter == 1
