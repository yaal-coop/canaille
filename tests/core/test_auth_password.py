import logging
from unittest import mock

from canaille.core.auth import AuthenticationSession


def test_no_auth_session_not_logged_in(testclient, user):
    """Non-logged users should not be able to access the password auth form if an authentication session has not been properly started."""
    res = testclient.get("/auth/password", status=302)
    assert res.location == "/login"
    assert res.flashes == [
        ("warning", "Cannot remember the login you attempted to sign in with.")
    ]


def test_no_auth_session_logged_in(testclient, logged_user):
    """Logged users should not be able to access the password auth form if an authentication session has not been properly started."""
    res = testclient.get("/auth/password", status=302)
    assert res.location == "/"


def test_not_password_step(testclient, user):
    """Users reaching the password form while this is not the right auth step in their flow should be redirected there."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["email", "password"],
        ).serialize()

    res = testclient.get("/auth/password", status=302)
    assert res.location == "/auth/email"


def test_signin_and_out(testclient, user, caplog):
    with testclient.session_transaction() as session:
        assert not session.get("sessions")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert "user" == session["auth"]["user_name"]

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
    res = res.follow(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert [{"user": user.id, "last_login_datetime": mock.ANY}] == session.get(
            "sessions"
        )
        assert "auth" not in session

    res = testclient.get("/login", status=302)

    res = testclient.get("/logout")
    assert (
        "success",
        "You have been disconnected. See you next time Johnny",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Logout user",
    ) in caplog.record_tuples
    res = res.follow(status=302)
    res = res.follow(status=200)


def test_signin_wrong_password(testclient, user, caplog):
    with testclient.session_transaction() as session:
        assert not session.get("sessions")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = "incorrect horse"
    res = res.form.submit(status=200)
    assert ("error", "Login failed, please check your information") in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Failed password authentication for user",
    ) in caplog.record_tuples


def test_signin_password_substring(testclient, user):
    with testclient.session_transaction() as session:
        assert not session.get("sessions")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = "c"
    res = res.form.submit(status=200)
    assert ("error", "Login failed, please check your information") in res.flashes


def test_signin_bad_csrf(testclient, user):
    with testclient.session_transaction() as session:
        assert not session.get("sessions")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = ""
    res = res.form.submit(status=200)
    assert ("error", "Login failed, please check your information") in res.flashes


def test_signin_with_alternate_attribute(testclient, user):
    res = testclient.get("/login", status=200)

    res.form["login"] = "john@doe.test"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()
    res = res.follow(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert [{"user": user.id, "last_login_datetime": mock.ANY}] == session.get(
            "sessions"
        )


def test_password_page_without_signin_in_redirects_to_login_page(testclient, user):
    res = testclient.get("/auth/password", status=302)
    assert res.location == "/login"
    assert res.flashes == [
        ("warning", "Cannot remember the login you attempted to sign in with.")
    ]
