import logging

import pytest

from canaille import add_logging_level


@pytest.fixture(autouse=True)
def run_after_tests():
    yield

    safe_delattr(logging, "test")
    safe_delattr(logging, "test1")
    safe_delattr(logging, "test2")
    safe_delattr(logging, "TEST")
    safe_delattr(logging, "TEST1")
    safe_delattr(logging, "TEST2")
    safe_delattr(logging.getLoggerClass(), "test")
    safe_delattr(logging.getLoggerClass(), "test1")
    safe_delattr(logging.getLoggerClass(), "test2")


def test_add_logging_level_nominal(testclient, caplog):
    add_logging_level("TEST", 10)

    testclient.app.logger.test("Add logging level test")

    assert (
        "canaille",
        logging.TEST,
        "Add logging level test",
    ) in caplog.record_tuples


def test_add_logging_level_getlogger(testclient, caplog):
    add_logging_level("TEST", 10)

    logger = logging.getLogger("test_logger")
    logger.test("Add logging level test")

    assert (
        "test_logger",
        logging.TEST,
        "Add logging level test",
    ) in caplog.record_tuples


def test_add_logging_level_name_already_defined():
    add_logging_level("TEST", 0, "test1")

    with pytest.raises(
        AttributeError,
        match=r"TEST already defined in logging module",
    ):
        add_logging_level("TEST", 0, "test2")


def test_add_logging_method_name_already_defined():
    add_logging_level("TEST1", 0, "test")

    with pytest.raises(
        AttributeError,
        match=r"test already defined in logging module",
    ):
        add_logging_level("TEST2", 0, "test")


def safe_delattr(self, attrname):
    if hasattr(self, attrname):
        delattr(self, attrname)
