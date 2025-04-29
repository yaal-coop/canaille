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
