import logging

import pytest

from canaille.app.session import USER_SESSION
from canaille.app.session import UserSession
from tests.core.test_auth_otp import generate_otp


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_account_reset_otp(testclient, backend, caplog, logged_user, otp_method):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password", "otp"]

    assert logged_user.last_otp_login is not None

    res = testclient.get("/profile/user/settings")
    res.mustcontain("Reset")

    res = res.form.submit(name="action", value="otp-reset-confirm")
    res = res.form.submit(name="action", value="otp-reset")

    backend.reload(logged_user)
    assert logged_user.secret_token is None
    assert res.flashes == [
        ("success", "Authenticator application passcode authentication has been reset.")
    ]
    assert (
        "canaille",
        logging.SECURITY,
        "Reset one-time passcode authentication for user by user",
    ) in caplog.record_tuples


@pytest.mark.parametrize("otp_method", ["TOTP", "HOTP"])
def test_account_setup_otp(testclient, backend, logged_user, otp_method):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = otp_method
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password", "otp"]

    logged_user.secret_token = None
    backend.save(logged_user)

    res = testclient.get("/profile/user/settings")
    res.mustcontain("Set-up")

    res = res.form.submit(name="action", value="otp-setup")
    assert res.location == "/auth/otp-setup"
    res = res.follow()

    with testclient.session_transaction() as session:
        secret_token = (
            session["auth"]["data"]["otp_user_secret"]
            if "data" in session["auth"]
            else None
        )

    res.form["otp"] = generate_otp(otp_method, secret_token)
    res = res.form.submit(status=302)

    assert res.location == "/profile/user/settings"
    assert (
        "success",
        "Authenticator application correctly configured.",
    ) in res.flashes

    with testclient.session_transaction() as sess:
        user_sessions = [
            UserSession.deserialize(payload)
            for payload in sess.get(USER_SESSION, [])
            if UserSession.deserialize(payload)
        ]
        assert len(user_sessions) == 1
        assert user_sessions[0].user.id == logged_user.id

    backend.reload(logged_user)
    assert logged_user.secret_token
    if otp_method == "HOTP":
        assert logged_user.hotp_counter == 1
