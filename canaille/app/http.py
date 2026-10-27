"""The outgoing HTTP requests of Canaille."""

import httpx2
from flask import current_app


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

    def build(self, **kwargs) -> httpx2.Client:
        """Return a new client that routes the mounted URL prefixes."""
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
        self.client = self.build()


def setup_http(app) -> None:
    app.extensions["canaille_http"] = HTTP()


def http() -> HTTP:
    """Return the outgoing HTTP requests of the current application."""
    return current_app.extensions["canaille_http"]
