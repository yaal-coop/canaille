import datetime

from flask import g
from flask import session

from canaille.app.session import USER_SESSION
from canaille.app.session import UserSession
from canaille.app.session import logout_all_users
from canaille.app.session import logout_user


def test_visitor_logout(testclient, user):
    """Test that logging out without an active session works gracefully."""
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


def test_logout_specific_user_not_current(testclient, user, moderator, admin, backend):
    """Test logout of a specific user that is not the current session."""
    with testclient.session_transaction() as sess:
        sess[USER_SESSION] = [
            UserSession(
                user=user,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
            UserSession(
                user=moderator,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
            UserSession(
                user=admin,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
        ]

    res = testclient.get(f"/logout/{moderator.user_name}")
    assert res.status_code == 302
    assert (
        "success",
        f"You have been disconnected from {moderator.name} account.",
    ) in res.flashes

    with testclient.session_transaction() as sess:
        sessions = sess.get(USER_SESSION, [])
        assert len(sessions) == 2
        user_ids = [UserSession.deserialize(s).user.id for s in sessions]
        assert moderator.id not in user_ids
        assert user.id in user_ids
        assert admin.id in user_ids


def test_logout_first_session_specific_user(testclient, user, moderator, backend):
    """Test logout of the first session (current user) via username."""
    with testclient.session_transaction() as sess:
        sess[USER_SESSION] = [
            UserSession(
                user=user,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
            UserSession(
                user=moderator,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
        ]

    res = testclient.get(f"/logout/{user.user_name}")
    assert res.status_code == 302
    assert (
        "success",
        f"You have been disconnected from {user.name} account.",
    ) in res.flashes

    with testclient.session_transaction() as sess:
        sessions = sess.get(USER_SESSION, [])
        assert len(sessions) == 1
        first_session = UserSession.deserialize(sessions[0])
        assert first_session.user.id == moderator.id


def test_logout_user_function_with_user_id(testclient, user, moderator, backend):
    """Test logout_user function with specific user_id."""
    with testclient.app.test_request_context():
        session[USER_SESSION] = [
            UserSession(
                user=user,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
            UserSession(
                user=moderator,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
        ]

        result = logout_user(moderator.id)
        assert result is True

        sessions = session.get(USER_SESSION, [])
        assert len(sessions) == 1


def test_logout_user_function_no_sessions(testclient):
    """Test logout_user returns False when no sessions exist."""
    with testclient.app.test_request_context():
        session.clear()

        result = logout_user()
        assert result is False


def test_logout_user_function_invalid_user_id(testclient, user, backend):
    """Test logout_user returns False for non-existent user_id."""
    with testclient.app.test_request_context():
        session[USER_SESSION] = [
            UserSession(
                user=user,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
        ]

        result = logout_user("nonexistent-id")
        assert result is False

        sessions = session.get(USER_SESSION, [])
        assert len(sessions) == 1


def test_logout_last_user(testclient, user, backend):
    """Test logout_user removes USER_SESSION when logging out last session."""
    with testclient.app.test_request_context():
        session[USER_SESSION] = [
            UserSession(
                user=user,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
        ]
        g.session = UserSession.deserialize(session[USER_SESSION][0])

        result = logout_user()
        assert result is True
        assert USER_SESSION not in session


def test_logout_all_users_function(testclient, user, moderator, backend):
    """Test logout_all_users clears all sessions."""
    with testclient.app.test_request_context():
        session[USER_SESSION] = [
            UserSession(
                user=user,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
            UserSession(
                user=moderator,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
        ]

        logout_all_users()

        assert USER_SESSION not in session


def test_logout_nonexistent_user_via_url(testclient, user, backend):
    """Test logout via URL with non-existent username."""
    with testclient.session_transaction() as sess:
        sess[USER_SESSION] = [
            UserSession(
                user=user,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
        ]

    res = testclient.get("/logout/nonexistent")
    assert res.status_code == 302
    assert ("error", "The session could not be closed.") in res.flashes

    with testclient.session_transaction() as sess:
        sessions = sess.get(USER_SESSION, [])
        assert len(sessions) == 1


def test_logout_user_exception_handling(testclient):
    """Test logout_user handles exceptions when session data is inconsistent."""
    with testclient.app.test_request_context():
        session[USER_SESSION] = []

        result = logout_user()
        assert result is False


def test_logout_user_with_corrupted_session(testclient, user, moderator, backend):
    """Test logout with corrupted session in the list."""
    with testclient.app.test_request_context():
        session[USER_SESSION] = [
            UserSession(
                user=user,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
            {"user": "nonexistent-id", "last_login_datetime": "2024-01-01T00:00:00"},
            UserSession(
                user=moderator,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
        ]

        result = logout_user(moderator.id)
        assert result is True

        sessions = session.get(USER_SESSION, [])
        assert len(sessions) == 2


def test_logout_all_users_without_g_session(testclient, user, backend):
    """Test logout_all_users when g.session doesn't exist."""
    with testclient.app.test_request_context():
        session[USER_SESSION] = [
            UserSession(
                user=user,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
        ]

        logout_all_users()

        assert USER_SESSION not in session
