import logging
import smtplib
import warnings
from unittest import mock

import pytest
from flask_webtest import TestApp

from canaille import create_app
from canaille.app.mails import type_from_filename


@pytest.fixture
def configuration(configuration, httpserver):
    configuration["SERVER_NAME"] = f"{httpserver.host}:{httpserver.port}"
    configuration["WTF_CSRF_ENABLED"] = False
    return configuration


def test_send_test_email(testclient, logged_admin, smtpd, caplog):
    assert len(smtpd.messages) == 0

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.test"
    res = res.form.submit()

    assert (
        "info",
        "Sending test mail. Please check the recipient mail box.",
    ) in res.flashes

    assert (
        "canaille",
        logging.INFO,
        "The mail has been sent correctly.",
    ) in caplog.record_tuples

    assert len(smtpd.messages) == 1


def test_send_test_email_ssl(testclient, logged_admin, smtpd, caplog):
    smtpd.config.use_ssl = True
    smtpd.config.use_starttls = False

    testclient.app.config["CANAILLE"]["SMTP"]["SSL"] = True
    testclient.app.config["CANAILLE"]["SMTP"]["TLS"] = False
    testclient.app.config["CANAILLE"]["SMTP"]["LOGIN"] = None
    testclient.app.config["CANAILLE"]["SMTP"]["PASSWORD"] = None

    assert len(smtpd.messages) == 0

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.test"
    res = res.form.submit()

    assert (
        "info",
        "Sending test mail. Please check the recipient mail box.",
    ) in res.flashes

    assert (
        "canaille",
        logging.INFO,
        "The mail has been sent correctly.",
    ) in caplog.record_tuples

    assert len(smtpd.messages) == 1


def test_send_test_email_without_credentials(testclient, logged_admin, smtpd, caplog):
    testclient.app.config["CANAILLE"]["SMTP"]["LOGIN"] = None
    testclient.app.config["CANAILLE"]["SMTP"]["PASSWORD"] = None

    assert len(smtpd.messages) == 0

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.test"
    res = res.form.submit()

    assert (
        "info",
        "Sending test mail. Please check the recipient mail box.",
    ) in res.flashes

    assert (
        "canaille",
        logging.INFO,
        "The mail has been sent correctly.",
    ) in caplog.record_tuples

    assert len(smtpd.messages) == 1


@mock.patch("smtplib.SMTP")
def test_send_test_email_recipient_refused(
    SMTP, testclient, logged_admin, smtpd, caplog
):
    SMTP.side_effect = mock.Mock(
        side_effect=smtplib.SMTPRecipientsRefused("test@test.test")
    )
    assert len(smtpd.messages) == 0

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.test"
    res = res.form.submit()

    assert (
        "info",
        "Sending test mail. Please check the recipient mail box.",
    ) in res.flashes

    assert (
        "canaille",
        logging.INFO,
        "The mail has been sent correctly.",
    ) in caplog.record_tuples

    assert len(smtpd.messages) == 0


def test_send_test_email_failed(testclient, logged_admin, caplog, smtpd):
    assert len(smtpd.messages) == 0
    testclient.app.config["CANAILLE"]["SMTP"]["TLS"] = False
    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.test"
    with warnings.catch_warnings(record=True):
        res = res.form.submit(expect_errors=True)

    assert (
        "info",
        "Sending test mail. Please check the recipient mail box.",
    ) in res.flashes

    assert (
        "canaille",
        logging.WARNING,
        "Could not send email: SMTP AUTH extension not supported by server.",
    ) in caplog.record_tuples

    assert len(smtpd.messages) == 0


def test_mail_with_default_no_logo(testclient, logged_admin, smtpd, caplog):
    testclient.app.config["CANAILLE"]["LOGO"] = None
    assert len(smtpd.messages) == 0

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.test"
    res = res.form.submit()

    assert (
        "info",
        "Sending test mail. Please check the recipient mail box.",
    ) in res.flashes

    assert (
        "canaille",
        logging.INFO,
        "The mail has been sent correctly.",
    ) in caplog.record_tuples

    assert len(smtpd.messages) == 1
    html_message = smtpd.messages[0].get_payload()[1]
    html_content = html_message.get_payload(decode=True).decode()
    assert "cid" not in html_content


