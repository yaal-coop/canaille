def test_content_security_policy(testclient):
    res = testclient.get("/login", status=200)
    assert (
        res.headers["Content-Security-Policy"]
        == "default-src 'self'; font-src 'self' data:"
    )
