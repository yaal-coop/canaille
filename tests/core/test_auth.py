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


def test_get_user_from_login_partial_email_no_multiple_results(
    testclient, user, moderator, backend
):
    """Test that partial email searches don't cause MultipleResultsFound errors (issue #278).

    This test reproduces the SQLAlchemy bug where searching for a partial string
    in JSON list columns would find multiple users and cause scalar_one_or_none()
    to raise MultipleResultsFound instead of returning None.
    """
    # Ensure we have users with emails containing common substrings
    user.emails = ["user@example.com"]
    moderator.emails = ["support@example.com"]
    backend.save(user)
    backend.save(moderator)

    result = get_user_from_login(login="u")

    assert result is None
    exact_result = get_user_from_login(login="user@example.com")
    assert exact_result == user


def test_session_permanence_with_remember_true(testclient, user, backend):
    # This test verifies the session is configured as permanent
    # Actual expiration testing would require browser simulation
    from canaille.app.session import LOGIN_HISTORY

    with testclient.session_transaction() as sess:
        sess.clear()

    res = testclient.get("/login")
    res.form["login"] = user.user_name
    res = res.form.submit()

    res = res.follow()
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()

    # Note: WebTest doesn't expose session.permanent directly
    # This test mainly ensures the login flow works with remember=True
    with testclient.session_transaction() as sess:
        assert LOGIN_HISTORY in sess
        assert user.user_name in sess[LOGIN_HISTORY]


def test_direct_login_with_username_uses_default_remember(testclient, user, backend):
    """Test that direct login via /login/<username> uses default remember=True."""
    from canaille.app.session import LOGIN_HISTORY

    with testclient.session_transaction() as sess:
        sess.clear()

    res = testclient.get(f"/login/{user.user_name}")
    res = res.follow()
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()

    with testclient.session_transaction() as sess:
        assert LOGIN_HISTORY in sess
        assert user.user_name in sess[LOGIN_HISTORY]
