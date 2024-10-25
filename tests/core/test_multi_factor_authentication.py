import datetime
import logging

import time_machine

from canaille.app import models


def test_totp_disabled(testclient):
    testclient.app.config["CANAILLE"]["ENABLE_TOTP"] = False

    testclient.get("/setup-2fa", status=404)
    testclient.get("/verify-2fa", status=404)


def test_signin_and_out_with_totp(testclient, user_totp, caplog):
    testclient.app.config["CANAILLE"]["ENABLE_TOTP"] = True

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

    res = testclient.get("/verify-2fa")
    res.form["otp"] = user_totp.generate_otp()
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
        assert [user_totp.id] == session.get("user_id")
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


def test_signin_wrong_totp(testclient, user_totp, caplog):
    testclient.app.config["CANAILLE"]["ENABLE_TOTP"] = True

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
        "Failed login attempt (wrong TOTP) for user from unknown IP",
    ) in caplog.record_tuples


def test_signin_expired_totp(testclient, user_totp, caplog):
    testclient.app.config["CANAILLE"]["ENABLE_TOTP"] = True

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

        res.form["otp"] = user_totp.generate_otp()
        traveller.shift(datetime.timedelta(seconds=30))
        res = res.form.submit()

        assert (
            "error",
            "The one-time password you entered is invalid. Please try again",
        ) in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Failed login attempt (wrong TOTP) for user from unknown IP",
        ) in caplog.record_tuples


def test_setup_totp(testclient, backend, caplog):
    testclient.app.config["CANAILLE"]["ENABLE_TOTP"] = True

    u = models.User(
        formatted_name="Totp User",
        family_name="Totp",
        user_name="totp",
        emails=["john@doe.com"],
        password="correct horse battery staple",
    )
    backend.save(u)

    assert u.secret_token is not None

    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/login", status=200)

    res.form["login"] = "totp"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)

    assert res.location == "/setup-2fa"
    assert (
        "info",
        "You have not enabled Two-Factor Authentication. Please enable it first to login.",
    ) in res.flashes
    res = testclient.get("/setup-2fa", status=200)
    assert u.secret_token == res.form["secret"].value

    res = testclient.get("/verify-2fa", status=200)
    res.form["otp"] = u.generate_otp()
    res = res.form.submit(status=302)

    assert (
        "success",
        "Two-factor authentication setup successful. Welcome Totp User",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Succeed login attempt for totp from unknown IP",
    ) in caplog.record_tuples
    res = res.follow(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert [u.id] == session.get("user_id")
        assert "attempt_login" not in session
        assert "attempt_login_with_correct_password" not in session

    res = testclient.get("/login", status=302)


def test_verify_totp_page_without_signin_in_redirects_to_login_page(
    testclient, user_totp
):
    testclient.app.config["CANAILLE"]["ENABLE_TOTP"] = True

    res = testclient.get("/verify-2fa", status=302)
    assert res.location == "/login"
    assert res.flashes == [
        ("warning", "Cannot remember the login you attempted to sign in with")
    ]


def test_setup_totp_page_without_signin_in_redirects_to_login_page(
    testclient, user_totp
):
    testclient.app.config["CANAILLE"]["ENABLE_TOTP"] = True

    res = testclient.get("/setup-2fa", status=302)
    assert res.location == "/login"
    assert res.flashes == [
        ("warning", "Cannot remember the login you attempted to sign in with")
    ]


def test_verify_totp_page_already_logged_in(testclient, logged_user_totp):
    testclient.app.config["CANAILLE"]["ENABLE_TOTP"] = True

    res = testclient.get("/verify-2fa", status=302)
    assert res.location == "/profile/user"


def test_setup_totp_page_already_logged_in(testclient, logged_user_totp):
    testclient.app.config["CANAILLE"]["ENABLE_TOTP"] = True

    res = testclient.get("/setup-2fa", status=302)
    assert res.location == "/profile/user"
