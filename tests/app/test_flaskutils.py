import os

import pytest
import toml
from flask_webtest import TestApp

from canaille import create_app
from canaille.app.flask import set_parameter_in_url_query


def test_set_parameter_in_url_query():
    assert (
        set_parameter_in_url_query("https://auth.mydomain.tld", foo="bar")
        == "https://auth.mydomain.tld?foo=bar"
    )

    assert (
        set_parameter_in_url_query("https://auth.mydomain.tld?foo=baz", foo="bar")
        == "https://auth.mydomain.tld?foo=bar"
    )

    assert (
        set_parameter_in_url_query("https://auth.mydomain.tld?foo=baz", hello="world")
        == "https://auth.mydomain.tld?foo=baz&hello=world"
    )


def test_environment_configuration(configuration, tmp_path):
    config_path = os.path.join(tmp_path, "config.toml")
    with open(config_path, "w") as fd:
        toml.dump(configuration, fd)

    os.environ["CONFIG"] = config_path
    app = create_app()
    assert app.config["SMTP"]["FROM_ADDR"] == "admin@mydomain.tld"

    del os.environ["CONFIG"]
    os.remove(config_path)


def test_no_configuration():
    with pytest.raises(Exception) as exc:
        create_app()

    assert "No configuration file found." in str(exc)


def test_logging_to_file(configuration, backend, tmp_path, smtpd, admin):
    assert len(smtpd.messages) == 0
    log_path = os.path.join(tmp_path, "canaille.log")
    logging_configuration = {
        **configuration,
        "LOGGING": {"LEVEL": "DEBUG", "PATH": log_path},
    }
    app = create_app(logging_configuration, backend=backend)

    testclient = TestApp(app)
    with testclient.session_transaction() as sess:
        sess["user_id"] = [admin.id]

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.com"
    res = res.form.submit()

    assert len(smtpd.messages) == 1
    assert "Test email from" in smtpd.messages[0].get("Subject")

    with open(log_path) as fd:
        log_content = fd.read()

    assert "Sending a mail to test@test.com: Test email from" in log_content
