from flask import g
from flask import session as flask_session
from itsdangerous.url_safe import URLSafeSerializer

from canaille.app import models
from canaille.app.session import LOGIN_HISTORY
from canaille.app.session import LOGIN_HISTORY_COOKIE
from canaille.app.session import _get_login_history_from_cookie
from canaille.app.session import add_to_login_history
from canaille.app.session import get_login_history
from canaille.app.session import login_user
from canaille.app.session import remove_from_login_history


def test_add_to_login_history_empty_identifier(testclient):
    """Test that empty identifiers are ignored."""
    with testclient.session_transaction() as sess:
        sess.clear()

    add_to_login_history("")
    add_to_login_history(None)

    with testclient.session_transaction() as sess:
        assert LOGIN_HISTORY not in sess


def test_add_to_login_history_single_user(testclient):
    """Test adding a single user to past users list."""
    with testclient.session_transaction() as sess:
        sess.clear()

    with testclient.app.test_request_context():
        flask_session.clear()
        add_to_login_history("testuser")
        assert flask_session[LOGIN_HISTORY] == ["testuser"]


def test_add_to_login_history_multiple_users(testclient):
    """Test adding multiple users maintains MRU order."""
    with testclient.app.test_request_context():
        flask_session.clear()

        add_to_login_history("user1")
        add_to_login_history("user2")
        add_to_login_history("user3")

        assert g.login_history_needs_update == ["user3", "user2", "user1"]


def test_add_to_login_history_duplicate_moves_to_front(testclient):
    """Test that re-adding an existing user moves it to front."""
    with testclient.app.test_request_context():
        add_to_login_history("user1")
        add_to_login_history("user2")
        add_to_login_history("user3")
        add_to_login_history("user1")

        assert g.login_history_needs_update == ["user1", "user3", "user2"]


def test_add_to_login_history_max_limit(testclient):
    """Test that past users list is capped at MAX_LOGIN_HISTORY."""
    with testclient.app.test_request_context():
        for i in range(8):
            add_to_login_history(f"user{i}")

        assert len(g.login_history_needs_update) == 6
        assert g.login_history_needs_update == [
            "user7",
            "user6",
            "user5",
            "user4",
            "user3",
            "user2",
        ]


def test_get_login_history_empty(testclient):
    """Test get_login_history with empty session."""
    with testclient.session_transaction() as sess:
        sess.clear()

    login_history = get_login_history()
    assert login_history == []


def test_get_login_history_with_valid_user(testclient, user):
    """Test get_login_history retrieves valid user objects."""
    with testclient.session_transaction() as sess:
        sess.clear()

    add_to_login_history(user.user_name)
    login_history = get_login_history()

    assert len(login_history) == 1
    assert login_history[0].user_name == user.user_name


def test_get_login_history_filters_deleted_users(testclient, user):
    """Test get_login_history filters out deleted/invalid users."""
    with testclient.app.test_request_context():
        add_to_login_history(user.user_name)
        add_to_login_history("nonexistent_user")

        login_history = get_login_history()

        assert len(login_history) == 1
        assert login_history[0].user_name == user.user_name


def test_login_page_without_login_history(testclient):
    """Test login page renders normally without past users."""
    with testclient.session_transaction() as sess:
        sess.clear()

    res = testclient.get("/login")
    assert res.status_code == 200
    assert "Choose an account" not in res.text
    assert "Use another account" not in res.text


def test_login_page_with_login_history(testclient, user):
    """Test login page displays past users when available."""
    with testclient.session_transaction() as sess:
        sess.clear()
        sess[LOGIN_HISTORY] = [user.user_name]

    res = testclient.get("/login")
    assert res.status_code == 200
    assert "Choose an account" in res.text
    assert "Use another account" in res.text
    assert user.name in res.text


def test_login_with_username_valid_user(testclient, user):
    """Test direct login with valid username redirects to auth."""
    res = testclient.get(f"/login/{user.user_name}")
    assert res.status_code == 302
    assert "/auth/password" in res.location


def test_login_with_username_invalid_user(testclient):
    """Test direct login with invalid username continues to auth (no user enumeration)."""
    res = testclient.get("/login/nonexistent")
    assert res.status_code == 302
    assert "/auth/password" in res.location


