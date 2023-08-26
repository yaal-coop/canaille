from authlib.jose import JsonWebKey


def test_jwks(testclient, keypair):
    _, pubkey = keypair
    jwk = JsonWebKey.import_key(pubkey, {"kty": "RSA"})

    res = testclient.get("/oauth/jwks.json")
    assert res.json == {
        "keys": [
            {
                "use": "sig",
                "alg": "RS256",
                **jwk,
            }
        ]
    }
