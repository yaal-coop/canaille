from .test_auth_otp import generate_otp


def test_signin_with_multiple_otp_methods(smtpd, testclient, backend, user):
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = [
        "password",
        "otp",
        "email",
        "sms",
    ]

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    # TOTP/HOTP
    res.form["otp"] = generate_otp("TOTP", user.secret_token)
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    # EMAIL_OTP
    backend.reload(user)
    res.form["otp"] = user.one_time_password
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    # SMS_OTP
    backend.reload(user)
    res.form["otp"] = user.one_time_password
    res = res.form.submit(status=302)

    assert (
        "success",
        "Connection successful. Welcome Johnny",
    ) in res.flashes


def test_login_page_resets_multifactor_authentication_progress(testclient, user):
    """Verify visiting login page resets any in-progress multifactor authentication session."""
    testclient.app.config["CANAILLE"]["AUTHENTICATION_FACTORS"] = ["password", "otp"]

    # Start authentication process with first user
    res = testclient.get("/login")
    res.form["login"] = user.user_name
    res = res.form.submit(status=302).follow(status=200)

    # Complete password step
    assert res.template == "core/auth/password.html"
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302).follow(status=200)

    # Should be on OTP page (second factor)
    assert res.template == "core/auth/otp.html"

    # Return to login page directly (simulating user changing mind)
    res = testclient.get("/login")

    # Submit a different username
    res.form["login"] = "differentuser"
    res = res.form.submit(status=302).follow(status=200)

    # Should be back on password page (first step) - authentication was reset
    assert res.template == "core/auth/password.html"

    # Verify we're authenticating the new user
    assert "differentuser" in res.text
