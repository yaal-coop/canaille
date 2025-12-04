import json
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone

import httpx
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import current_app
from joserfc import jwk
from joserfc import jws
from joserfc import jwt
from joserfc.jwk import OKPKey
from joserfc.jwk import RSAKey

from canaille.app.flask import cache

registry = jws.JWSRegistry(algorithms=list(jws.JWSRegistry.algorithms.keys()))


def supported_verification_algorithms(excluded=None):
    """Return the list of JWS algorithms the server can verify."""
    return [
        alg for alg in registry.algorithms.keys() if not excluded or alg not in excluded
    ]


def make_default_okp_jwk(seed=None):
    """Generate a deterministic JWK based on a seed if available.

    If seed is provided, it will be used to generate a deterministic Ed25519 key.
    Otherwise, a random Ed25519 key is generated.
    """
    if seed:
        salt = b"canaille-jwk-generation-salt-v1"

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        key_material = kdf.derive(seed.encode())

        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(key_material)
    else:
        private_key = ed25519.Ed25519PrivateKey.generate()

    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    key = OKPKey.import_key(pem)
    key.ensure_kid()

    return key


def make_default_rsa_jwk():
    """Generate a random RSA JWK for RS256 support."""
    return RSAKey.generate_key(2048, auto_kid=True)


def has_rsa_key(keys):
    """Check if at least one RSA key is present in the key list."""
    for key in keys:
        key_obj = jwk.import_key(key)
        if key_obj.as_dict().get("kty") == "RSA":
            return True
    return False


def get_alg_for_key(key):
    """Find the algorithm for the given key."""
    return registry.guess_alg(key, registry.Strategy.SECURITY)


def server_jwks(include_inactive=True):
    keys = list(current_app.config["CANAILLE_OIDC"]["ACTIVE_JWKS"])
    if include_inactive and current_app.config["CANAILLE_OIDC"]["INACTIVE_JWKS"]:
        keys += list(current_app.config["CANAILLE_OIDC"]["INACTIVE_JWKS"])

    key_objs = []
    for key in keys:
        key_objs.append(jwk.import_key(key))

    for obj in key_objs:
        obj.ensure_kid()
    return jwk.KeySet(key_objs)


def get_algorithms_for_key(key):
    # hotfix for https://github.com/authlib/joserfc/pull/79
    algorithms = registry.filter_algorithms(key, registry.algorithms.keys())

    # hotfix for https://github.com/authlib/joserfc/pull/80
    key_dict = key.as_dict()
    if key_dict.get("kty") == "OKP":
        crv = key_dict.get("crv")
        algorithms = [alg for alg in algorithms if alg.name in ("EdDSA", crv)]

    return algorithms


def supported_signing_algorithms():
    """Return the list of JWS algorithms the server can sign with.

    This is computed dynamically from the active JWKS keys.
    Includes 'none' as allowed by OIDC spec for id_token and userinfo signing.
    """
    keys = server_jwks(include_inactive=False)
    algorithms = ["none"]

    # hotfix for https://github.com/authlib/joserfc/pull/81
    for key in keys.keys:  # pragma: no cover
        for alg in get_algorithms_for_key(key):
            if alg.name not in algorithms:
                algorithms.append(alg.name)

    return algorithms


def get_client_jwks(client, kid=None):
    """Get the client JWK set, either stored locally or by downloading them from the URI the client indicated."""

    @cache.cached(timeout=50, key_prefix=f"jwks_{client.client_id}")
    def get_public_jwks():
        return httpx.get(client.jwks_uri).json()

    if client.jwks_uri:
        raw_jwks = get_public_jwks()
        key_set = jwk.KeySet.import_key_set(raw_jwks)
        key = key_set.get_by_kid(kid)
        return key

    if client.jwks:
        raw_jwks = json.loads(client.jwks)
        key_set = jwk.KeySet.import_key_set(raw_jwks)
        key = key_set.get_by_kid(kid)
        return key

    return None


def build_client_management_token(
    scope: str, lifetime: timedelta | None = None, client_id: str | None = None
):
    """Build a JWT token for client registration."""
    from .provider import get_issuer

    jti = str(uuid.uuid4())
    client_id = client_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    issuer = get_issuer()

    payload = {
        "iss": issuer,
        "sub": client_id,
        "aud": issuer,
        "iat": int(now.timestamp()),
        "jti": jti,
        "scope": scope,
    }
    if lifetime:
        payload["exp"] = int((now + lifetime).timestamp())

    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    token = jwt.encode({"alg": alg}, payload, jwk_key, registry=registry)

    return token
