import os

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
    assert app.config["CANAILLE"]["SMTP"]["FROM_ADDR"] == "admin@mydomain.tld"

    del os.environ["CONFIG"]
    os.remove(config_path)


def test_file_log_config(configuration, backend, tmp_path, smtpd, admin):
    assert len(smtpd.messages) == 0
    log_path = os.path.join(tmp_path, "canaille-by-file.log")

    file_content = LOGGING_CONF_FILE_CONTENT.format(log_path=log_path)
    config_file_path = tmp_path / "logging.conf"
    with open(config_file_path, "w") as fd:
        fd.write(file_content)

    configuration["CANAILLE"]["LOGGING"] = str(config_file_path)
    app = create_app(configuration, backend=backend)

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


def test_dict_log_config(configuration, backend, tmp_path, smtpd, admin):
    assert len(smtpd.messages) == 0
    log_path = os.path.join(tmp_path, "canaille-by-dict.log")
    configuration["CANAILLE"]["LOGGING"] = {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.handlers.WatchedFileHandler",
                "filename": log_path,
                "formatter": "default",
            }
        },
        "root": {"level": "DEBUG", "handlers": ["wsgi"]},
        "loggers": {
            "faker": {"level": "WARNING"},
        },
        "disable_existing_loggers": False,
    }
    app = create_app(configuration, backend=backend)

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


LOGGING_CONF_FILE_CONTENT = """
[loggers]
keys=root

[handlers]
keys=wsgi

[formatters]
keys=default

[logger_root]
level=DEBUG
handlers=wsgi

[handler_wsgi]
class=logging.handlers.WatchedFileHandler
args=('{log_path}',)
formatter=default

[formatter_default]
format=[%(asctime)s] %(levelname)s in %(module)s: %(message)s
"""
