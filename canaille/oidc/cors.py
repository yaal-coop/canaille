"""CORS protection.

Should be removed in favor of flask-cors when this PR is merged:
https://github.com/corydolphin/flask-cors/pull/401
"""

from urllib.parse import urlparse

from flask import Flask
from flask import request

from canaille.app import models
from canaille.backends import Backend


def get_client_origin(client) -> str | None:
    """Extract the origin from a client's client_uri."""
    if not client.client_uri:
        return None

    parsed = urlparse(client.client_uri)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"

    return None


def get_allowed_origins() -> set[str]:
    """Get all allowed CORS origins from registered clients."""
    origins = set()
    clients = Backend.instance.query(models.Client)
    for client in clients:
        if origin := get_client_origin(client):
            origins.add(origin)
    return origins


CORS_ENABLED_PATHS = (
    "/.well-known/",
    "/oauth/token",
    "/oauth/introspect",
    "/oauth/revoke",
    "/oauth/register",
    "/oauth/jwks.json",
    "/oauth/userinfo",
    "/scim/",
)


def is_cors_enabled_path(path: str) -> bool:
    """Check if CORS is enabled for this path."""
    return any(path.startswith(prefix) for prefix in CORS_ENABLED_PATHS)


def setup_cors(app: Flask) -> None:
    """Configure CORS for OIDC and SCIM endpoints."""

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        if not origin:
            return response

        if not is_cors_enabled_path(request.path):
            return response

        allowed_origins = get_allowed_origins()
        if origin not in allowed_origins:
            return response

        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"

        if request.method == "OPTIONS":
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, POST, PUT, DELETE, OPTIONS"
            )
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization"
            )
            response.headers["Access-Control-Max-Age"] = "86400"

        return response

    @app.before_request
    def handle_preflight():
        if request.method != "OPTIONS":
            return None

        origin = request.headers.get("Origin")
        if not origin:
            return None

        if not is_cors_enabled_path(request.path):
            return None

        allowed_origins = get_allowed_origins()
        if origin not in allowed_origins:
            return None

        from flask import make_response

        response = make_response()
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE, OPTIONS"
        )
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Max-Age"] = "86400"
        response.headers["Vary"] = "Origin"
        return response
