from authlib.oidc.core.grants.util import generate_id_token

from canaille.oidc.oauth import generate_user_info
from canaille.oidc.oauth import get_jwt_config


def test_end_session(testclient, backend, logged_user, client, id_token):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://mydomain.test/disconnected"
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
        assert not sess.get("user_id")

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_end_session_no_client_id(testclient, backend, logged_user, client, id_token):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://mydomain.test/disconnected"
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
        assert not sess.get("user_id")

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
        assert not sess.get("user_id")

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_bad_redirect_uri_no_redirect(
    testclient, backend, logged_user, client, id_token
):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://mydomain.test/invalid-uri"
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
        assert not sess.get("user_id")

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_no_client_hint_no_redirect(testclient, backend, logged_user, client, id_token):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://mydomain.test/disconnected"
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
        assert not sess.get("user_id")

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_end_session_invalid_client_id(testclient, backend, logged_user, client):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://mydomain.test/disconnected"
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
        assert not sess.get("user_id")

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_client_hint_invalid(testclient, backend, logged_user, client):
    id_token = generate_id_token(
        {},
        generate_user_info(logged_user, client.scope),
        aud="invalid-client-id",
        **get_jwt_config(None),
    )

    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://mydomain.test/disconnected"
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
        assert not sess.get("user_id")

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_no_jwt_logout(testclient, backend, logged_user, client):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://mydomain.test/disconnected"
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
        assert not sess.get("user_id")

    assert res.location == f"{post_logout_redirect_url}?state=foobar"

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_no_jwt_no_logout(testclient, backend, logged_user, client):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://mydomain.test/disconnected"
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
        assert sess.get("user_id")

    assert res.location == "/"

    testclient.get(f"/profile/{logged_user.user_name}", status=200)


def test_jwt_not_issued_here(testclient, backend, logged_user, client, id_token):
    testclient.app.config["CANAILLE_OIDC"]["JWT"]["ISS"] = "https://foobar.test"

    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://mydomain.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": id_token,
            "logout_hint": logged_user.user_name,
            "client_id": client.client_id,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=200,
    )

    assert res.json == {
        "message": "id_token_hint has not been issued here",
        "status": "error",
    }


def test_client_hint_mismatch(testclient, backend, logged_user, client):
    id_token = generate_id_token(
        {},
        generate_user_info(logged_user, client.scope),
        aud="another_client_id",
        **get_jwt_config(None),
    )

    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://mydomain.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": id_token,
            "logout_hint": logged_user.user_name,
            "client_id": client.client_id,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
        status=200,
    )

    assert res.json == {
        "message": "id_token audience and client_id don't match",
        "status": "error",
    }


def test_end_session_bad_id_token(testclient, backend, logged_user, client, id_token):
    post_logout_redirect_url = "https://mydomain.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": "invalid",
            "logout_hint": logged_user.user_name,
            "client_id": client.client_id,
            "post_logout_redirect_uri": post_logout_redirect_url,
            "state": "foobar",
        },
    )

    assert res.json == {"status": "error", "message": "Invalid input segments length: "}


def test_bad_user_id_token_mismatch(testclient, backend, logged_user, client, admin):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    id_token = generate_id_token(
        {},
        generate_user_info(admin, client.scope),
        aud=client.client_id,
        **get_jwt_config(None),
    )

    post_logout_redirect_url = "https://mydomain.test/disconnected"
    res = testclient.get(
        "/oauth/end_session",
        params={
            "id_token_hint": id_token,
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
        assert not sess.get("user_id")

    assert res.location == f"{post_logout_redirect_url}?state=foobar"

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_bad_user_hint(testclient, backend, logged_user, client, id_token, admin):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://mydomain.test/disconnected"
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
        assert not sess.get("user_id")

    assert res.location == f"{post_logout_redirect_url}?state=foobar"

    testclient.get(f"/profile/{logged_user.user_name}", status=403)


def test_no_jwt_bad_csrf(testclient, backend, logged_user, client):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://mydomain.test/disconnected"
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
    post_logout_redirect_url = "https://mydomain.test/disconnected"
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

    assert res.location == "/"


def test_end_session_no_state(testclient, backend, logged_user, client, id_token):
    testclient.get(f"/profile/{logged_user.user_name}", status=200)

    post_logout_redirect_url = "https://mydomain.test/disconnected"
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
        assert not sess.get("user_id")

    testclient.get(f"/profile/{logged_user.user_name}", status=403)
