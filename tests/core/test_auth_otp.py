import datetime
import logging

import otpauth
import pytest
import time_machine

from canaille.app import models
from canaille.app.otp import HOTP_LOOK_AHEAD_WINDOW
from canaille.app.otp import HOTP_START_COUNTER
from canaille.core.auth import AuthenticationSession


@pytest.fixture
def configuration(configuration):
    configuration["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["otp"]
    return configuration


def generate_otp(method, secret, hotp_counter=None):
    hotp_counter = HOTP_START_COUNTER if hotp_counter is None else hotp_counter
    if method == "TOTP":
        totp = otpauth.TOTP(secret.encode("utf-8"))
        return totp.string_code(totp.generate())

    else:
        hotp = otpauth.HOTP(secret.encode("utf-8"))
        return hotp.string_code(hotp.generate(hotp_counter))


def test_no_auth_session_not_logged_in(testclient, user):
    """Non-logged users should not be able to access the otp auth form if an authentication session has not been properly started."""
    res = testclient.get("/auth/otp", status=302)
    assert res.location == "/login"
    assert res.flashes == [
        ("warning", "Cannot remember the login you attempted to sign in with.")
    ]


def test_no_auth_session_logged_in(testclient, logged_user):
    """Logged users should not be able to access the otp auth form if an authentication session has not been properly started."""
    res = testclient.get("/auth/otp", status=302)
    assert res.location == "/"


def test_not_otp_step(testclient, user):
    """Users reaching the otp form while this is not the right auth step in their flow should be redirected there."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["email", "otp"],
        ).serialize()

    res = testclient.get("/auth/otp", status=302)
    assert res.location == "/auth/email"


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_signin_with_otp(testclient, user, caplog, otp_method):
    """Nominal case for OTP authentication."""
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["otp"] = generate_otp(otp_method, user.secret_token, user.hotp_counter)
    res = res.form.submit(status=302)

    assert (
        "success",
        "Connection successful. Welcome Johnny",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Successful authentication for user",
    ) in caplog.record_tuples
    res = res.follow(status=302)
    res = res.follow(status=200)


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_signin_wrong_otp(testclient, user, caplog, otp_method):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    with testclient.session_transaction() as session:
        assert not session.get("sessions")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["otp"] = 111111
    res = res.form.submit()

    assert (
        "error",
        "The passcode you entered is invalid. Please try again",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Failed OTP authentication for user",
    ) in caplog.record_tuples


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_signin_wrong_user(testclient, user, caplog, otp_method):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    with testclient.session_transaction() as session:
        assert not session.get("sessions")

    res = testclient.get("/login", status=200)

    res.form["login"] = "invalid"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["otp"] = 111111
    res = res.form.submit()

    assert (
        "error",
        "The passcode you entered is invalid. Please try again",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Failed OTP authentication for invalid",
    ) in caplog.record_tuples


def test_signin_expired_totp(testclient, user, caplog):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = "TOTP"

    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False) as traveller:
        with testclient.session_transaction() as session:
            assert not session.get("sessions")

        res = testclient.get("/login", status=200)

        res.form["login"] = "user"
        res = res.form.submit(status=302)
        res = res.follow(status=200)

        res.form["otp"] = generate_otp("TOTP", user.secret_token, user.hotp_counter)
        traveller.shift(datetime.timedelta(seconds=30))
        res = res.form.submit()

        assert (
            "error",
            "The passcode you entered is invalid. Please try again",
        ) in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Failed OTP authentication for user",
        ) in caplog.record_tuples


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_signin_invalid_otp_chars(testclient, user, caplog, otp_method):
    """Test putting unicode characters in the OTP field."""
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    with testclient.session_transaction() as session:
        assert not session.get("sessions")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["otp"] = "●●●●●●"
    res = res.form.submit()

    assert (
        "error",
        "The passcode you entered is invalid. Please try again",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Failed OTP authentication for user",
    ) in caplog.record_tuples


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_setup_otp(testclient, backend, caplog, otp_method):
    """Users who have never logged in with OTP should be shown the OTP setup screen."""
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    user = models.User(
        formatted_name="Otp User",
        family_name="Otp",
        user_name="otp",
        emails=["john@doe.test"],
        password="correct horse battery staple",
    )
    backend.save(user)

    if otp_method == "HOTP":
        assert user.hotp_counter is None

    with testclient.session_transaction() as session:
        assert not session.get("sessions")

    res = testclient.get("/login", status=200)

    res.form["login"] = "otp"
    res = res.form.submit(status=302)
    res = res.follow(status=302)

    assert res.location == "/auth/otp-setup"
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        secret_token = (
            session["auth"]["data"]["otp_user_secret"]
            if "data" in session["auth"]
            else None
        )

    res.form["otp"] = generate_otp(otp_method, secret_token, user.hotp_counter)
    res = res.form.submit(status=302)

    backend.reload(user)
    if otp_method == "HOTP":
        assert user.hotp_counter == 1

    assert (
        "success",
        "Connection successful. Welcome Otp User",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Successful authentication for otp",
    ) in caplog.record_tuples
    res = res.follow(status=302)
    res = res.follow(status=200)

    backend.delete(user)


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_setup_otp_bad_otp(testclient, backend, caplog, otp_method):
    """Users who have never logged in with OTP should be shown the OTP setup screen."""
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    user = models.User(
        formatted_name="Otp User",
        family_name="Otp",
        user_name="otp",
        emails=["john@doe.test"],
        password="correct horse battery staple",
    )
    backend.save(user)

    if otp_method == "HOTP":
        assert user.hotp_counter is None

    with testclient.session_transaction() as session:
        assert not session.get("sessions")

    res = testclient.get("/login", status=200)

    res.form["login"] = "otp"
    res = res.form.submit(status=302)
    res = res.follow(status=302)

    assert res.location == "/auth/otp-setup"
    res = res.follow(status=200)

    res.form["otp"] = 111111
    res = res.form.submit(status=200)

    assert (
        "error",
        "The passcode you entered is invalid. Please try again.",
    ) in res.flashes

    backend.reload(user)
    assert not user.secret_token

    backend.delete(user)


def test_signin_multiple_attempts_doesnt_desynchronize_hotp(testclient, user, caplog):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = "HOTP"

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    for _ in range(3):
        res.form["otp"] = "111111"
        res = res.form.submit(status=200)

    res.form["otp"] = generate_otp("HOTP", user.secret_token, user.hotp_counter)
    res = res.form.submit(status=302)

    assert (
        "success",
        "Connection successful. Welcome Johnny",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Successful authentication for user",
    ) in caplog.record_tuples


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_setup_otp_page_already_logged_in(testclient, logged_user, otp_method):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method

    res = testclient.get("/auth/otp-setup", status=302)
    assert res.location == "/profile/user/settings"


def test_signin_inside_hotp_look_ahead_window(testclient, backend, user, caplog):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = "HOTP"

    assert user.hotp_counter == 1

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["otp"] = generate_otp(
        "HOTP", user.secret_token, user.hotp_counter + HOTP_LOOK_AHEAD_WINDOW
    )

    res = res.form.submit(status=302)

    assert (
        "success",
        "Connection successful. Welcome Johnny",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Successful authentication for user",
    ) in caplog.record_tuples

    user = backend.get(models.User, id=user.id)
    assert user.hotp_counter == HOTP_LOOK_AHEAD_WINDOW + 2


def test_signin_outside_hotp_look_ahead_window(testclient, backend, user, caplog):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = "HOTP"

    assert user.hotp_counter == 1

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["otp"] = generate_otp(
        "HOTP", user.secret_token, user.hotp_counter + HOTP_LOOK_AHEAD_WINDOW + 1
    )
    res = res.form.submit(status=200)

    assert (
        "error",
        "The passcode you entered is invalid. Please try again",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Failed OTP authentication for user",
    ) in caplog.record_tuples

    user = backend.get(models.User, id=user.id)
    assert user.hotp_counter == 1
