def test_incomplete_requests(testclient, logged_user, client):
    testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
        ),
        status=400,
    )


def test_bad_client(testclient, logged_user, client):
    testclient.get(
        "/oauth/authorize",
        params=dict(
            response_type="code",
            clienrt_id="nope",
        ),
        status=400,
    )
