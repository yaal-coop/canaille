import logging
import smtplib
import urllib.error
import urllib.request
import warnings
from unittest import mock

import pytest
from flask_webtest import TestApp

from canaille import create_app
from canaille.app.mails import _read_local_logo
from canaille.app.mails import _resolve_theme_static_file
from canaille.app.mails import type_from_filename


@pytest.fixture
def configuration(configuration, httpserver):
    configuration["SERVER_NAME"] = f"{httpserver.host}:{httpserver.port}"
    configuration["WTF_CSRF_ENABLED"] = False
    return configuration


def test_send_test_email(testclient, logged_admin, smtpd, caplog):
    """Test that admin can send a test email successfully."""
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
    """Test that emails can be sent using SSL connection."""
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
    """Test that emails can be sent without SMTP authentication credentials."""
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
    """Test that SMTPRecipientsRefused error is handled gracefully when sending email."""
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
    """Test that email sending failures are reported with an error flash message."""
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
    """Test that emails can be sent without a logo when LOGO is None."""
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


def test_mail_with_default_logo(testclient, logged_admin, smtpd, caplog):
    """Test that emails include the default logo as an embedded image.

    The default ``LOGO`` points to a file served by Flask's static route.
    The logo is fetched via the in-process WSGI stack, so no HTTP loopback
    occurs.
    """
    logo_path = "/static/img/canaille-head.webp"
    with open(f"canaille/{logo_path}", "rb") as fd:
        raw_logo = fd.read()

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


