def test_json_oauth_errors(testclient):
    """Checks that HTTP errors on the oauth endpoints are in the JSON format."""
    res = testclient.get("/oauth/invalid", status=404)
    assert res.json == {
        "error": "not_found",
        "error_description": "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.",
    }


def test_invalid_client(testclient, logged_user, keypair):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id="invalid",
            scope="openid profile email groups address phone",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
        status=400,
    )
    res.mustcontain("Invalid client.")


def test_no_redirect_uri(testclient, logged_user, client, backend):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            nonce="somenonce",
        ),
        status=400,
    )
    assert "Missing 'redirect_uri' in request." in str(res.html)


def test_invalid_redirect_uri(testclient, logged_user, client, backend):
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            client_id=client.client_id,
            nonce="somenonce",
            redirect_uri="https://invalid.test",
        ),
        status=400,
    )
    assert "Invalid 'redirect_uri' in request." in str(res.html)


def test_missing_client_id(
    testclient, logged_user, client, keypair, trusted_client, backend
):
    """Missing client_id should raise a 400 error."""
    res = testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            scope="openid profile email groups address phone",
            nonce="somenonce",
            redirect_uri="https://client.test/redirect1",
        ),
        status=400,
    )
    assert "'client_id' parameter is missing." in str(res.html)
