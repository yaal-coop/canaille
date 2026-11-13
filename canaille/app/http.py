"""The outgoing HTTP requests of Canaille."""

import functools
import ipaddress
import os
import socket

import httpx2
from flask import current_app

NAT64_NETWORK = ipaddress.ip_network("64:ff9b::/96")


class BlockedRequestError(httpx2.ConnectError):
    """A request to an address that is not public was refused."""


def unwrap_ipv4(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    """Return the IPv4 address in an IPv4-mapped or NAT64 address."""
    if address.version == 6 and address.ipv4_mapped:
        return address.ipv4_mapped

    if address in NAT64_NETWORK:
        return ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)

    return address


@functools.lru_cache(maxsize=8)
def parse_networks(
    networks: tuple[str, ...],
) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    return tuple(ipaddress.ip_network(network, strict=False) for network in networks)


def is_allowed_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Whether a request can be sent to an address.

    Public addresses are allowed, and so are the addresses of the networks in
    ``OUTGOING_ALLOWED_NETWORKS``.
    """
    address = unwrap_ipv4(address)
    if address.is_global:
        return True

    networks = current_app.config["CANAILLE"]["OUTGOING_ALLOWED_NETWORKS"]
    return any(address in network for network in parse_networks(tuple(networks)))


def is_ssrf_protection_enabled() -> bool:
    """Development and test environments can send requests to local networks."""
    return not (
        current_app.debug
        or current_app.testing
        or os.environ.get("AUTHLIB_INSECURE_TRANSPORT")
    )


class PublicNetworkTransport(httpx2.HTTPTransport):
    """Refuse the requests to local networks, to prevent SSRF attacks.

    A request is refused if one of the addresses of its host is not allowed.
    The connection resolves the host again, so a DNS rebinding can bypass
    this check.
    """

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        if is_ssrf_protection_enabled():
            check_host(request)

        return super().handle_request(request)


def check_host(request: httpx2.Request) -> None:
    """Raise :class:`BlockedRequestError` if an address of the host is not allowed."""
    host = request.url.raw_host.decode("ascii")
    port = request.url.port or (443 if request.url.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise httpx2.ConnectError(str(exc), request=request) from exc

    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if is_allowed_address(address):
            continue

        current_app.logger.security(
            "Request to %s refused, as %s is not a public address. "
            "Allow its network with OUTGOING_ALLOWED_NETWORKS.",
            request.url,
            address,
        )
        raise BlockedRequestError(f"{address} is not a public address", request=request)


class HTTP:
    """Build the clients for the outgoing HTTP requests of the application.

    URL prefixes can be routed to other transports with :meth:`mount`, for
    instance to serve the requests to a client application from a WSGI
    application in tests::

        http = app.extensions["canaille_http"]
        http.mount("http://client.test", httpx2.WSGITransport(app=client_app))
    """

    def __init__(self):
        self.mounts = {}
        self.client = self.build()
        self.untrusted_client = self.build(untrusted=True)

    def build(self, untrusted: bool = False, **kwargs) -> httpx2.Client:
        """Return a new client that routes the mounted URL prefixes.

        Use ``untrusted`` for the URLs that clients provide.
        The requests to local networks are then refused,
        and the proxies of the environment are ignored.
        """
        if untrusted:
            kwargs["transport"] = PublicNetworkTransport()
            kwargs["trust_env"] = False

        return httpx2.Client(mounts=self.mounts, **kwargs)

    def mount(self, prefix: str, transport: httpx2.BaseTransport) -> None:
        """Route the requests to the URLs starting with ``prefix`` to ``transport``."""
        self.mounts[prefix] = transport
        self.reset()

    def unmount(self, prefix: str) -> None:
        """Stop routing the requests to the URLs starting with ``prefix``."""
        self.mounts.pop(prefix, None)
        self.reset()

    def reset(self) -> None:
        self.client.close()
        self.untrusted_client.close()
        self.client = self.build()
        self.untrusted_client = self.build(untrusted=True)


def setup_http(app) -> None:
    app.extensions["canaille_http"] = HTTP()


def http() -> HTTP:
    """Return the outgoing HTTP requests of the current application."""
    return current_app.extensions["canaille_http"]
