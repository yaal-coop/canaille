import gzip

import pytest

from canaille.oidc.utils import fetch_document
from canaille.oidc.utils import unique_scopes


def test_unique_scopes():
    assert unique_scopes("openid profile openid email profile") == [
        "openid",
        "profile",
        "email",
    ]
    assert unique_scopes("openid   profile") == ["openid", "profile"]
    assert unique_scopes("") == []
    assert unique_scopes(None) == []


def test_fetch_document(httpserver):
    httpserver.expect_request("/doc").respond_with_data("hello")
    url = f"http://{httpserver.host}:{httpserver.port}/doc"

    assert fetch_document(url) == "hello"
    assert fetch_document(url, max_size=5) == "hello"


def test_fetch_document_compression_bomb(httpserver):
    """The size limit applies to the decompressed content.

    The announced ``Content-Length`` is that of the compressed payload, and stays
    below the limit, so only the chunk accounting can catch this.
    """
    payload = gzip.compress(b"a" * 1_000_000)
    assert len(payload) < 2000

    httpserver.expect_request("/bomb").respond_with_data(
        payload, headers={"Content-Encoding": "gzip"}
    )
    url = f"http://{httpserver.host}:{httpserver.port}/bomb"

    with pytest.raises(ValueError):
        fetch_document(url)


def test_fetch_document_bails_out_on_content_length(httpserver):
    """Documents announcing a too big size are refused before being read."""
    httpserver.expect_request("/doc").respond_with_data("a" * 100)
    url = f"http://{httpserver.host}:{httpserver.port}/doc"

    with pytest.raises(ValueError):
        fetch_document(url, max_size=99)
