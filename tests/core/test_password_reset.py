from canaille.core.endpoints.account import build_hash


def test_password_reset(testclient, user):
    assert not user.check_password("foobarbaz")[0]
    hash = build_hash("user", user.preferred_email, user.password)

    res = testclient.get("/reset/user/" + hash, status=200)

    res.form["password"] = "foobarbaz"
    res.form["confirmation"] = "foobarbaz"
    res = res.form.submit()
    assert ("success", "Your password has been updated successfully") in res.flashes
    assert res.location == "/profile/user"

    user.reload()
    assert user.check_password("foobarbaz")[0]

    res = testclient.get("/reset/user/" + hash)
    assert (
        "error",
        "The password reset link that brought you here was invalid.",
    ) in res.flashes


def test_password_reset_multiple_emails(testclient, user):
    user.emails = ["foo@bar.com", "foo@baz.com"]
    user.save()

    assert not user.check_password("foobarbaz")[0]
    hash = build_hash("user", "foo@baz.com", user.password)

    res = testclient.get("/reset/user/" + hash, status=200)

    res.form["password"] = "foobarbaz"
    res.form["confirmation"] = "foobarbaz"
    res = res.form.submit()
    assert ("success", "Your password has been updated successfully") in res.flashes

    user.reload()
    assert user.check_password("foobarbaz")[0]

    res = testclient.get("/reset/user/" + hash)
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


def test_password_reset_bad_password(testclient, user):
    hash = build_hash("user", user.preferred_email, user.password)

    res = testclient.get("/reset/user/" + hash, status=200)

    res.form["password"] = "foobarbaz"
    res.form["confirmation"] = "typo"
    res = res.form.submit(status=200)

    assert user.check_password("correct horse battery staple")[0]


def test_unavailable_if_no_smtp(testclient, user):
    res = testclient.get("/login")
    res.mustcontain("Forgotten password")

    res.form["login"] = "user"
    res = res.form.submit()
    res = res.follow()
    res.mustcontain("Forgotten password")

    testclient.get("/reset", status=200)

    del testclient.app.config["CANAILLE"]["SMTP"]

    res = testclient.get("/login")
    res.mustcontain(no="Forgotten password")

    res.form["login"] = "user"
    res = res.form.submit()
    res = res.follow()
    res.mustcontain(no="Forgotten password")

    testclient.get("/reset", status=500, expect_errors=True)
