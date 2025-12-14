import logging
from urllib.parse import parse_qs
from urllib.parse import urlsplit

import pytest
from joserfc import jwk
from joserfc import jwt
from pydantic import ValidationError

from canaille import create_app
from canaille.app import models
from canaille.oidc.configuration import OIDCSettings
from canaille.oidc.jose import registry
from canaille.oidc.jose import server_jwks
from canaille.oidc.provider import get_jwt_config

from . import client_credentials


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


def test_jwks_endpoint(testclient):
    """Test that the /oauth/jwks.json endpoint returns the server's public keys."""
    res = testclient.get("/oauth/jwks.json")
    assert res.status_code == 200
    assert "keys" in res.json
    assert len(res.json["keys"]) > 0

    for key in res.json["keys"]:
        assert "kty" in key
        assert "kid" in key
        assert "d" not in key
        assert "p" not in key
        assert "q" not in key


def test_id_token_signing_uses_key_matching_client_algorithm(
    testclient, logged_user, client, backend
):
    """Test that ID token signing selects a key compatible with the client's algorithm.

    When ACTIVE_JWKS contains multiple keys (e.g., RSA first, then EC), and a client
    is configured with id_token_signed_response_alg=ES256, the server should use
    the EC key, not the first (RSA) key.
    """
    rsa_key = jwk.generate_key("RSA", 2048)
    rsa_key.ensure_kid()
    ec_key = jwk.generate_key("EC", "P-256")
    ec_key.ensure_kid()

    testclient.app.config["CANAILLE_OIDC"]["ACTIVE_JWKS"] = [
        rsa_key.as_dict(),
        ec_key.as_dict(),
    ]

    backend.update(client, id_token_signed_response_alg="ES256")
    backend.save(client)

    res = testclient.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client.client_id,
            "scope": "openid profile",
            "nonce": "testnonce",
            "redirect_uri": client.redirect_uris[0],
        },
    )
    res = res.form.submit(name="answer", value="accept", status=302)

    params = parse_qs(urlsplit(res.location).query)
    code = params["code"][0]

    res = testclient.post(
        "/oauth/token",
        params={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": client.redirect_uris[0],
        },
        headers={"Authorization": f"Basic {client_credentials(client)}"},
        status=200,
    )

    assert "id_token" in res.json

    id_token = res.json["id_token"]
    decoded = jwt.decode(id_token, ec_key, registry=registry)
    assert decoded.header["alg"] == "ES256"

    for consent in backend.query(models.Consent, subject=logged_user):
        backend.delete(consent)


def test_missing_rsa_key_error():
    """Test that an error is raised when no RSA key is configured."""
    ec_key = jwk.generate_key("EC", "P-256")
    ec_key.ensure_kid()

    with pytest.raises(
        ValidationError, match="OIDC specification requires RS256 support"
    ):
        OIDCSettings(ACTIVE_JWKS=[ec_key.as_dict()])


def test_missing_active_jwks_warning(configuration, caplog):
    """Test that a warning is logged when ACTIVE_JWKS is not configured."""
    del configuration["CANAILLE_OIDC"]["ACTIVE_JWKS"]

    with caplog.at_level(logging.WARNING):
        app = create_app(configuration)

    assert (
        "canaille",
        logging.WARNING,
        "ACTIVE_JWKS is not configured. "
        "Please generate one or several keys, including at least one RSA key. "
        "https://canaille.readthedocs.io/en/latest/howtos/sso.html#server-key-management",
    ) in caplog.record_tuples

    with app.app_context():
        assert len(server_jwks(False).keys) == 2


def test_get_jwt_config_fallback_to_first_key(testclient):
    """Test that get_jwt_config falls back to first key when no RSA key exists."""
    okp_key = jwk.generate_key("OKP", "Ed25519")
    okp_key.ensure_kid()

    testclient.app.config["CANAILLE_OIDC"]["ACTIVE_JWKS"] = [okp_key.as_dict()]

    config = get_jwt_config(None)

    assert config["key"]["kty"] == "OKP"
    assert config["alg"] == "EdDSA"
    assert config["kid"] == okp_key.kid
