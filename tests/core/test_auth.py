import datetime

from canaille.core.auth import AuthenticationSession
from canaille.core.auth import get_user_from_login


def test_user_get_user_from_login(testclient, user):
    """Check that 'get_user_from_login' gets users according to LOGIN_ATTRIBUTES."""
    assert get_user_from_login(login="invalid") is None
    assert get_user_from_login(login="user") == user
    assert get_user_from_login(login="john@doe.test") == user
    assert get_user_from_login(login="555-000-000") is None


def test_user_get_user_from_login_dict(testclient, user):
    """Check that 'get_user_from_login' gets users according to LOGIN_ATTRIBUTES when it is a dict."""
    testclient.app.config["CANAILLE"]["LOGIN_ATTRIBUTES"] = {
        "user_name": "{{ login | replace('@doe.test', '') }}",
        "emails": "{{ login }}",
    }
    assert get_user_from_login(login="invalid") is None
    assert get_user_from_login(login="user") == user
    assert get_user_from_login(login="john@doe.test") == user
    assert get_user_from_login(login="user@doe.test") == user


def test_visitor_logout(testclient, user):
    with testclient.session_transaction() as session:
        assert not session.get("sessions")

    res = testclient.get("/logout")
    res = res.follow(status=302)
    res = res.follow(status=200)
    assert (
        "success",
        "You have been disconnected. See you next time user",
    ) not in res.flashes

    with testclient.session_transaction() as session:
        assert not session.get("sessions")


def test_wrong_login(testclient, user):
    testclient.app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] = True

    res = testclient.get("/login", status=200)
    res.form["login"] = "invalid"
    res = res.form.submit(status=302)
    res = res.follow(status=200)
    assert res.template == "core/auth/password.html"

    testclient.app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] = False

    res = testclient.get("/login", status=200)
    res.form["login"] = "invalid"
    res = res.form.submit(status=200)
    res.mustcontain("The login 'invalid' does not exist")


def test_signin_locked_account(testclient, user, backend):
    with testclient.session_transaction() as session:
        assert not session.get("sessions")

    user.lock_date = datetime.datetime.now(datetime.timezone.utc)
    backend.save(user)

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"

    res = res.form.submit(status=302)
    res = res.follow(status=200)
    res.form["password"] = "correct horse battery staple"

    res = res.form.submit()
    res.mustcontain("Your account has been locked.")

    user.lock_date = None
    backend.save(user)


def test_login_placeholder(testclient):
    """Check that the login form placeholders display values according to the 'LOGIN_ATTRIBUTES' configuration parameter."""
    testclient.app.config["CANAILLE"]["LOGIN_ATTRIBUTES"] = ["user_name"]
    placeholder = testclient.get("/login").form["login"].attrs["placeholder"]
    assert placeholder == "jdoe"

    testclient.app.config["CANAILLE"]["LOGIN_ATTRIBUTES"] = ["formatted_name"]
    placeholder = testclient.get("/login").form["login"].attrs["placeholder"]
    assert placeholder == "John Doe"

    testclient.app.config["CANAILLE"]["LOGIN_ATTRIBUTES"] = ["emails"]
    placeholder = testclient.get("/login").form["login"].attrs["placeholder"]
    assert placeholder == "john.doe@example.com"

    testclient.app.config["CANAILLE"]["LOGIN_ATTRIBUTES"] = ["user_name", "emails"]
    placeholder = testclient.get("/login").form["login"].attrs["placeholder"]
    assert placeholder == "jdoe or john.doe@example.com"


def test_bad_authentication_step(testclient, user):
    """Handle corrupted authentication sessions."""
    with testclient.session_transaction() as session:
        session["auth"] = AuthenticationSession(
            user_name="user",
            remaining=["password", "invalid"],
        ).serialize()

    res = testclient.get("/auth/password", status=200)
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit(status=302)

    assert (
        "error",
        "An error happened during your authentication process. Please try again.",
    ) in res.flashes
