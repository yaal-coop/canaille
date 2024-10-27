import logging
from logging.config import dictConfig
from logging.config import fileConfig


def add_log_level(level_name, level_num, method_name=None):
    """
    Adapted from https://stackoverflow.com/a/35804945/2700168

    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.
    `level_name` becomes an attribute of the `logging` module with the value
    `level_num`.
    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present
    Example
    -------
    >>> addLoggingLevel("TRACE", logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace("that worked")
    >>> logging.trace("so did this")
    >>> logging.TRACE
    5
    """
    if not method_name:
        method_name = level_name.lower()

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def log_for_level(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            self._log(level_num, message, args, **kwargs)

    def log_to_root(message, *args, **kwargs):
        logging.log(level_num, message, *args, **kwargs)

    logging.addLevelName(level_num, level_name)
    setattr(logging, level_name, level_num)
    setattr(logging.getLoggerClass(), method_name, log_for_level)
    setattr(logging, method_name, log_to_root)


def setup_logging(app):
    conf = app.config["CANAILLE"]["LOGGING"]

    security_level_name = "SECURITY"
    security_level = logging.INFO + 5

    if not hasattr(logging, security_level_name):
        add_log_level(security_level_name, security_level)

    if conf is None:
        log_level = "DEBUG" if app.debug else "INFO"
        dictConfig(
            {
                "version": 1,
                "formatters": {
                    "default": {
                        "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                    }
                },
                "handlers": {
                    "wsgi": {
                        "class": "logging.StreamHandler",
                        "stream": "ext://flask.logging.wsgi_errors_stream",
                        "formatter": "default",
                    }
                },
                "root": {"level": log_level, "handlers": ["wsgi"]},
                "loggers": {
                    "faker": {"level": "WARNING"},
                    "mail.log": {"level": "WARNING"},
                },
                "disable_existing_loggers": False,
            }
        )

    elif isinstance(conf, dict):
        dictConfig(conf)

    else:
        fileConfig(conf, disable_existing_loggers=False)
