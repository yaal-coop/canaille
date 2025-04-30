Troubleshooting
###############

The web interface throws useless error messages
===============================================

Error messages including technical information are displayed when logged user has admin :class:`permissions <canaille.core.configuration.Permission>`,
or the installation is in :attr:`~canaille.app.configuration.RootSettings.DEBUG` mode.

How to manually generate the OIDC keypair?
==========================================

.. note::

   The keypair generation can be automatically done using the :ref:`install command <cli_install>`.

Canaille needs a key pair to sign OIDC tokens.
You can customize those commands, as long as they match the ``JWT`` section of your configuration file.

.. code-block:: bash

    openssl genrsa -out private.pem 4096
    openssl rsa -in private.pem -pubout -outform PEM -out public.pem

My application return errors with the Canaille connection
=========================================================

If your Canaille client is misconfigured, you can get error messages in your application logs such as ``{"error": "invalid_client"}``.
If this happens, check you application documentation to find what is the expected configuration.
A common misconfiguration is to use ``client_secret_basic`` instead of ``client_secret_post`` as client authentication method.
