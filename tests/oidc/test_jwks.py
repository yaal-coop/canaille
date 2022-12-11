from authlib.jose import jwk


def test_jwks(testclient, keypair):
    _, pubkey = keypair
    obj = jwk.dumps(pubkey, "RSA")

    res = testclient.get("/oauth/jwks.json")
    assert res.json == {
        "keys": [
            {
                "kid": None,
                "use": "sig",
                "alg": "RS256",
                **obj,
            }
        ]
    }
