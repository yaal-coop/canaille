import datetime
import logging

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


def test_signin_and_out(testclient, user, caplog):
    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert "user" == session.get("attempt_login")

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()

    assert (
        "success",
        "Connection successful. Welcome Johnny",
    ) in res.flashes
    assert (
        "canaille",
        logging.SECURITY,
        "Succeed login attempt for user",
    ) in caplog.record_tuples
    res = res.follow(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert [user.id] == session.get("user_id")
        assert "attempt_login" not in session

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


def test_visitor_logout(testclient, user):
    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/logout")
    res = res.follow(status=302)
    res = res.follow(status=200)
    assert (
        "success",
        "You have been disconnected. See you next time user",
    ) not in res.flashes

    with testclient.session_transaction() as session:
        assert not session.get("user_id")


def test_signin_wrong_password(testclient, user, caplog):
    with testclient.session_transaction() as session:
        assert not session.get("user_id")

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
        "Failed login attempt for user",
    ) in caplog.record_tuples


def test_signin_password_substring(testclient, user):
    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)
    res.form["password"] = "c"
    res = res.form.submit(status=200)
    assert ("error", "Login failed, please check your information") in res.flashes


def test_signin_bad_csrf(testclient, user):
    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    res = testclient.get("/login", status=200)

    res.form["login"] = "John (johnny) Doe"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = ""
    res = res.form.submit(status=200)
    assert ("error", "Login failed, please check your information") in res.flashes


def test_signin_with_alternate_attribute(testclient, user):
    res = testclient.get("/login", status=200)

    res.form["login"] = "user"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()
    res = res.follow(status=302)
    res = res.follow(status=200)

    with testclient.session_transaction() as session:
        assert [user.id] == session.get("user_id")


def test_password_page_without_signin_in_redirects_to_login_page(testclient, user):
    res = testclient.get("/password", status=302)
    assert res.location == "/login"
    assert res.flashes == [
        ("warning", "Cannot remember the login you attempted to sign in with")
    ]


def test_password_page_already_logged_in(testclient, logged_user):
    res = testclient.get("/password", status=302)
    assert res.location == "/profile/user"


def test_wrong_login(testclient, user):
    testclient.app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] = True

    res = testclient.get("/login", status=200)
    res.form["login"] = "invalid"
    res = res.form.submit(status=302)
    res = res.follow(status=200)

    res.form["password"] = "incorrect horse"
    res = res.form.submit(status=200)
    res.mustcontain(no="The login &#39;invalid&#39; does not exist")

    testclient.app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] = False

    res = testclient.get("/login", status=200)
    res.form["login"] = "invalid"
    res = res.form.submit(status=200)
    res.mustcontain("The login &#39;invalid&#39; does not exist")


def test_signin_locked_account(testclient, user, backend):
    with testclient.session_transaction() as session:
        assert not session.get("user_id")

    user.lock_date = datetime.datetime.now(datetime.timezone.utc)
    backend.save(user)

    res = testclient.get("/login", status=200)
    res.form["login"] = "user"

    res = res.form.submit(status=302).follow(status=200)
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
