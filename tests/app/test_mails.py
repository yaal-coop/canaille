import smtplib
import warnings
from unittest import mock

from canaille import create_app
from flask_webtest import TestApp


def test_send_test_email(testclient, logged_admin, smtpd):
    assert len(smtpd.messages) == 0

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.com"
    res = res.form.submit()
    assert (
        "success",
        "The test invitation mail has been sent correctly",
    ) in res.flashes

    assert len(smtpd.messages) == 1


def test_send_test_email_ssl(testclient, logged_admin, smtpd):
    smtpd.config.use_ssl = True
    smtpd.config.use_starttls = False

    testclient.app.config["SMTP"]["SSL"] = True
    testclient.app.config["SMTP"]["TLS"] = False
    del testclient.app.config["SMTP"]["LOGIN"]
    del testclient.app.config["SMTP"]["PASSWORD"]

    assert len(smtpd.messages) == 0

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.com"
    res = res.form.submit()
    assert (
        "success",
        "The test invitation mail has been sent correctly",
    ) in res.flashes

    assert len(smtpd.messages) == 1


def test_send_test_email_without_credentials(testclient, logged_admin, smtpd):
    del testclient.app.config["SMTP"]["LOGIN"]
    del testclient.app.config["SMTP"]["PASSWORD"]

    assert len(smtpd.messages) == 0

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.com"
    res = res.form.submit()
    assert (
        "success",
        "The test invitation mail has been sent correctly",
    ) in res.flashes

    assert len(smtpd.messages) == 1


@mock.patch("smtplib.SMTP")
def test_send_test_email_recipient_refused(SMTP, testclient, logged_admin, smtpd):
    SMTP.side_effect = mock.Mock(
        side_effect=smtplib.SMTPRecipientsRefused("test@test.com")
    )
    assert len(smtpd.messages) == 0

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.com"
    res = res.form.submit()
    assert (
        "success",
        "The test invitation mail has been sent correctly",
    ) in res.flashes

    assert len(smtpd.messages) == 0


def test_send_test_email_failed(testclient, logged_admin):
    testclient.app.config["SMTP"]["TLS"] = False
    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.com"
    with warnings.catch_warnings(record=True):
        res = res.form.submit(expect_errors=True)
    assert (
        "error",
        "The test invitation mail has not been sent correctly",
    ) in res.flashes


def test_mail_with_default_no_logo(testclient, logged_admin, smtpd):
    testclient.app.config["LOGO"] = None
    assert len(smtpd.messages) == 0

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.com"
    res = res.form.submit()
    assert (
        "success",
        "The test invitation mail has been sent correctly",
    ) in res.flashes

    assert len(smtpd.messages) == 1
    html_message = smtpd.messages[0].get_payload()[1]
    html_content = html_message.get_payload(decode=True).decode()
    assert "cid" not in html_content


def test_mail_with_default_logo(testclient, logged_admin, smtpd, httpserver):
    logo_path = "/static/img/canaille-head.png"
    with open(f"canaille/{logo_path}", "rb") as fd:
        raw_logo = fd.read()

    httpserver.expect_request(logo_path).respond_with_data(raw_logo)
    testclient.app.config["SERVER_NAME"] = f"{httpserver.host}:{httpserver.port}"
    assert len(smtpd.messages) == 0

    res = testclient.get(f"http://{httpserver.host}:{httpserver.port}/admin/mail")
    res.form["email"] = "test@test.com"
    res = res.form.submit()
    assert (
        "success",
        "The test invitation mail has been sent correctly",
    ) in res.flashes

    assert len(smtpd.messages) == 1
    html_message = smtpd.messages[0].get_payload()[1]
    html_content = html_message.get_payload()[0].get_payload(decode=True).decode()
    raw_payload = html_message.get_payload()[1].get_payload(decode=True)
    cid = html_message.get_payload()[1].get("Content-ID")[1:-1]
    assert cid in html_content
    assert raw_payload == raw_logo


def test_mail_with_logo_in_http(testclient, logged_admin, smtpd, httpserver):
    logo_path = "/static/img/canaille-head.png"
    with open(f"canaille/{logo_path}", "rb") as fd:
        raw_logo = fd.read()

    httpserver.expect_request(logo_path).respond_with_data(raw_logo)
    testclient.app.config[
        "LOGO"
    ] = f"http://{httpserver.host}:{httpserver.port}{logo_path}"
    assert len(smtpd.messages) == 0

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.com"
    res = res.form.submit()
    assert (
        "success",
        "The test invitation mail has been sent correctly",
    ) in res.flashes

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
    ]:
        testclient.get(f"/admin/mail/{base}.html")
        testclient.get(f"/admin/mail/{base}.txt")


def test_custom_from_addr(testclient, user, smtpd):
    testclient.app.config["NAME"] = "My Canaille"
    res = testclient.get("/reset", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert smtpd.messages[0]["X-MailFrom"] == "admin@mydomain.tld"
    assert smtpd.messages[0]["From"] == '"My Canaille" <admin@mydomain.tld>'


def test_default_from_addr(testclient, user, smtpd):
    del testclient.app.config["SMTP"]["FROM_ADDR"]
    res = testclient.get("/reset", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert smtpd.messages[0]["X-MailFrom"] == "admin@localhost"
    assert smtpd.messages[0]["From"] == '"Canaille" <admin@localhost>'


def test_default_from_flask_server_name(configuration, user, smtpd, backend):
    app = create_app(configuration, backend=backend)
    del app.config["SMTP"]["FROM_ADDR"]
    app.config["SERVER_NAME"] = "foobar.tld"

    testclient = TestApp(app)
    res = testclient.get("/reset", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert smtpd.messages[0]["X-MailFrom"] == "admin@foobar.tld"
    assert smtpd.messages[0]["From"] == '"Canaille" <admin@foobar.tld>'