def test_mail_with_logo_in_http(testclient, logged_admin, smtpd, httpserver, caplog):
    """Test that emails include custom HTTP logo as an embedded image."""
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
    """Test that all email template debug pages are accessible."""
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
    """Test that emails use custom FROM_ADDR when configured."""
    testclient.app.config["CANAILLE"]["NAME"] = "My Canaille"
    res = testclient.get("/reset", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert smtpd.messages[0]["X-MailFrom"] == "admin@mydomain.test"
    assert smtpd.messages[0]["From"] == '"My Canaille" <admin@mydomain.test>'


def test_default_from_addr(testclient, user, smtpd):
    """Test that emails use default FROM_ADDR when not configured."""
    testclient.app.config["CANAILLE"]["SMTP"]["FROM_ADDR"] = None
    res = testclient.get("/reset", status=200)
    res.form["login"] = "user"
    res = res.form.submit(status=200)
    assert smtpd.messages[0]["X-MailFrom"] == "admin@localhost"
    assert smtpd.messages[0]["From"] == '"Canaille" <admin@localhost>'


def test_default_with_no_flask_server_name(configuration, user, smtpd, backend):
    """Test that FROM_ADDR defaults to localhost when SERVER_NAME is not configured."""
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
    """Test that FROM_ADDR is derived from SERVER_NAME when FROM_ADDR is not configured."""
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
    """Test that type_from_filename correctly determines MIME types from file extensions."""
    assert type_from_filename("index.html") == ("text", "html")
    assert type_from_filename("unknown") == ("application", "octet-stream")


def test_mail_local_logo_does_not_http_loopback(
    testclient, logged_admin, smtpd, monkeypatch
):
    """Regression test for #340 (hang with SMTP + EagerBroker).

    With :class:`EagerBroker` (the default when ``BROKER_URL`` is unset), mail
    actors run synchronously in the request thread. Fetching the logo through
    an HTTP loopback to the Canaille server would deadlock a single-threaded
    server. Local logo URLs must therefore be resolved in-process without any
    network call.
    """

    def forbidden_urlopen(*args, **kwargs):  # pragma: no cover
        raise AssertionError("urlopen must not be called for local LOGO URLs")

    monkeypatch.setattr(urllib.request, "urlopen", forbidden_urlopen)

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.test"
    res.form.submit()

    assert len(smtpd.messages) == 1
    html_message = smtpd.messages[0].get_payload()[1]
    raw_payload = html_message.get_payload()[1].get_payload(decode=True)
    with open("canaille/static/img/canaille-head.webp", "rb") as fd:
        assert raw_payload == fd.read()


def test_mail_external_logo_uses_timeout(
    testclient, logged_admin, smtpd, httpserver, monkeypatch
):
    """Test that external logo fetches use a timeout.

    A slow or unreachable third-party host must not stall mail delivery.
    """
    captured = {}
    original_urlopen = urllib.request.urlopen

    def tracking_urlopen(url, *args, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        return original_urlopen(url, *args, **kwargs)

    monkeypatch.setattr(urllib.request, "urlopen", tracking_urlopen)

    logo_path = "/static/img/canaille-head.webp"
    with open(f"canaille/{logo_path}", "rb") as fd:
        raw_logo = fd.read()

    httpserver.expect_request(logo_path).respond_with_data(raw_logo)
    testclient.app.config["CANAILLE"]["LOGO"] = (
        f"http://{httpserver.host}:{httpserver.port}{logo_path}"
    )

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.test"
    res.form.submit()

    assert captured.get("timeout") is not None and captured["timeout"] > 0


def test_mail_with_missing_local_logo(testclient, logged_admin, smtpd):
    """Test mail delivery when the local logo file is missing.

    A ``LOGO`` pointing at a non-existent local path sends the mail without
    an embedded image and without raising.
    """
    testclient.app.config["CANAILLE"]["LOGO"] = "/static/img/does-not-exist.webp"

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.test"
    res.form.submit()

    assert len(smtpd.messages) == 1
    html_message = smtpd.messages[0].get_payload()[1]
    html_content = html_message.get_payload(decode=True).decode()
    assert "cid" not in html_content


def test_mail_with_unreachable_external_logo(
    testclient, logged_admin, smtpd, monkeypatch
):
    """An unreachable HTTP logo URL does not break mail delivery.

    The :func:`urllib.request.urlopen` call raises :class:`URLError` which
    ``_fetch_external_logo`` must swallow.
    """

    def raising_urlopen(*args, **kwargs):
        raise urllib.error.URLError("unreachable")

    monkeypatch.setattr(urllib.request, "urlopen", raising_urlopen)
    testclient.app.config["CANAILLE"]["LOGO"] = "http://unreachable.invalid/logo.png"

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.test"
    res.form.submit()

    assert len(smtpd.messages) == 1
    html_message = smtpd.messages[0].get_payload()[1]
    html_content = html_message.get_payload(decode=True).decode()
    assert "cid" not in html_content


def test_resolve_theme_static_file_edge_cases(configuration, backend, tmp_path):
    """Test theme static resolution edge cases.

    Returns ``None`` for malformed URLs, unknown themes, and missing files.
    """
    theme_dir = tmp_path / "mytheme"
    (theme_dir / "static").mkdir(parents=True)
    (theme_dir / "static" / "logo.png").write_bytes(b"x")

    configuration["CANAILLE"]["THEME"] = str(theme_dir)
    app = create_app(configuration, backend=backend)

    with app.app_context():
        # URL without a filename part
        assert _resolve_theme_static_file("/_theme/mytheme/") is None
        # URL without a theme name part
        assert _resolve_theme_static_file("/_theme//logo.png") is None
        # Theme that is not registered
        assert _resolve_theme_static_file("/_theme/unknown/logo.png") is None
        # Known theme but missing file
        assert _resolve_theme_static_file("/_theme/mytheme/missing.png") is None


def test_resolve_theme_static_file(configuration, backend, tmp_path):
    """Test that theme logos resolve to a file on disk.

    Logos referenced by a ``flask_themer`` theme static path must be
    resolvable without any HTTP loopback.
    """
    theme_dir = tmp_path / "mytheme"
    (theme_dir / "static").mkdir(parents=True)
    logo_bytes = b"\x89PNG\r\n\x1a\nfake-theme-logo"
    (theme_dir / "static" / "logo.png").write_bytes(logo_bytes)

    configuration["CANAILLE"]["THEME"] = str(theme_dir)
    configuration["CANAILLE"]["LOGO"] = "/_theme/mytheme/logo.png"

    app = create_app(configuration, backend=backend)

    with app.app_context():
        content = _read_local_logo("/_theme/mytheme/logo.png")

    assert content == logo_bytes
