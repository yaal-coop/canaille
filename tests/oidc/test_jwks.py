from unittest import mock

from joserfc.jwk import RSAKey

from flask import current_app

def test_jwks(testclient, keypair):
    _, pubkey = keypair
    jwk = RSAKey.import_key(pubkey)

    res = testclient.get("/oauth/jwks.json")
    assert res.json == [
        None,
        {
        "keys": [
            {
                "kid": mock.ANY,
                "use": "sig",
                "alg": "RS256",
                **jwk,
            }
        ]
        }
        ]

def test_rotate_keys(testclient, logged_admin):
    res = testclient.get("/oauth/jwks.json")
    assert res.json[0] is None
    res = testclient.get("/admin/token/rotate-keys", status=302)
    assert res.location == "/admin/token/"
    assert res.flashes == [("success", "The signing keys were changed successfully.")]
    res = testclient.get("/oauth/jwks.json")
    assert res.json[0] is not None
    assert res.json[0] != res.json[1]
