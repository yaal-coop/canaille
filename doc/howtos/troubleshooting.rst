Troubleshooting
###############

The web interface throws useless error messages
===============================================

Error messages including technical information are displayed when logged user has admin :class:`permissions <canaille.core.configuration.Permission>`,
or the installation is in :attr:`~canaille.app.configuration.RootSettings.DEBUG` mode.

My application return errors with the Canaille connection
=========================================================

If your Canaille client is misconfigured, you can get error messages in your application logs such as ``{"error": "invalid_client"}``.
If this happens, check you application documentation to find what is the expected configuration.
A common misconfiguration is to use ``client_secret_basic`` instead of ``client_secret_post`` as client authentication method.

OAuth endpoints answer ``insecure_transport``
=============================================

OAuth 2 requires HTTPS.
Canaille refuses the OAuth requests sent over plain HTTP, except to ``localhost`` and loopback addresses.
Applications then get an ``{"error": "insecure_transport"}`` response from the token endpoint, and Canaille logs a warning.

Behind a reverse proxy that handles TLS, Canaille must know that the original request used HTTPS.
Configure the proxy to send the ``X-Forwarded-Proto`` header,
and set :attr:`PROXY_MODE <canaille.hypercorn.configuration.HypercornSettings.PROXY_MODE>` as described in the :doc:`deployment guide <deployment>`.

For test environments without TLS, such as containers that reach Canaille by its service name,
set the ``AUTHLIB_INSECURE_TRANSPORT=1`` environment variable.
Never set it in production.