def test_login_with_username_invalid_user_auth_fails(testclient):
    """Test that authentication fails for invalid user without revealing it doesn't exist.

    Note: Currently, the auth templates display the username, which could allow
    user enumeration. However, this follows the existing Canaille UX pattern
    and the main protection is that we don't immediately reject invalid users.
    """
    res = testclient.get("/login/nonexistent")
    res = res.follow()
    assert res.status_code == 200
    assert res.template == "core/auth/password.html"

    res.form["password"] = "any password"
    res = res.form.submit()

    assert res.status_code == 200
    assert "Login failed" in res.text or "Authentication failed" in res.text
    assert "User not found" not in res.text


def test_login_success_adds_to_login_history(testclient, user, backend):
    """Test successful login adds user to past users list."""
    with testclient.session_transaction() as sess:
        sess.clear()

    res = testclient.get("/login")
    res.form["login"] = user.user_name
    res = res.form.submit()

    res = res.follow()
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()

    with testclient.session_transaction() as sess:
        assert LOGIN_HISTORY in sess
        assert user.user_name in sess[LOGIN_HISTORY]


def test_logout_preserves_login_history(testclient, user, backend):
    """Test logout preserves login history in cookie."""
    with testclient.session_transaction() as sess:
        sess.clear()

    res = testclient.get("/login")
    res.form["login"] = user.user_name
    res = res.form.submit()
    res = res.follow()
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()

    testclient.get("/logout")

    res = testclient.get("/login")
    assert "Choose an account" in res.text
    assert user.name in res.text


def test_login_history_card_links(testclient, user):
    """Test that past user cards have correct links."""
    with testclient.session_transaction() as sess:
        sess.clear()
        sess[LOGIN_HISTORY] = [user.user_name]

    res = testclient.get("/login")
    assert res.status_code == 200

    expected_link = f"/login/{user.user_name}"
    assert f'href="{expected_link}"' in res.text


def test_get_login_history_lookup_consistency(testclient, user):
    """Test get_login_history uses consistent lookup with get_user_from_login."""
    with testclient.session_transaction() as sess:
        sess.clear()

    add_to_login_history(user.user_name)

    login_history = get_login_history()
    assert len(login_history) == 1
    assert login_history[0] == user


def test_auth_template_displays_user_name_for_known_users(testclient, user):
    """Test that auth templates display user name only for users in LOGIN_HISTORY."""
    with testclient.session_transaction() as sess:
        sess[LOGIN_HISTORY] = [user.user_name]

    res = testclient.get(f"/login/{user.user_name}")
    res = res.follow()
    assert res.status_code == 200
    assert res.template == "core/auth/password.html"

    assert user.name in res.text
    assert user.user_name in res.text


def test_auth_template_displays_identifier_for_unknown_users(testclient, user):
    """Test that auth templates display only identifier for unknown users."""
    with testclient.session_transaction() as sess:
        sess.clear()

    res = testclient.get(f"/login/{user.user_name}")
    res = res.follow()
    assert res.status_code == 200
    assert res.template == "core/auth/password.html"

    assert user.name not in res.text
    assert user.user_name in res.text


def test_impersonated_users_not_in_login_history(testclient, logged_admin, user):
    """Test that impersonated users do not appear in login_history list."""
    with testclient.session_transaction() as sess:
        sess.pop(LOGIN_HISTORY, None)

    testclient.get(f"/impersonate/{user.user_name}", status=302)

    with testclient.session_transaction() as sess:
        login_history = sess.get(LOGIN_HISTORY, [])
        assert user.user_name not in login_history


def test_login_user_remember_parameter(testclient, user):
    """Test that login_user respects the remember parameter."""
    with testclient.app.test_request_context():
        flask_session.clear()
        login_user(user)
        assert flask_session.get(LOGIN_HISTORY, []) == [user.user_name]

        flask_session.clear()
        login_user(user, remember=False)
        assert LOGIN_HISTORY not in flask_session


def test_forget(testclient, user):
    """Test the remove past user route."""
    res = testclient.get(f"/forget/{user.user_name}")
    assert res.status_code == 302
    assert res.location.endswith("/login")


def test_forget_nonexistent_user(testclient):
    """Test removing a non-existent user returns redirect (security)."""
    with testclient.session_transaction() as sess:
        sess[LOGIN_HISTORY] = ["existing_user"]

    res = testclient.get("/forget/nonexistent")
    assert res.status_code == 302
    assert res.location.endswith("/login")

    with testclient.session_transaction() as sess:
        login_history = sess.get(LOGIN_HISTORY, [])
        assert login_history == ["existing_user"]


