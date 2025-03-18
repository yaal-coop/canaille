Troubleshooting
###############

The web interface throws useless error messages
===============================================

Unless the current user has admin :class:`permissions <canaille.core.configuration.Permission>`, or the installation is in :attr:`~canaille.app.configuration.RootSettings.DEBUG` mode, error messages won't be too technical.
For instance, you can see *The request you made is invalid*.
To enable detailed error messages, you can **temporarily** enable the :attr:`~canaille.app.configuration.RootSettings.DEBUG` configuration parameter.

How to manually generate the OIDC keypair?
==========================================

.. note::

   The keypair generation can be automatically done using the :ref:`install command <cli_install>`.

Canaille needs a key pair to sign OIDC tokens.
You can customize those commands, as long as they match the ``JWT`` section of your configuration file.

.. code-block:: bash

    sudo openssl genrsa -out "$CANAILLE_CONF_DIR/private.pem" 4096
    sudo openssl rsa -in "$CANAILLE_CONF_DIR/private.pem" -pubout -outform PEM -out "$CANAILLE_CONF_DIR/public.pem"

My application return errors with the Canaille connection
=========================================================

If your Canaille client is misconfigured, you can get error messages in your application logs such as ``{"error": "invalid_client"}``.
If this happens, check you application documentation to find what is the expected configuration.
A common misconfiguration is to use ``client_secret_basic`` instead of ``client_secret_post`` as client authentication method.
