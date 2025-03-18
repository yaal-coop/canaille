def test_content_security_policy(testclient):
    res = testclient.get("/login", status=302)
    assert (
        res.headers["Content-Security-Policy"]
        == "default-src 'self'; object-src 'none'"
    )
