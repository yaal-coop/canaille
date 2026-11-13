import socket

import httpx2
import pytest
from flask import Flask

from canaille.app.http import BlockedRequestError
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


@pytest.fixture
def ssrf_protection(app, monkeypatch):
    """Enable the SSRF protection, that is disabled in tests."""
    monkeypatch.setattr(app, "testing", False)
    monkeypatch.setattr(app, "debug", False)
    monkeypatch.delenv("AUTHLIB_INSECURE_TRANSPORT", raising=False)


@pytest.fixture
def sent_requests(monkeypatch):
    """Record the requests instead of sending them."""
    requests = []

    def handle_request(self, request):
        requests.append(request)
        return httpx2.Response(200, text="ok")

    monkeypatch.setattr(httpx2.HTTPTransport, "handle_request", handle_request)
    return requests


def resolve_to(monkeypatch, *addresses):
    """Resolve every host name to these addresses."""

    def getaddrinfo(host, port, *args, **kwargs):
        return [
            (
                socket.AF_INET6 if ":" in address else socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                (address, port),
            )
            for address in addresses
        ]

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)


def test_public_address(app, ssrf_protection, sent_requests, monkeypatch):
    """The requests to public addresses are sent unchanged."""
    resolve_to(monkeypatch, "93.184.215.14")

    assert fetch_document("https://client.test/doc") == "ok"
    assert sent_requests[0].url == "https://client.test/doc"


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "100.64.0.1",
        "169.254.169.254",
        "::1",
        "fe80::1%eth0",
        "::ffff:127.0.0.1",
        "64:ff9b::a00:1",
    ],
)
def test_local_address(
    app, ssrf_protection, sent_requests, monkeypatch, caplog, address
):
    """The requests to local networks are refused."""
    resolve_to(monkeypatch, address)

    with pytest.raises(BlockedRequestError):
        fetch_document("https://client.test/doc")

    assert not sent_requests
    assert caplog.records[-1].levelname == "SECURITY"
    assert (
        caplog.records[-1]
        .getMessage()
        .startswith("Request to https://client.test/doc refused")
    )


def test_one_local_address(app, ssrf_protection, sent_requests, monkeypatch):
    """A request is refused when one of the addresses of the host is local."""
    resolve_to(monkeypatch, "93.184.215.14", "10.0.0.1")

    with pytest.raises(BlockedRequestError):
        fetch_document("https://client.test/doc")

    assert not sent_requests


def test_allowed_network(app, ssrf_protection, sent_requests, monkeypatch):
    """The requests to the allowed networks are sent."""
    monkeypatch.setitem(
        app.config["CANAILLE"], "OUTGOING_ALLOWED_NETWORKS", ["10.0.0.0/8"]
    )
    resolve_to(monkeypatch, "10.1.2.3")

    assert fetch_document("http://client.test/doc") == "ok"


def test_allowed_network_ipv4_in_ipv6(app, ssrf_protection, sent_requests, monkeypatch):
    """IPv4-mapped addresses are checked against the allowed IPv4 networks."""
    monkeypatch.setitem(
        app.config["CANAILLE"], "OUTGOING_ALLOWED_NETWORKS", ["10.0.0.0/8"]
    )
    resolve_to(monkeypatch, "::ffff:10.1.2.3")

    assert fetch_document("http://client.test/doc") == "ok"


@pytest.mark.parametrize("setting", ["debug", "testing", "insecure_transport"])
def test_development_environments(
    app, ssrf_protection, sent_requests, monkeypatch, setting
):
    """Development and test environments can send requests to local networks."""
    if setting == "insecure_transport":
        monkeypatch.setenv("AUTHLIB_INSECURE_TRANSPORT", "1")
    else:
        monkeypatch.setattr(app, setting, True)
    resolve_to(monkeypatch, "127.0.0.1")

    assert fetch_document("http://client.test/doc") == "ok"
    assert sent_requests[0].url == "http://client.test/doc"


def test_unknown_host(app, ssrf_protection, sent_requests, monkeypatch):
    """A host that cannot be resolved gives a connection error."""

    def getaddrinfo(*args, **kwargs):
        raise socket.gaierror("unknown host")

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)

    with pytest.raises(httpx2.ConnectError):
        fetch_document("https://client.test/doc")

    assert not sent_requests


def test_trusted_client(app, ssrf_protection, sent_requests, monkeypatch):
    """The requests to configured URLs are not checked."""
    resolve_to(monkeypatch, "127.0.0.1")

    assert http().client.get("http://client.test/doc").text == "ok"
