def test_content_security_policy(testclient):
    """Test that Content-Security-Policy header is set correctly on responses."""
    res = testclient.get("/login", status=200)
    assert (
        res.headers["Content-Security-Policy"]
        == "default-src 'self'; font-src 'self' data:; img-src 'self' blob: data: https:"
    )
