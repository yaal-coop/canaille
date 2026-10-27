import httpx2
import pytest
from flask import Flask

from canaille.app.http import http
from canaille.oidc.utils import fetch_document


@pytest.fixture
def client_app():
    client_app = Flask("client")

    @client_app.route("/doc")
    def doc():
        return "served by the mounted application"

    return client_app


def test_mount_a_transport(app, client_app):
    """The requests to a mounted URL prefix are served by its transport."""
    http().mount("http://client.test", httpx2.WSGITransport(app=client_app))

    assert fetch_document("http://client.test/doc") == (
        "served by the mounted application"
    )
    with http().build(base_url="http://client.test") as client:
        assert client.get("/doc").text == "served by the mounted application"

    http().unmount("http://client.test")
    assert http().mounts == {}
