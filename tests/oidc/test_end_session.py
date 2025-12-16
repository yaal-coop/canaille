from authlib.oidc.core import UserInfo
from authlib.oidc.core.grants.util import generate_id_token
from joserfc.jwk import RSAKey

from canaille.oidc.provider import get_jwt_config
from canaille.oidc.userinfo import generate_user_claims


def test_end_session(testclient, backend, logged_user, client, id_token):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://client.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": id_token,
            "logout_hint": logged_user.user_name,
            "client_id": client.client_id,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=302,
    )

    assert res.location == f"{post_logout_redirect_url}?state=foobar"

    with testclient.session_transaction() as sess:
        assert not sess.get("sessions")

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_end_session_no_client_id(testclient, backend, logged_user, client, id_token):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://client.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": id_token,
            "logout_hint": logged_user.user_name,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=302,
    )

    assert res.location == f"{post_logout_redirect_url}?state=foobar"

    with testclient.session_transaction() as sess:
        assert not sess.get("sessions")

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_no_redirect_uri_no_redirect(
    testclient, backend, logged_user, client, id_token
):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": id_token,
            "logout_hint": logged_user.user_name,
            "client_id": client.client_id,
            "state": "foobar",
        },
        status=302,
    )

    assert res.location == "/"

    with testclient.session_transaction() as sess:
        assert not sess.get("sessions")

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_bad_redirect_uri_no_redirect(
    testclient, backend, logged_user, client, id_token
):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://client.test/invalid-uri"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": id_token,
            "logout_hint": logged_user.user_name,
            "client_id": client.client_id,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=302,
    )

    assert res.location == "/"

    with testclient.session_transaction() as sess:
        assert not sess.get("sessions")

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_no_id_token_hint_no_redirect(
    testclient, backend, logged_user, client, id_token
):
    """At the Logout Endpoint, the OP SHOULD ask the End-User whether to log out of the OP as well.

    Furthermore, the OP MUST ask the End-User this question if an id_token_hint was not provided or
    if the supplied ID Token does not belong to the current OP session with the RP and/or currently
    logged in End-User. If the End-User says "yes", then the OP MUST log out the End-User.
    """
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://client.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "logout_hint": logged_user.user_name,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=200,
    )
    res = res.form.submit(name="answer", value="logout", status=302)
    res = res.follow(status=302)

    assert res.location == "/"

    with testclient.session_transaction() as sess:
        assert not sess.get("sessions")

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_end_session_invalid_client_id(testclient, backend, logged_user, client):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://client.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "logout_hint": logged_user.user_name,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "client_id": "invalid_client_id",
            "state": "foobar",
        },
        status=200,
    )

    res = res.form.submit(name="answer", value="logout", status=302)
    res = res.follow(status=302)

    assert res.location == "/"

    with testclient.session_transaction() as sess:
        assert not sess.get("sessions")

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_client_hint_invalid(testclient, backend, logged_user, client):
    id_token = generate_id_token(
        {},
        UserInfo(generate_user_claims(logged_user)).filter(client.scope),
        aud="invalid-client-id",
        **get_jwt_config(None),
    )

    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://client.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": id_token,
            "logout_hint": logged_user.user_name,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=302,
    )

    assert res.location == "/"

    with testclient.session_transaction() as sess:
        assert not sess.get("sessions")

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_no_jwt_untrusted_domain_logout_no_redirection(
    testclient, backend, logged_user, client
):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://client.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "logout_hint": logged_user.user_name,
            "client_id": client.client_id,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=200,
    )

    res = res.form.submit(name="answer", value="logout", status=302)
    res = res.follow(status=302)

    with testclient.session_transaction() as sess:
        assert not sess.get("sessions")

    assert res.location == "/"

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_no_jwt_trusted_domain_logout_redirection(
    testclient, backend, logged_user, trusted_client
):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://client.trusted.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "logout_hint": logged_user.user_name,
            "client_id": trusted_client.client_id,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=200,
    )

    res = res.form.submit(name="answer", value="logout", status=302)
    res = res.follow(status=302)

    with testclient.session_transaction() as sess:
        assert not sess.get("sessions")

    assert res.location == f"{post_logout_redirect_url}?state=foobar"

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_no_jwt_no_logout(testclient, backend, logged_user, client):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://client.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "logout_hint": logged_user.user_name,
            "client_id": client.client_id,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=200,
    )

    res = res.form.submit(name="answer", value="stay", status=302)

    with testclient.session_transaction() as sess:
        assert sess.get("sessions")

    assert res.location == "/"

    testclient.get(f"/profile/{logged_user.user_name}", status=200)


def test_jwt_not_issued_here(testclient, backend, logged_user, client, user):
    jwt_config = get_jwt_config(None)
    jwt_config["key"] = RSAKey.generate_key(2048, auto_kid=True).as_bytes()
    foreign_id_token = generate_id_token(
        {},
        UserInfo(generate_user_claims(user)).filter(client.scope),
        aud=client.client_id,
        **jwt_config,
    )

    post_logout_redirect_url = "https://client.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": foreign_id_token,
            "logout_hint": logged_user.user_name,
            "client_id": client.client_id,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=400,
    )

    assert res.json == {
        "error": "invalid_request",
    }


def test_client_hint_mismatch(testclient, backend, logged_user, client):
    id_token = generate_id_token(
        {},
        UserInfo(generate_user_claims(logged_user)).filter(client.scope),
        aud="another_client_id",
        **get_jwt_config(None),
    )

    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://client.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": id_token,
            "logout_hint": logged_user.user_name,
            "client_id": client.client_id,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=400,
    )

    assert res.json == {
        "error": "invalid_request",
        "error_description": "'client_id' does not match 'aud' claim",
    }


def test_end_session_bad_id_token(testclient, backend, logged_user, client, id_token):
    post_logout_redirect_url = "https://client.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": "invalid",
            "logout_hint": logged_user.user_name,
            "client_id": client.client_id,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=400,
    )

    assert res.json == {
        "error": "invalid_request",
    }


def test_bad_user_hint(testclient, backend, logged_user, client, id_token, admin):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://client.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": id_token,
            "logout_hint": admin.user_name,
            "client_id": client.client_id,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=200,
    )

    res = res.form.submit(name="answer", value="logout", status=302)
    res = res.follow(status=302)

    with testclient.session_transaction() as sess:
        assert not sess.get("sessions")

    assert res.location == f"{post_logout_redirect_url}?state=foobar"

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_no_jwt_bad_csrf(testclient, backend, logged_user, client):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://client.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "logout_hint": logged_user.user_name,
            "client_id": client.client_id,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=200,
    )

    form = res.form
    form["csrf_token"] = "foobar"
    res = form.submit(name="answer", value="logout", status=400, expect_errors=True)


def test_end_session_already_disconnected(testclient, backend, user, client, id_token):
    post_logout_redirect_url = "https://client.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": id_token,
            "logout_hint": user.user_name,
            "client_id": client.client_id,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=302,
    )

    assert res.location == f"{post_logout_redirect_url}?state=foobar"


def test_end_session_no_state(testclient, backend, logged_user, client, id_token):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://client.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": id_token,
            "logout_hint": logged_user.user_name,
            "client_id": client.client_id,
            "post_logout_redirect_uri": post_logout_redirect_url,
        },
        status=302,
    )

    assert res.location == post_logout_redirect_url

    with testclient.session_transaction() as sess:
        assert not sess.get("sessions")

    testclient.get(f"/profile/{logged_user.user_name}", status=403)
