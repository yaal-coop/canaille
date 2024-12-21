import datetime
import logging

import pytest
import time_machine

import tests.conftest
from canaille.app import mask_email
from canaille.app import mask_phone
from canaille.core.models import OTP_VALIDITY
from canaille.core.models import SEND_NEW_OTP_DELAY


def test_email_otp_disabled(testclient):
    testclient.app.config["CANAILLE"]["EMAIL_OTP"] = None
    with testclient.session_transaction() as session:
        session["remaining_otp_methods"] = ["EMAIL_OTP"]
        session["attempt_login_with_correct_password"] = "id"
    testclient.get("/verify-mfa", status=404)

    testclient.app.config["WTF_CSRF_ENABLED"] = False
    testclient.post("/send-mail-otp", status=404)


def test_sms_otp_disabled(testclient):
    testclient.app.config["CANAILLE"]["SMS_OTP"] = None
    with testclient.session_transaction() as session:
        session["remaining_otp_methods"] = ["SMS_OTP"]
        session["attempt_login_with_correct_password"] = "id"
    testclient.get("/verify-mfa", status=404)

    testclient.app.config["WTF_CSRF_ENABLED"] = False
    testclient.post("/send-sms-otp", status=404)


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
        "A one-time password has been sent to your email address j#####n@doe.test. Please enter it below to login.",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Sent one-time password for user to john@doe.test from unknown IP",
    ) in caplog.record_tuples
    res = res.follow(status=200)
    with testclient.session_transaction() as session:
        assert "attempt_login" not in session
        assert "user" == session.get("attempt_login_with_correct_password")

    res = testclient.get("/verify-mfa")

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


def test_signin_with_email_otp_failed_to_send_code(testclient, user):
    testclient.app.config["CANAILLE"]["EMAIL_OTP"] = True
    testclient.app.config["CANAILLE"]["SMTP"]["HOST"] = "invalid host"

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
        "danger",
        "Error while sending one-time password. Please try again.",
    ) in res.flashes

    assert res.location == "/password"


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
        main_form["otp"] = user.generate_and_send_otp_mail()

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


def test_signin_expired_sms_otp(testclient, user, caplog, mock_smpp):
    testclient.app.config["CANAILLE"]["SMS_OTP"] = True

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
        otp = user.generate_and_send_otp_sms()
        main_form["otp"] = otp
        assert otp in str(tests.conftest.pdu.generate())
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


def test_signin_and_out_with_sms_otp(testclient, backend, user, caplog, mock_smpp):
    testclient.app.config["CANAILLE"]["SMS_OTP"] = True

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
        "A one-time password has been sent to your phone number 555#####00. Please enter it below to login.",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Sent one-time password for user to 555-000-000 from unknown IP",
    ) in caplog.record_tuples
    res = res.follow(status=200)
    with testclient.session_transaction() as session:
        assert "attempt_login" not in session
        assert "user" == session.get("attempt_login_with_correct_password")

    res = testclient.get("/verify-mfa")

    backend.reload(user)
    otp = user.one_time_password

    main_form = res.forms[0]
    main_form["otp"] = otp
    assert otp in str(tests.conftest.pdu.generate())

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


def test_signin_with_sms_otp_failed_to_send_code(testclient, user):
    testclient.app.config["CANAILLE"]["SMS_OTP"] = True
    testclient.app.config["CANAILLE"]["SMPP"]["HOST"] = "invalid host"

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
        "danger",
        "Error while sending one-time password. Please try again.",
    ) in res.flashes

    assert res.location == "/password"


def test_signin_wrong_sms_otp(testclient, user, caplog, mock_smpp):
    testclient.app.config["CANAILLE"]["SMS_OTP"] = True

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


@pytest.mark.parametrize("otp_method", ["EMAIL_OTP", "SMS_OTP"])
def test_verify_mail_or_sms_otp_page_without_signin_in_redirects_to_login_page(
    testclient, user, otp_method
):
    testclient.app.config["CANAILLE"][otp_method] = True

    res = testclient.get("/verify-mfa", status=302)
    assert res.location == "/login"
    assert res.flashes == [
        ("warning", "Cannot remember the login you attempted to sign in with")
    ]


