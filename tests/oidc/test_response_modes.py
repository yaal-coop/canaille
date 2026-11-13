from urllib.parse import parse_qs
from urllib.parse import urlsplit

from canaille.app import models


def authorize(testclient, client, **kwargs):
    params = dict(
        response_type="code",
        client_id=client.client_id,
        scope="openid profile",
        nonce="somenonce",
        state="somestate",
        redirect_uri=client.redirect_uris[0],
    )
    params.update(kwargs)
    return testclient.get("/oauth/authorize", params=params, expect_errors=True)


def form_post_params(res):
    """Return the action and the fields of a form post page."""
    form = res.forms["form-post"]
    return form.action, {name: field.value for name, field in form.field_order}


def test_code_flow_form_post(
    testclient, logged_user, trusted_client, backend, monkeypatch
):
    """Per OAuth 2.0 Form Post Response Mode §2, the parameters are sent with an HTML form."""
    monkeypatch.setitem(testclient.app.config["CANAILLE"], "JAVASCRIPT", True)

    res = authorize(testclient, trusted_client, response_mode="form_post")

    assert res.status_code == 200
    assert res.headers["Cache-Control"] == "no-store"
    assert res.pyquery("script").attr("src") == "/static/js/form-post.js"
    assert res.pyquery("noscript button[type=submit]")

    action, params = form_post_params(res)
    assert action == trusted_client.redirect_uris[0]
    assert params["state"] == "somestate"
    assert params["iss"] == "http://canaille.test"
    assert backend.get(models.AuthorizationCode, code=params["code"])


def test_form_post_without_javascript(testclient, logged_user, trusted_client):
    """Without JavaScript, the user submits the form with the button."""
    res = authorize(testclient, trusted_client, response_mode="form_post")

    assert res.status_code == 200
    assert not res.pyquery("script")
    assert res.pyquery("#form-post button[type=submit]")


def test_code_flow_fragment(testclient, logged_user, trusted_client):
    """Per OAuth 2.0 Multiple Response Types §2.1, clients choose the response mode."""
    res = authorize(testclient, trusted_client, response_mode="fragment")

    assert res.status_code == 303
    url = urlsplit(res.location)
    assert not url.query
    assert parse_qs(url.fragment)["code"]


def test_hybrid_flow_form_post(testclient, logged_user, trusted_client):
    res = authorize(
        testclient,
        trusted_client,
        response_type="code id_token",
        response_mode="form_post",
    )

    assert res.status_code == 200
    _, params = form_post_params(res)
    assert params["code"]
    assert params["id_token"]


def test_implicit_flow_form_post(testclient, logged_user, trusted_client):
    res = authorize(
        testclient,
        trusted_client,
        response_type="id_token token",
        response_mode="form_post",
    )

    assert res.status_code == 200
    _, params = form_post_params(res)
    assert params["access_token"]
    assert params["id_token"]


def test_form_post_login_required(testclient, user, trusted_client):
    """Errors raised after the user interactions use the requested response mode."""
    res = authorize(
        testclient, trusted_client, response_mode="form_post", prompt="none"
    )

    assert res.status_code == 200
    _, params = form_post_params(res)
    assert params["error"] == "login_required"


def test_query_refused_with_tokens(testclient, logged_user, trusted_client):
    """Per OAuth 2.0 Multiple Response Types §5, tokens are not sent in the query."""
    res = authorize(
        testclient,
        trusted_client,
        response_type="id_token token",
        response_mode="query",
    )

    assert res.status_code == 303
    url = urlsplit(res.location)
    assert not url.query
    assert parse_qs(url.fragment)["error"] == ["invalid_request"]


def test_unsupported_response_mode(testclient, logged_user, trusted_client):
    """Errors about the response mode use the default response mode of the flow."""
    res = authorize(testclient, trusted_client, response_mode="unknown")

    assert res.status_code == 303
    assert parse_qs(urlsplit(res.location).query)["error"] == ["invalid_request"]


def test_form_post_error(testclient, logged_user, client):
    """Errors use the requested response mode."""
    res = authorize(testclient, client, response_mode="form_post")
    res = res.form.submit(name="answer", value="deny", status=200)

    action, params = form_post_params(res)
    assert action == client.redirect_uris[0]
    assert params["error"] == "access_denied"
    assert params["state"] == "somestate"


def test_form_post_with_custom_scheme(testclient, logged_user, trusted_client, backend):
    """Form post needs an http or https redirect URI, so a form cannot run a script."""
    trusted_client.redirect_uris = ["com.example.app:/callback"]
    backend.save(trusted_client)

    res = authorize(testclient, trusted_client, response_mode="form_post")

    assert res.status_code == 400
    assert "form-post" not in res.forms
