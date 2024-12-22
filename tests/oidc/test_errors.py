def test_json_oauth_errors(testclient):
    """Checks that HTTP errors on the oauth endpoints are in the JSON format."""
    res = testclient.get("/oauth/invalid", status=404)
    assert res.json == {
        "error": "not_found",
        "error_description": "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.",
    }