@pytest.mark.parametrize("otp_method", ["EMAIL_OTP", "SMS_OTP"])
def test_verify_mail_or_sms_otp_page_already_logged_in(
    testclient, logged_user, otp_method
):
    testclient.app.config["CANAILLE"][otp_method] = True

    res = testclient.get("/verify-mfa", status=302)
    assert res.location == "/profile/user"


def test_mask_email():
    email = "foo@bar.com"
    assert mask_email(email) == "f#####o@bar.com"

    email = "hello"
    assert mask_email(email) is None


def test_mask_phone_number():
    phone = "+33123456789"
    assert mask_phone(phone) == "+33#####89"


@pytest.mark.parametrize(
    "otp_method,new_otp_path",
    [("EMAIL_OTP", "/send-mail-otp"), ("SMS_OTP", "/send-sms-otp")],
)
def test_send_new_mail_or_sms_otp_without_signin_in_redirects_to_login_page(
    testclient, user, otp_method, new_otp_path
):
    testclient.app.config["CANAILLE"][otp_method] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    res = testclient.post(new_otp_path, status=302)
    assert res.location == "/login"
    assert res.flashes == [
        ("warning", "Cannot remember the login you attempted to sign in with")
    ]


@pytest.mark.parametrize(
    "otp_method,new_otp_path",
    [("EMAIL_OTP", "/send-mail-otp"), ("SMS_OTP", "/send-sms-otp")],
)
def test_send_new_mail_or_sms_otp_already_logged_in(
    testclient, logged_user, otp_method, new_otp_path
):
    testclient.app.config["CANAILLE"][otp_method] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    res = testclient.post(new_otp_path, status=302)
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
        "Sent one-time password for user to john@doe.test from unknown IP",
    ) in caplog.record_tuples

    assert res.location == "/verify-mfa"


def test_send_mail_otp_multiple_attempts(testclient, backend, user, caplog):
    testclient.app.config["CANAILLE"]["EMAIL_OTP"] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False) as traveller:
        with testclient.session_transaction() as session:
            session["attempt_login_with_correct_password"] = user.user_name

        res = testclient.post("/send-mail-otp", status=302)
        assert res.location == "/verify-mfa"

        traveller.shift(datetime.timedelta(seconds=SEND_NEW_OTP_DELAY - 1))
        res = testclient.post("/send-mail-otp", status=302)
        assert (
            "danger",
            f"Too many attempts. Please try again in {SEND_NEW_OTP_DELAY} seconds.",
        ) in res.flashes
        assert res.location == "/verify-mfa"

        traveller.shift(datetime.timedelta(seconds=1))

        res = testclient.post("/send-mail-otp", status=302)
        assert (
            "success",
            "Code successfully sent!",
        ) in res.flashes


def test_send_new_mail_otp_failed(testclient, user):
    testclient.app.config["CANAILLE"]["EMAIL_OTP"] = True
    testclient.app.config["CANAILLE"]["SMTP"]["HOST"] = "invalid host"
    testclient.app.config["WTF_CSRF_ENABLED"] = False
    with testclient.session_transaction() as session:
        session["attempt_login_with_correct_password"] = user.user_name

    res = testclient.post("/send-mail-otp", status=302)

    assert (
        "danger",
        "Error while sending one-time password. Please try again.",
    ) in res.flashes

    assert res.location == "/verify-mfa"


def test_send_new_sms_otp(testclient, backend, user, caplog, mock_smpp):
    testclient.app.config["CANAILLE"]["SMS_OTP"] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False
    with testclient.session_transaction() as session:
        session["attempt_login_with_correct_password"] = user.user_name

    res = testclient.post("/send-sms-otp", status=302)

    backend.reload(user)
    otp = user.one_time_password

    assert otp in str(tests.conftest.pdu.generate())

    assert (
        "success",
        "Code successfully sent!",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Sent one-time password for user to 555-000-000 from unknown IP",
    ) in caplog.record_tuples

    assert res.location == "/verify-mfa"