def test_remove_from_login_history_function(testclient):
    """Test the remove_from_login_history function directly."""
    with testclient.app.test_request_context():
        add_to_login_history("user1")
        add_to_login_history("user2")
        add_to_login_history("user3")

        remove_from_login_history("user2")
        assert g.login_history_needs_update == ["user3", "user1"]

        g.login_history_needs_update = ["user1"]
        remove_from_login_history("user1")
        assert g.login_history_needs_update == []

        g.login_history_needs_update = ["user1"]
        remove_from_login_history("nonexistent")
        assert g.login_history_needs_update == ["user1"]

        g.login_history_needs_update = ["user1"]
        remove_from_login_history("")
        assert g.login_history_needs_update == ["user1"]


def test_remember_me_checkbox_default_true(testclient):
    """Test that remember checkbox is checked by default."""
    res = testclient.get("/login")
    assert res.status_code == 200

    assert 'name="remember"' in res.text
    assert "checked" in res.text


def test_remember_me_false_no_login_history(testclient, user, backend):
    """Test that remember=False doesn't add user to login history."""
    with testclient.session_transaction() as sess:
        sess.clear()

    res = testclient.get("/login")
    res.form["login"] = user.user_name
    res.form["remember"].checked = False
    res = res.form.submit()

    res = res.follow()
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()

    testclient.get("/logout")

    res = testclient.get("/login")
    assert "Choose an account" not in res.text


def test_remember_me_true_adds_to_login_history(testclient, user, backend):
    """Test that remember=True adds user to login history."""
    with testclient.session_transaction() as sess:
        sess.clear()

    res = testclient.get("/login")
    res.form["login"] = user.user_name
    res = res.form.submit()

    res = res.follow()
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()

    testclient.get("/logout")

    res = testclient.get("/login")
    assert "Choose an account" in res.text
    assert user.name in res.text


def test_remember_me_false_preserves_existing_history(testclient, user, backend):
    """Test that remember=False doesn't remove existing login history."""
    res = testclient.get("/login")
    res.form["login"] = user.user_name
    res = res.form.submit()
    res = res.follow()
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()
    testclient.get("/logout")

    res = testclient.get("/login")
    assert "Choose an account" in res.text

    res = testclient.get("/login")
    res.form["login"] = user.user_name
    res.form["remember"].checked = False
    res = res.form.submit()
    res = res.follow()
    res.form["password"] = "correct horse battery staple"
    res = res.form.submit()
    testclient.get("/logout")

    res = testclient.get("/login")
    assert "Choose an account" in res.text
    assert user.name in res.text


def test_user_without_password_redirects_to_firstlogin_via_direct_url(
    testclient, backend
):
    """Test that direct login URL for user without password redirects to firstlogin."""
    temp_user = models.User(
        formatted_name="Temp User",
        family_name="Temp",
        user_name="tempuser",
        emails=["temp@example.com"],
    )
    backend.save(temp_user)

    res = testclient.get("/login/tempuser")

    assert res.status_code == 302
    assert res.location == "/firstlogin/tempuser"

    backend.delete(temp_user)


def test_get_login_history_from_cookie_no_cookie(testclient):
    """Test _get_login_history_from_cookie with no cookie present."""
    with testclient.app.test_request_context():
        result = _get_login_history_from_cookie()
        assert result == []


def test_get_login_history_from_cookie_invalid_data_type(testclient):
    """Test _get_login_history_from_cookie with non-list data in cookie."""
    with testclient.app.test_request_context():
        serializer = URLSafeSerializer(testclient.app.secret_key)
        invalid_data = serializer.dumps("not_a_list")

        with testclient.app.test_request_context(
            environ_base={"HTTP_COOKIE": f"{LOGIN_HISTORY_COOKIE}={invalid_data}"}
        ):
            result = _get_login_history_from_cookie()
            assert result == []


def test_get_login_history_from_cookie_corrupted_cookie(testclient):
    """Test _get_login_history_from_cookie with corrupted cookie."""
    with testclient.app.test_request_context(
        environ_base={"HTTP_COOKIE": f"{LOGIN_HISTORY_COOKIE}=corrupted_data"}
    ):
        result = _get_login_history_from_cookie()
        assert result == []
