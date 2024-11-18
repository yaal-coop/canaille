import datetime
import logging

import time_machine

from canaille.app import mask_email
from canaille.core.models import OTP_VALIDITY


def test_email_otp_disabled(testclient):
    testclient.app.config["CANAILLE"]["EMAIL_OTP"] = None
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    testclient.get("/verify-2fa", status=404)
    testclient.post("/send-mail-otp", status=404)


def test_signin_and_out_with_email_otp(smtpd, testclient, backend, user, caplog):
    testclient.app.config["CANAILLE"]["EMAIL_OTP"] = True

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
        "A one-time password has been sent to your email address j#####n@doe.com. Please enter it below to login.",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Sent one-time password for user to john@doe.com from unknown IP",
    ) in caplog.record_tuples
    res = res.follow(status=200)
    with testclient.session_transaction() as session:
        assert "attempt_login" not in session
        assert "user" == session.get("attempt_login_with_correct_password")

    res = testclient.get("/verify-2fa")

    backend.reload(user)
    otp = user.one_time_password
    assert len(smtpd.messages) == 1
    email_content = str(smtpd.messages[0].get_payload()[0]).replace("=\n", "")
    assert otp in email_content

    main_form = res.forms[0]
    main_form["otp"] = otp
    res = main_form.submit(status=302)

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
        assert [user.id] == session.get("user_id")
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


def test_signin_wrong_email_otp(testclient, user, caplog):
    testclient.app.config["CANAILLE"]["EMAIL_OTP"] = True

    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    main_form = res.forms[0]
    main_form["otp"] = 111111
    res = main_form.submit()

    assert (
        "error",
        "The one-time password you entered is invalid. Please try again",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Failed login attempt (wrong OTP) for user from unknown IP",
    ) in caplog.record_tuples


def test_signin_expired_email_otp(testclient, user, caplog):
    testclient.app.config["CANAILLE"]["EMAIL_OTP"] = True

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

        main_form = res.forms[0]
        main_form["otp"] = user.generate_otp_mail()
        traveller.shift(datetime.timedelta(seconds=OTP_VALIDITY))
        res = main_form.submit()

        assert (
            "error",
            "The one-time password you entered is invalid. Please try again",
        ) in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Failed login attempt (wrong OTP) for user from unknown IP",
        ) in caplog.record_tuples


def test_verify_mail_otp_page_without_signin_in_redirects_to_login_page(
    testclient, user
):
    testclient.app.config["CANAILLE"]["EMAIL_OTP"] = True

    res = testclient.get("/verify-2fa", status=302)
    assert res.location == "/login"
    assert res.flashes == [
        ("warning", "Cannot remember the login you attempted to sign in with")
    ]


def test_verify_mail_otp_page_already_logged_in(testclient, logged_user):
    testclient.app.config["CANAILLE"]["EMAIL_OTP"] = True

    res = testclient.get("/verify-2fa", status=302)
    assert res.location == "/profile/user"


def test_mask_email():
    email = "foo@bar.com"
    assert mask_email(email) == "f#####o@bar.com"

    email = "hello"
    assert mask_email(email) is None


def test_send_new_mail_otp_without_signin_in_redirects_to_login_page(testclient, user):
    testclient.app.config["CANAILLE"]["EMAIL_OTP"] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    res = testclient.post("/send-mail-otp", status=302)
    assert res.location == "/login"
    assert res.flashes == [
        ("warning", "Cannot remember the login you attempted to sign in with")
    ]


def test_send_new_mail_otp_already_logged_in(testclient, logged_user):
    testclient.app.config["CANAILLE"]["EMAIL_OTP"] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    res = testclient.post("/send-mail-otp", status=302)
    assert res.location == "/profile/user"


def test_send_new_mail_otp(smtpd, testclient, backend, user, caplog):
    testclient.app.config["CANAILLE"]["EMAIL_OTP"] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False
    with testclient.session_transaction() as session:
        session["attempt_login_with_correct_password"] = user.user_name

    res = testclient.post("/send-mail-otp", status=302)

    backend.reload(user)
    otp = user.one_time_password
    assert len(smtpd.messages) == 1
    email_content = str(smtpd.messages[0].get_payload()[0]).replace("=\n", "")
    assert otp in email_content

    assert (
        "success",
        "Code successfully sent!",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Sent one-time password for user to john@doe.com from unknown IP",
    ) in caplog.record_tuples

    assert res.location == "/verify-2fa"
