def test_jwks(testclient, server_jwk, old_server_jwk):
    res = testclient.get("/oauth/jwks.json")
    assert res.json == {
        "keys": [
            server_jwk.as_dict(private=False),
            old_server_jwk.as_dict(private=False),
        ]
    }
