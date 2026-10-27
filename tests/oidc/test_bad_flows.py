from . import client_credentials


def test_incomplete_requests(testclient, logged_user, client):
    """Test that incomplete authorization requests return a bad request error."""
    testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
        ),
        status=404,
    )


def test_bad_client(testclient, logged_user, client):
    """Test that requests with invalid client parameters return a bad request error."""
    testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            clienrt_id="nope",
        ),
        status=404,
    )


def test_token_request_without_grant_type(testclient, client):
    """A token request without grant_type returns an error, not a crash."""
    res = testclient.post(
        "/oauth/token",
        params={"code": "foobar"},
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=400,
    )
    assert res.json["error"] == "unsupported_grant_type"
