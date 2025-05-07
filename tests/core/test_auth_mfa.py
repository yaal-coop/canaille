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
