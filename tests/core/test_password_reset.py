import time_machine

from canaille.app.session import USER_SESSION


def test_password_reset_does_not_bypass_mfa(testclient, user, backend):
    """Password reset should not automatically log in users when MFA is enabled.

    This is a security requirement: if an attacker compromises a user's email,
    they should not be able to bypass MFA by using the password reset flow.
    """
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password", "otp"]

    token = user.generate_url_safe_token()
    backend.save(user)

    res = testclient.get("/reset/user/" + token, status=200)
    res.form["password"] = "foobarbaz"
    res.form["confirmation"] = "foobarbaz"
    res = res.form.submit()

    assert ("success", "Your password has been updated successfully") in res.flashes

    # User should NOT be logged in - they need to complete MFA
    with testclient.session_transaction() as sess:
        assert USER_SESSION not in sess


def test_password_reset_logs_in_when_password_only(testclient, user, backend):
    """Password reset can log in user when password is the only authentication factor."""
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password"]

    token = user.generate_url_safe_token()
    backend.save(user)

    res = testclient.get("/reset/user/" + token, status=200)
    res.form["password"] = "foobarbaz"
    res.form["confirmation"] = "foobarbaz"
    res = res.form.submit()

    assert ("success", "Your password has been updated successfully") in res.flashes

    # User should be logged in since password is the only factor
    with testclient.session_transaction() as sess:
        assert USER_SESSION in sess


def test_password_reset(testclient, user, backend):
    """Test that password reset functionality works correctly with validation."""
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
    """Test that password reset tokens expire after the validity period."""
    with time_machine.travel("2020-01-01 01:00:00+00:00", tick=False) as traveller:
        token = user.generate_url_safe_token()
        backend.save(user)

        res = testclient.get("/reset/user/" + token, status=200)

        traveller.shift(testclient.app.config["CANAILLE"]["OTP_LIFETIME"])

        res = testclient.get("/reset/user/" + token)
        assert (
            "error",
            "The password reset link that brought you here was invalid.",
        ) in res.flashes


def test_password_reset_multiple_emails(testclient, user, backend):
    """Test that password reset works correctly for users with multiple email addresses."""
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
    """Test that accessing password reset with an invalid token shows an error."""
    res = testclient.get("/reset/user/foobarbaz")
    assert (
        "error",
        "The password reset link that brought you here was invalid.",
    ) in res.flashes


def test_password_reset_bad_password(testclient, user, backend):
    """Test that password reset fails when confirmation password does not match."""
    token = user.generate_url_safe_token()
    backend.save(user)

    res = testclient.get("/reset/user/" + token, status=200)

    res.form["password"] = "foobarbaz"
    res.form["confirmation"] = "typo"
    res = res.form.submit(status=200)

    assert backend.check_user_password(user, "correct horse battery staple")[0]


def test_unavailable_if_no_smtp(testclient, user, smtpd):
    """Test that password reset features are unavailable when SMTP is not configured."""
    res = testclient.get("/login")

    res.form["login"] = "user"
    res = res.form.submit()
    res = res.follow()
    res.mustcontain("Forgotten password")

    testclient.get("/reset", status=200)

    testclient.app.config["CANAILLE"]["SMTP"] = None

    res = testclient.get("/login")

    res.form["login"] = "user"
    res = res.form.submit()
    res = res.follow()
    res.mustcontain(no="Forgotten password")

    testclient.get("/reset", status=500, expect_errors=True)
