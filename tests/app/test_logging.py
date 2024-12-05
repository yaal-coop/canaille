import logging
import os

from flask_webtest import TestApp

from canaille import create_app
from canaille.app.logging import add_log_level

LOGGING_CONF_FILE_CONTENT = """
[loggers]
keys=root

[handlers]
keys=wsgi

[formatters]
keys=default

[logger_root]
level={log_level}
handlers=wsgi

[handler_wsgi]
class=logging.handlers.WatchedFileHandler
args=('{log_path}',)
formatter=default

[formatter_default]
format=[%(asctime)s] %(levelname)s in %(module)s: %(message)s
"""


def test_file_log_config(configuration, backend, tmp_path, smtpd, admin):
    assert len(smtpd.messages) == 0
    log_path = os.path.join(tmp_path, "canaille-by-file.log")

    file_content = LOGGING_CONF_FILE_CONTENT.format(
        log_path=log_path, log_level="DEBUG"
    )
    config_file_path = tmp_path / "logging.conf"
    with open(config_file_path, "w") as fd:
        fd.write(file_content)

    configuration["CANAILLE"]["LOGGING"] = str(config_file_path)
    app = create_app(configuration, backend=backend)

    testclient = TestApp(app)
    with testclient.session_transaction() as sess:
        sess["user_id"] = [admin.id]

    res = testclient.get("/admin/mail")
    res.form["email"] = "test@test.test"
    res = res.form.submit()

    assert len(smtpd.messages) == 1
    assert "Test email from" in smtpd.messages[0].get("Subject")

    with open(log_path) as fd:
        log_content = fd.read()

    assert "Sending a mail to test@test.test: Test email from" in log_content


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
    res.form["email"] = "test@test.test"
    res = res.form.submit()

    assert len(smtpd.messages) == 1
    assert "Test email from" in smtpd.messages[0].get("Subject")

    with open(log_path) as fd:
        log_content = fd.read()

    assert "Sending a mail to test@test.test: Test email from" in log_content


def test_custom_root_logger(caplog):
    """Checks adding custom log levels to the root logger."""

    add_log_level("FOOBAR", logging.INFO + 6)
    logging.foobar("foobar")
    assert ("root", logging.FOOBAR, "foobar") in caplog.record_tuples

    add_log_level("FOOBAZ", logging.INFO + 7, "baz")
    logging.baz("foobar")
    assert ("root", logging.FOOBAZ, "foobar") in caplog.record_tuples


def test_custom_flask_logger(testclient, caplog):
    """Checks adding custom log levels to the Flask logger."""

    add_log_level("FOOBAR", logging.INFO + 6)
    testclient.app.logger.foobar("foobar")
    assert ("canaille", logging.FOOBAR, "foobar") in caplog.record_tuples

    add_log_level("FOOBAZ", logging.INFO + 7, "baz")
    testclient.app.logger.baz("foobar")
    assert ("canaille", logging.FOOBAZ, "foobar") in caplog.record_tuples


def test_silent_custom_logger(testclient, caplog, tmp_path, configuration, backend):
    """Checks custom log levels de-activated by configuration."""

    add_log_level("FOOBAR", logging.INFO + 6)
    add_log_level("FOOBAZ", logging.INFO + 7)

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
        "root": {"level": "FOOBAZ", "handlers": ["wsgi"]},
        "loggers": {
            "faker": {"level": "FOOBAZ"},
        },
        "disable_existing_loggers": False,
    }
    app = create_app(configuration, backend=backend)

    TestApp(app)

    testclient.app.logger.foobar("foobar")
    testclient.app.logger.foobaz("foobaz")

    with open(log_path) as fd:
        log_content = fd.read()

    assert "foobar" not in log_content
    assert "foobaz" in log_content
