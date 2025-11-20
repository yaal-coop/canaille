from canaille import create_app
from canaille.oidc.jose import make_default_jwk
from canaille.oidc.jose import server_jwks


def test_rsa_key_in_active_jwks(app, configuration):
    """Test that a generated RSA 1024-bit key can be stored in ACTIVE_JWKS as PEM string."""
    configuration["CANAILLE_OIDC"]["ACTIVE_JWKS"] = [
        """-----BEGIN PRIVATE KEY-----
MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBALrKfTyLbJW7u/7A
QUi68KOVM15vkVw601AfVTIh/WARYKH8NxC11y7kBjBxElUBETGFnSvcVloubBFO
z/hPyKIMh/QiSbHY24qUYxhcbaoq/xZrupI7hOVr+svqF9ebXRSUu04+YHySx2Mz
TbvL6lkUpk9fEQko6IyoQPZ2yzWZAgMBAAECgYBsyavgzC8Ekd8uwpgDHOUz0Jyn
XoEhXx1dJ7J9zS/9eIF4NiV39QALTkCQi/oqScHSvsfIGL6uLSVBe05Ch20IfTm7
nJrAEakGq2SgvTaz5uz3letWXdaU/MiMxdmJ2lV422f87e0MJ04Wo8fEqqS5uttI
vLfuxMdGLy8pAVkwFQJBAOIcCcIAqkDcgyf384dZdAlPuGcF5ILIeqmSIJ9YwhlI
7VmriO3sF7c4QdJmNt9rn8RulHdgCwthrGhFWmnQqucCQQDTe9bNg2Vy7QgokYHR
xrDmNUasCiF4V6HElA2UoPi1hPNVKN28LtCcM/nJtJcChmF7KaDC1qtcBAyZr9Uc
TYt/AkBkaW8r6H+zLjpQlZxgjykouW560fMY4U8X3vz9xrzr3acKG1ND1YTyqNkS
RrI3pePdp/3mxZAiDc4ywBnWxAQhAkBEE1EJxooZfINry6rmQ/cdo3ikWH59pnfE
N4RHm6lzhOBvQUBfGxK7tV9qtl8FyQwIAVZmYYO3kvYbYqZO/gcxAkEAqxqpDvHN
G8VZ5W8yHji2zmi5swjwuVj2GnPRC3NFVQpYMYm5CAtDD8DGbch9EpejPr3CGXW8
nJu1vashTRdIRA==
-----END PRIVATE KEY-----"""
    ]

    app = create_app(configuration)
    with app.app_context():
        assert server_jwks(False).as_dict() == {
            "keys": [
                {
                    "n": "usp9PItslbu7_sBBSLrwo5UzXm-RXDrTUB9VMiH9YBFgofw3ELXXLuQGMHESVQERMYWdK9xWWi5sEU7P-E_IogyH9CJJsdjbipRjGFxtqir_Fmu6kjuE5Wv6y-oX15tdFJS7Tj5gfJLHYzNNu8vqWRSmT18RCSjojKhA9nbLNZk",
                    "e": "AQAB",
                    "d": "bMmr4MwvBJHfLsKYAxzlM9Ccp16BIV8dXSeyfc0v_XiBeDYld_UAC05AkIv6KknB0r7HyBi-ri0lQXtOQodtCH05u5yawBGpBqtkoL02s-bs95XrVl3WlPzIjMXZidpVeNtn_O3tDCdOFqPHxKqkubrbSLy37sTHRi8vKQFZMBU",
                    "p": "4hwJwgCqQNyDJ_fzh1l0CU-4ZwXkgsh6qZIgn1jCGUjtWauI7ewXtzhB0mY232ufxG6Ud2ALC2GsaEVaadCq5w",
                    "q": "03vWzYNlcu0IKJGB0caw5jVGrAoheFehxJQNlKD4tYTzVSjdvC7QnDP5ybSXAoZheymgwtarXAQMma_VHE2Lfw",
                    "dp": "ZGlvK-h_sy46UJWcYI8pKLluetHzGOFPF978_ca8692nChtTQ9WE8qjZEkayN6Xj3af95sWQIg3OMsAZ1sQEIQ",
                    "dq": "RBNRCcaKGXyDa8uq5kP3HaN4pFh-faZ3xDeER5upc4Tgb0FAXxsSu7VfarZfBckMCAFWZmGDt5L2G2KmTv4HMQ",
                    "qi": "qxqpDvHNG8VZ5W8yHji2zmi5swjwuVj2GnPRC3NFVQpYMYm5CAtDD8DGbch9EpejPr3CGXW8nJu1vashTRdIRA",
                    "kty": "RSA",
                    "kid": "joG9Ezrci5jPhDO_nYV7-F8gXjs-7dCuTqH8pg2AbIY",
                }
            ]
        }


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
