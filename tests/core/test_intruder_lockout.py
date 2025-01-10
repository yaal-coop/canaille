import datetime
import logging

import time_machine

from canaille.backends.ldap.backend import LDAPBackend
from canaille.core.models import PASSWORD_MIN_DELAY


def test_intruder_lockout_fail_second_attempt_then_succeed_in_third(
    testclient, user, caplog
):
    testclient.app.config["CANAILLE"]["ENABLE_INTRUDER_LOCKOUT"] = True

    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    # add 500 milliseconds to account for LDAP time
    with time_machine.travel(
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(milliseconds=500),
        tick=False,
    ) as traveller:
        res = testclient.get("/login", status=200)

        res.form["login"] = "user"
        res = res.form.submit(status=302).follow()

        res.form["password"] = "incorrect horse"
        res = res.form.submit(status=200)

        assert ("error", "Login failed, please check your information") in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Failed login attempt for user from unknown IP",
        ) in caplog.record_tuples

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(status=200)

        assert (
            "error",
            f"Too much attempts. Please wait for {PASSWORD_MIN_DELAY} seconds before trying to login again.",
        ) in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Failed login attempt for user from unknown IP",
        ) in caplog.record_tuples

        traveller.shift(datetime.timedelta(seconds=PASSWORD_MIN_DELAY))

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(status=302)

        assert (
            "success",
            "Connection successful. Welcome John (johnny) Doe",
        ) in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Succeed login attempt for user from unknown IP",
        ) in caplog.record_tuples


def test_intruder_lockout_two_consecutive_fails(testclient, backend, user, caplog):
    testclient.app.config["CANAILLE"]["ENABLE_INTRUDER_LOCKOUT"] = True

    # add 500 milliseconds to account for LDAP time
    with time_machine.travel(
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(milliseconds=500),
        tick=False,
    ) as traveller:
        res = testclient.get("/login", status=200)

        res.form["login"] = "user"
        res = res.form.submit().follow()

        res.form["password"] = "incorrect horse"
        res = res.form.submit(status=200)

        assert ("error", "Login failed, please check your information") in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Failed login attempt for user from unknown IP",
        ) in caplog.record_tuples

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(status=200)

        assert (
            "error",
            f"Too much attempts. Please wait for {PASSWORD_MIN_DELAY} seconds before trying to login again.",
        ) in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Failed login attempt for user from unknown IP",
        ) in caplog.record_tuples

        traveller.shift(datetime.timedelta(seconds=PASSWORD_MIN_DELAY))
        ldap_shift = (
            PASSWORD_MIN_DELAY if isinstance(backend, LDAPBackend) else 0
        )  # LDAP doesn't travel in time!

        res.form["password"] = "incorrect horse"
        res = res.form.submit(status=200)

        assert ("error", "Login failed, please check your information") in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Failed login attempt for user from unknown IP",
        ) in caplog.record_tuples

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(status=200)

        assert (
            "error",
            f"Too much attempts. Please wait for {PASSWORD_MIN_DELAY * 2 - ldap_shift} seconds before trying to login again.",
        ) in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Failed login attempt for user from unknown IP",
        ) in caplog.record_tuples

        traveller.shift(datetime.timedelta(seconds=PASSWORD_MIN_DELAY * 2))

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(status=302)

        assert (
            "success",
            "Connection successful. Welcome John (johnny) Doe",
        ) in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Succeed login attempt for user from unknown IP",
        ) in caplog.record_tuples
