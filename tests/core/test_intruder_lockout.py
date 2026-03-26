import datetime
import logging

import time_machine

from canaille.core.models import PASSWORD_MIN_DELAY


def test_intruder_lockout_fail_second_attempt_then_succeed_in_third(
    testclient, user, caplog
):
    """Test that intruder lockout delays login attempts after failures but allows success after timeout."""
    testclient.app.config["CANAILLE"]["ENABLE_INTRUDER_LOCKOUT"] = True

    with testclient.session_transaction() as session:
        assert not session.get("sessions")

    with time_machine.travel(
        datetime.datetime.now(datetime.timezone.utc),
        tick=True,
    ) as traveller:
        res = testclient.get("/login", status=200)

        res.form["login"] = "user"
        res = res.form.submit(status=302).follow()

        res.form["password"] = "incorrect horse"
        res = res.form.submit(status=200)

        assert ("error", "Login failed. Please check your information.") in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Failed password authentication for user",
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
            "Failed password authentication for user",
        ) in caplog.record_tuples

        traveller.shift(datetime.timedelta(seconds=PASSWORD_MIN_DELAY))

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(status=302)

        assert (
            "success",
            "Connection successful. Welcome Johnny",
        ) in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Successful authentication for user",
        ) in caplog.record_tuples


def test_intruder_lockout_two_consecutive_fails(testclient, user, caplog):
    """Test that intruder lockout increases delay exponentially after consecutive failed attempts."""
    testclient.app.config["CANAILLE"]["ENABLE_INTRUDER_LOCKOUT"] = True

    with time_machine.travel(
        datetime.datetime.now(datetime.timezone.utc),
        tick=True,
    ) as traveller:
        res = testclient.get("/login", status=200)

        res.form["login"] = "user"
        res = res.form.submit().follow()

        res.form["password"] = "incorrect horse"
        res = res.form.submit(status=200)

        assert ("error", "Login failed. Please check your information.") in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Failed password authentication for user",
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
            "Failed password authentication for user",
        ) in caplog.record_tuples

        traveller.shift(datetime.timedelta(seconds=PASSWORD_MIN_DELAY))

        res.form["password"] = "incorrect horse"
        res = res.form.submit(status=200)

        assert ("error", "Login failed. Please check your information.") in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Failed password authentication for user",
        ) in caplog.record_tuples

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(status=200)

        assert any(
            level == "error"
            and message.startswith("Too much attempts. Please wait for")
            for level, message in res.flashes
        )
        assert (
            "canaille",
            logging.SECURITY,
            "Failed password authentication for user",
        ) in caplog.record_tuples

        traveller.shift(datetime.timedelta(seconds=PASSWORD_MIN_DELAY * 2))

        res.form["password"] = "correct horse battery staple"
        res = res.form.submit(status=302)

        assert (
            "success",
            "Connection successful. Welcome Johnny",
        ) in res.flashes
        assert (
            "canaille",
            logging.SECURITY,
            "Successful authentication for user",
        ) in caplog.record_tuples
