from urllib.parse import urlparse

import httpx
from flask import current_app

from canaille.app.i18n import lazy_gettext as _

MAX_DOCUMENT_SIZE = 64 * 1024
"""Maximum size in bytes of the documents downloaded at client indicated URIs."""

SCOPE_DETAILS = {
    "profile": (
        "id card outline",
        _("Info about yourself, such as your name."),
    ),
    "email": ("at", _("Your e-mail address.")),
    "address": ("envelope open outline", _("Your postal address.")),
    "phone": ("phone", _("Your phone number.")),
    "groups": ("users", _("Groups you belong to.")),
}


def fetch_document(url: str, max_size: int = MAX_DOCUMENT_SIZE) -> str:
    """Download a document at a URI a client indicated.

    ``Content-Length`` is only trusted to bail out early, as servers can omit it
    or lie about it. The body is then read in chunks of *max_size*: getting a
    second chunk means the document is too big, and the connection is dropped
    there instead of being read to its end.

    Chunks hold decompressed data, unlike what
    :attr:`httpx.Response.num_bytes_downloaded` counts, so a compressed document
    cannot expand past the limit.

    :raises ValueError: when the document is bigger than *max_size*.
    """
    too_big = f"The document at {url} exceeds {max_size} bytes."
    with httpx.stream("GET", url) as response:
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > max_size:
            raise ValueError(too_big)

        chunks = response.iter_bytes(chunk_size=max_size)
        content = next(chunks, b"")
        if next(chunks, None) is not None:
            raise ValueError(too_big)

    return content.decode()


def unique_scopes(scope):
    """Split a space-separated scope string into an ordered list of unique scopes."""
    return list(dict.fromkeys(scope.split())) if scope else []


def is_trusted_domain(domain):
    if not domain:
        return False

    parsed = urlparse(domain)
    hostname = parsed.hostname
    if not hostname:
        return False

    trusted_domains = current_app.config["CANAILLE_OIDC"]["TRUSTED_DOMAINS"]
    for domain in trusted_domains:
        # Wildcard match: .example.com matches example.com and all subdomains
        if domain.startswith("."):
            domain_without_dot = domain[1:]
            if hostname == domain_without_dot or hostname.endswith(domain):
                return True

        # Exact match only for non-wildcard domains
        elif hostname == domain:
            return True

    return False
