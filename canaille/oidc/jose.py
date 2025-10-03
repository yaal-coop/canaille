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

from canaille.app.flask import cache

registry = jws.JWSRegistry(algorithms=list(jws.JWSRegistry.algorithms.keys()))


def make_default_jwk(seed=None):
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


def get_alg_for_key(key):
    """Find the algorithm for the given key."""
    # TODO: Improve this when a better solution is implemented upstream
    # https://github.com/authlib/joserfc/issues/49
    for alg_name, alg in registry.algorithms.items():  # pragma: no cover
        if alg.key_type == key.key_type:
            return alg_name


def server_jwks(include_inactive=True):
    keys = list(current_app.config["CANAILLE_OIDC"]["ACTIVE_JWKS"])
    if include_inactive and current_app.config["CANAILLE_OIDC"]["INACTIVE_JWKS"]:
        keys += list(current_app.config["CANAILLE_OIDC"]["INACTIVE_JWKS"])

    key_objs = [jwk.import_key(key) for key in keys if key]
    for obj in key_objs:
        obj.ensure_kid()
    return jwk.KeySet(key_objs)


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
    scope: str, lifetime: timedelta, client_id: str | None = None
):
    """Build a JWT token for client registration."""
    from .provider import get_issuer

    jti = str(uuid.uuid4())
    client_id = client_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    exp = now + lifetime
    issuer = get_issuer()

    payload = {
        "iss": issuer,
        "sub": client_id,
        "aud": issuer,
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": jti,
        "scope": scope,
    }

    jwks = server_jwks(include_inactive=False)
    jwk_key = jwks.keys[0]
    alg = get_alg_for_key(jwk_key)

    token = jwt.encode({"alg": alg}, payload, jwk_key, registry=registry)

    return token
