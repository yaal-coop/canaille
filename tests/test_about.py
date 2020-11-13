def test_version(testclient):
    testclient.get("/about", status=200)
