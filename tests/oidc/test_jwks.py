from canaille.oidc.jwk import make_default_jwk


def test_deterministic_jwk_generation_with_seed():
    """Test that the same seed always generates the same JWK."""
    test_seed = "test-seed-123"

    jwk1 = make_default_jwk(test_seed).as_dict()
    jwk2 = make_default_jwk(test_seed).as_dict()
    jwk3 = make_default_jwk(test_seed).as_dict()

    assert jwk1 == jwk2
    assert jwk2 == jwk3
    assert jwk1 == jwk3

    assert "kid" in jwk1
    assert "kty" in jwk1
    assert jwk1["kty"] == "OKP"
    assert jwk1["crv"] == "Ed25519"

    jwk4 = make_default_jwk("different-seed-456").as_dict()

    assert jwk1 != jwk4

    jwk5 = make_default_jwk("different-seed-456").as_dict()
    assert jwk4 == jwk5


def test_random_jwk_generation_without_seed():
    """Test that without seed, JWKs are randomly generated."""
    jwk1 = make_default_jwk(None).as_dict()
    jwk2 = make_default_jwk(None).as_dict()

    assert jwk1 != jwk2

    assert "kty" in jwk1
    assert jwk1["kty"] == "OKP"
    assert jwk1["crv"] == "Ed25519"


def test_jwks(testclient, server_jwk, old_server_jwk):
    res = testclient.get("/oauth/jwks.json")
    assert res.json == {
        "keys": [
            server_jwk.as_dict(private=False),
            old_server_jwk.as_dict(private=False),
        ]
    }
