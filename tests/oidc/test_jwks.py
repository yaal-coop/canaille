from unittest import mock

from joserfc.jwk import RSAKey


def test_jwks(testclient, keypair):
    _, pubkey = keypair
    jwk = RSAKey.import_key(pubkey)

    res = testclient.get("/oauth/jwks.json")
    assert res.json == {
        "keys": [
            {
                "kid": mock.ANY,
                "use": "sig",
                "alg": "RS256",
                **jwk,
            }
        ]
    }