def test_send_sms_otp_multiple_attempts(testclient, backend, user, caplog, mock_smpp):
    testclient.app.config["CANAILLE"]["SMS_OTP"] = True
    testclient.app.config["WTF_CSRF_ENABLED"] = False

    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False) as traveller:
        with testclient.session_transaction() as session:
            session["attempt_login_with_correct_password"] = user.user_name

        res = testclient.post("/send-sms-otp", status=302)
        assert res.location == "/verify-mfa"

        traveller.shift(datetime.timedelta(seconds=SEND_NEW_OTP_DELAY - 1))
        res = testclient.post("/send-sms-otp", status=302)
        assert (
            "danger",
            f"Too many attempts. Please try again in {SEND_NEW_OTP_DELAY} seconds.",
        ) in res.flashes
        assert res.location == "/verify-mfa"

        traveller.shift(datetime.timedelta(seconds=1))

        res = testclient.post("/send-sms-otp", status=302)
        assert (
            "success",
            "Code successfully sent!",
        ) in res.flashes


def test_send_new_sms_otp_failed(testclient, user):
    testclient.app.config["CANAILLE"]["SMS_OTP"] = True
    testclient.app.config["CANAILLE"]["SMPP"]["HOST"] = "invalid host"
    testclient.app.config["WTF_CSRF_ENABLED"] = False
    with testclient.session_transaction() as session:
        session["attempt_login_with_correct_password"] = user.user_name

    res = testclient.post("/send-sms-otp", status=302)

    assert (
        "danger",
        "Error while sending one-time password. Please try again.",
    ) in res.flashes

    assert res.location == "/verify-mfa"


def test_signin_with_multiple_otp_methods(
    smtpd, testclient, backend, user_otp, caplog, mock_smpp
):
    testclient.app.config["CANAILLE"]["OTP_METHOD"] = "HOTP"
    testclient.app.config["CANAILLE"]["EMAIL_OTP"] = True
    testclient.app.config["CANAILLE"]["SMS_OTP"] = True

    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert "user" == session.get("attempt_login")

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302).follow(status=200)

    with testclient.session_transaction() as session:
        assert "attempt_login" not in session
        assert "user" == session.get("attempt_login_with_correct_password")

    # TOTP/HOTP
    res = testclient.get("/verify-mfa")
    res.form["otp"] = user_otp.generate_otp()
    res = res.form.submit(status=302).follow(status=200)

    # EMAIL_OTP
    res = testclient.get("/verify-mfa")
    backend.reload(user_otp)
    otp = user_otp.one_time_password
    main_form = res.forms[0]
    main_form["otp"] = otp
    res = main_form.submit(status=302).follow(status=200)

    # SMS_OTP
    res = testclient.get("/verify-mfa")
    backend.reload(user_otp)
    otp = user_otp.one_time_password
    main_form = res.forms[0]
    main_form["otp"] = otp
    res = main_form.submit(status=302).follow(status=302).follow(status=200)

    with testclient.session_transaction() as session:
        assert [user_otp.id] == session.get("user_id")
        assert "attempt_login" not in session
        assert "attempt_login_with_correct_password" not in session

    res = testclient.get("/login", status=302)


def test_send_password_form_multiple_times(smtpd, testclient, backend, user, caplog):
    testclient.app.config["CANAILLE"]["EMAIL_OTP"] = True

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)

    with testclient.session_transaction() as session:
        session["attempt_login"] = user.user_name
        del session["attempt_login_with_correct_password"]

    res = testclient.get("/password", status=200)
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)

    assert (
        "danger",
        f"Too many attempts. Please try again in {SEND_NEW_OTP_DELAY} seconds.",
    ) in res.flashes
    assert res.location == "/password"