def test_mail_with_default_logo(testclient, logged_admin, smtpd, httpserver, caplog):
    logo_path = "/static/img/canaille-head.webp"
    with open(f"canaille/{logo_path}", "rb") as fd:
        raw_logo = fd.read()

    httpserver.expect_request(logo_path).respond_with_data(raw_logo)
    assert len(smtpd.messages) == 0

    res = testclient.get(f"http://{httpserver.host}:{httpserver.port}/admin/mail")
    res.form["email"] = "test@test.test"
    res = res.form.submit()

    assert (
        "info",
        "Sending test mail. Please check the recipient mail box.",
    ) in res.flashes

    assert (
        "canaille",
        logging.INFO,
        "The mail has been sent correctly.",
    ) in caplog.record_tuples

    assert len(smtpd.messages) == 1
    html_message = smtpd.messages[0].get_payload()[1]
    html_content = html_message.get_payload()[0].get_payload(decode=True).decode()
    raw_payload = html_message.get_payload()[1].get_payload(decode=True)
    cid = html_message.get_payload()[1].get("Content-ID")[1:-1]
    assert cid in html_content
    assert raw_payload == raw_logo


def test_mail_with_logo_in_http(testclient, logged_admin, smtpd, httpserver, caplog):
    logo_path = "/static/img/canaille-head.webp"
    with open(f"canaille/{logo_path}", "rb") as fd:
        raw_logo = fd.read()

    httpserver.expect_request(logo_path).respond_with_data(raw_logo)
    testclient.app.config["CANAILLE"]["LOGO"] = (
        f"http://{httpserver.host}:{httpserver.port}{logo_path}"
    )
    assert len(smtpd.messages) == 0

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.test"
    res = res.form.submit()

    assert (
        "info",
        "Sending test mail. Please check the recipient mail box.",
    ) in res.flashes

    assert (
        "canaille",
        logging.INFO,
        "The mail has been sent correctly.",
    ) in caplog.record_tuples

    assert len(smtpd.messages) == 1
    html_message = smtpd.messages[0].get_payload()[1]
    html_content = html_message.get_payload()[0].get_payload(decode=True).decode()
    raw_payload = html_message.get_payload()[1].get_payload(decode=True)
    cid = html_message.get_payload()[1].get("Content-ID")[1:-1]
    assert cid in html_content
    assert raw_payload == raw_logo


def test_mail_debug_pages(testclient, logged_admin):
    for base in [
        "test",
        "password-init",
        "reset",
        "admin/admin@admin.com/invitation",
        "admin/admin@admin.com/email-confirmation",
        "admin@admin.com/registration",
        "compromised_password_check_failure",
        "email_otp",
    ]:
        testclient.get(f"/admin/mail/{base}.html")
        testclient.get(f"/admin/mail/{base}.txt")


def test_custom_from_addr(testclient, user, smtpd):
    testclient.app.config["CANAILLE"]["NAME"] = "My Canaille"
    res = testclient.get("/reset", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert smtpd.messages[0]["X-MailFrom"] == "admin@mydomain.test"
    assert smtpd.messages[0]["From"] == '"My Canaille" <admin@mydomain.test>'


def test_default_from_addr(testclient, user, smtpd):
    testclient.app.config["CANAILLE"]["SMTP"]["FROM_ADDR"] = None
    res = testclient.get("/reset", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert smtpd.messages[0]["X-MailFrom"] == "admin@localhost"
    assert smtpd.messages[0]["From"] == '"Canaille" <admin@localhost>'


def test_default_with_no_flask_server_name(configuration, user, smtpd, backend):
    del configuration["SERVER_NAME"]
    configuration["CANAILLE"]["SMTP"]["FROM_ADDR"] = None
    app = create_app(configuration, backend=backend)

    testclient = TestApp(app)
    res = testclient.get("/reset", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert smtpd.messages[0]["X-MailFrom"] == "admin@localhost"
    assert smtpd.messages[0]["From"] == '"Canaille" <admin@localhost>'


def test_default_from_flask_server_name(configuration, user, smtpd, backend):
    app = create_app(configuration, backend=backend)
    app.config["CANAILLE"]["SMTP"]["FROM_ADDR"] = None
    app.config["SERVER_NAME"] = "foobar.test"

    testclient = TestApp(app)
    res = testclient.get("/reset", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert smtpd.messages[0]["X-MailFrom"] == "admin@foobar.test"
    assert smtpd.messages[0]["From"] == '"Canaille" <admin@foobar.test>'


def test_type_from_filename():
    assert type_from_filename("index.html") == ("text", "html")
    assert type_from_filename("unknown") == ("application", "octet-stream")
