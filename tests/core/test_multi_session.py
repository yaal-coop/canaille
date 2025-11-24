import datetime

from flask import session

from canaille.app.session import USER_SESSION
from canaille.app.session import UserSession
from canaille.app.session import get_active_sessions
from canaille.app.session import login_user
from canaille.app.session import switch_to_session
from canaille.app.session import user_session_opened


def test_switch_to_session_with_redirect(
    testclient, logged_moderator, logged_user, backend
):
    """Test switching to an existing session when redirect-after-login is set."""
    with testclient.session_transaction() as sess:
        sess["redirect-after-login"] = "/profile/user"
        first_session = UserSession.deserialize(sess[USER_SESSION][0])
        assert first_session.user.id == logged_moderator.id

    res = testclient.get(f"/login/{logged_user.user_name}", status=302)
    assert res.location == "/profile/user"

    with testclient.session_transaction() as sess:
        first_session = UserSession.deserialize(sess[USER_SESSION][0])
        assert first_session.user.id == logged_user.id


def test_switch_to_session_via_form_with_redirect(
    testclient, logged_moderator, logged_user, backend
):
    """Test switching via login form when session exists and redirect is set."""
    with testclient.session_transaction() as sess:
        sess["redirect-after-login"] = "/profile/settings"
        first_session = UserSession.deserialize(sess[USER_SESSION][0])
        assert first_session.user.id == logged_moderator.id

    res = testclient.get("/login")
    res.form["login"] = logged_user.user_name
    res = res.form.submit()

    assert res.status_code == 302
    assert res.location == "/profile/settings"

    with testclient.session_transaction() as sess:
        first_session = UserSession.deserialize(sess[USER_SESSION][0])
        assert first_session.user.id == logged_user.id


def test_switch_to_session_without_redirect(
    testclient, logged_moderator, logged_user, backend
):
    """Test switching to an existing session redirects to profile."""
    res = testclient.get(f"/login/{logged_user.user_name}")
    assert res.status_code == 302
    assert "/profile" in res.location
    assert ("success", f"You switched to {logged_user.name} session.") in res.flashes


def test_switch_to_session_nonexistent_user(testclient, user, backend):
    """Test switch_to_session with non-existent user does nothing."""
    with testclient.app.test_request_context():
        session[USER_SESSION] = [
            UserSession(
                user=user,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
        ]

        switch_to_session("nonexistent-id")

        sessions = session.get(USER_SESSION, [])
        assert len(sessions) == 1
        first_session = UserSession.deserialize(sessions[0])
        assert first_session.user.id == user.id


def test_switch_to_session_empty_sessions(testclient):
    """Test switch_to_session with empty sessions list does nothing."""
    with testclient.app.test_request_context():
        session.clear()

        switch_to_session("any-id")

        assert USER_SESSION not in session


def test_user_session_opened_true(testclient, user, backend):
    """Test user_session_opened returns True when session exists."""
    with testclient.app.test_request_context():
        session[USER_SESSION] = [
            UserSession(
                user=user,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
            ).serialize(),
        ]

        result = user_session_opened(user.id)
        assert result is True


def test_user_session_opened_false(testclient, user, backend):
    """Test user_session_opened returns False when no session exists."""
    with testclient.app.test_request_context():
        session.clear()

        result = user_session_opened(user.id)
        assert result is False


def test_get_active_sessions_multiple(testclient, user, moderator, backend):
    """Test get_active_sessions returns all valid sessions."""
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

        sessions = get_active_sessions()
        assert len(sessions) == 2
        user_ids = [s.user.id for s in sessions]
        assert user.id in user_ids
        assert moderator.id in user_ids


def test_get_active_sessions_empty(testclient):
    """Test get_active_sessions returns empty list when no sessions."""
    with testclient.app.test_request_context():
        session.clear()

        sessions = get_active_sessions()
        assert sessions == []


def test_switch_to_session_via_form_without_redirect(
    testclient, logged_user, logged_moderator, backend
):
    """Test switching via login form without redirect-after-login."""
    res = testclient.get("/login")
    res.form["login"] = logged_user.user_name
    res = res.form.submit()

    assert res.status_code == 302
    assert "/profile" in res.location


def test_login_user_removes_duplicate_sessions(testclient, user, backend):
    """Test that login_user removes existing session for the same user."""
    with testclient.app.test_request_context():
        session[USER_SESSION] = [
            UserSession(
                user=user,
                last_login_datetime=datetime.datetime.now(datetime.timezone.utc),
                authentication_methods=["password"],
            ).serialize(),
        ]

        sessions = get_active_sessions()
        assert len(sessions) == 1
        assert sessions[0].authentication_methods == ["password"]

        login_user(user, remember=False)

        sessions = get_active_sessions()
        assert len(sessions) == 1
        first_session = sessions[0]
        assert first_session.user.id == user.id
        assert first_session.authentication_methods is None
