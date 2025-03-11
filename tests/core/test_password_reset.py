import datetime

import time_machine

from canaille.core.models import OTP_VALIDITY


def test_password_reset(testclient, user, backend):
    assert not backend.check_user_password(user, "foobarbaz")[0]
    token = user.generate_url_safe_token()
    backend.save(user)

    res = testclient.get("/reset/user/" + token, status=200)

    res.form["password"] = "foobarbaz"
    res.form["confirmation"] = "foobar"
    res = res.form.submit()
    res.mustcontain("Password and confirmation do not match.")
    res.mustcontain('data-percent="50"')

    res.form["password"] = "123"
    res.form["confirmation"] = "123"
    res = res.form.submit()
    res.mustcontain("Field must be at least 8 characters long.")

    res.form["password"] = "foobarbaz"
    res.form["confirmation"] = "foobarbaz"
    res = res.form.submit()
    assert ("success", "Your password has been updated successfully") in res.flashes
    assert res.location == "/profile/user"

    backend.reload(user)
    assert backend.check_user_password(user, "foobarbaz")[0]
    assert not user.one_time_password
    assert not user.one_time_password_emission_date

    res = testclient.get("/reset/user/" + token)
    assert (
        "error",
        "The password reset link that brought you here was invalid.",
    ) in res.flashes


def test_password_reset_expired_token(testclient, user, backend):
    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False) as traveller:
        token = user.generate_url_safe_token()
        backend.save(user)

        res = testclient.get("/reset/user/" + token, status=200)

        traveller.shift(datetime.timedelta(seconds=OTP_VALIDITY))

        res = testclient.get("/reset/user/" + token)
        assert (
            "error",
            "The password reset link that brought you here was invalid.",
        ) in res.flashes


def test_password_reset_multiple_emails(testclient, user, backend):
    user.emails = ["foo@bar.test", "foo@baz.test"]
    backend.save(user)

    assert not backend.check_user_password(user, "foobarbaz")[0]
    token = user.generate_url_safe_token()
    backend.save(user)

    res = testclient.get("/reset/user/" + token, status=200)

    res.form["password"] = "foobarbaz"
    res.form["confirmation"] = "foobarbaz"
    res = res.form.submit()
    assert ("success", "Your password has been updated successfully") in res.flashes

    backend.reload(user)
    assert backend.check_user_password(user, "foobarbaz")[0]

    res = testclient.get("/reset/user/" + token)
    assert (
        "error",
        "The password reset link that brought you here was invalid.",
    ) in res.flashes


def test_password_reset_bad_link(testclient, user):
    res = testclient.get("/reset/user/foobarbaz")
    assert (
        "error",
        "The password reset link that brought you here was invalid.",
    ) in res.flashes


def test_password_reset_bad_password(testclient, user, backend):
    token = user.generate_url_safe_token()
    backend.save(user)

    res = testclient.get("/reset/user/" + token, status=200)

    res.form["password"] = "foobarbaz"
    res.form["confirmation"] = "typo"
    res = res.form.submit(status=200)

    assert backend.check_user_password(user, "correct horse battery staple")[0]


def test_unavailable_if_no_smtp(testclient, user):
    res = testclient.get("/login")
    res.mustcontain("Forgotten password")

    res.form["login"] = "user"
    res = res.form.submit()
    res = res.follow()
    res.mustcontain("Forgotten password")

    testclient.get("/reset", status=200)

    testclient.app.config["CANAILLE"]["SMTP"] = None

    res = testclient.get("/login")
    res.mustcontain(no="Forgotten password")

    res.form["login"] = "user"
    res = res.form.submit()
    res = res.follow()
    res.mustcontain(no="Forgotten password")

    testclient.get("/reset", status=500, expect_errors=True)
