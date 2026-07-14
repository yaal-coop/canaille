def test_redirect_to_server_name(testclient):
    """Requests with wrong host are redirected to SERVER_NAME."""
    testclient.app.config["SERVER_NAME"] = "canaille.test"

    res = testclient.get("/login", headers={"Host": "localhost"}, status=302)
    assert res.location == "http://canaille.test/login"


def test_redirect_to_server_name_preserves_query_string(testclient):
    """Redirect preserves query string parameters."""
    testclient.app.config["SERVER_NAME"] = "canaille.test"

    res = testclient.get(
        "/login?next=/profile", headers={"Host": "localhost"}, status=302
    )
    assert res.location == "http://canaille.test/login?next=/profile"


def test_no_redirect_when_host_matches(testclient):
    """No redirect when host already matches SERVER_NAME."""
    testclient.app.config["SERVER_NAME"] = "canaille.test"

    res = testclient.get("/login", headers={"Host": "canaille.test"}, status=200)
    assert res.status_int == 200


def test_no_redirect_without_server_name(testclient):
    """No redirect when SERVER_NAME is not configured."""
    testclient.app.config["SERVER_NAME"] = None

    res = testclient.get("/login", status=200)
    assert res.status_int == 200


def test_redirect_to_server_name_neutralizes_crlf_in_path(testclient):
    """A CRLF injection attempt in the path is neutralized instead of raising.

    Without iri_to_uri the reconstructed URL keeps the raw newline characters,
    which Werkzeug refuses to put in the Location header, resulting in a 500.
    """
    testclient.app.config["SERVER_NAME"] = "canaille.test"

    res = testclient.get("/.env%0d%0a", headers={"Host": "localhost"}, status=302)
    assert res.location == "http://canaille.test/.env"
    assert "\r" not in res.location
    assert "\n" not in res.location


def test_non_get_with_wrong_host_returns_400(testclient):
    """Non-GET requests with wrong host return 400 instead of redirect."""
    testclient.app.config["SERVER_NAME"] = "canaille.test"

    res = testclient.delete("/login", headers={"Host": "localhost"}, status=400)
    assert res.status_int == 400
    assert "canaille.test" in res.text
