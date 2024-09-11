Troubleshooting
###############

The web interface throws useless error messages
===============================================

Unless the current user has admin :class:`permissions <canaille.core.configuration.Permission>`, or the installation is in :attr:`~canaille.app.configuration.RootSettings.DEBUG` mode, error messages won't be too technical.
For instance, you can see *The request you made is invalid*.
To enable detailed error messages, you can **temporarily** enable the :attr:`~canaille.app.configuration.RootSettings.DEBUG` configuration parameter.

How to manually install LDAP schemas?
=====================================

.. note::

   Schema installation can be automatically done using the :ref:`install command <cli_install>`.

As of OpenLDAP 2.4, two configuration methods are available:

- The `deprecated <https://www.openldap.org/doc/admin26/slapdconf2.html>`_ one, based on a configuration file (generally ``/etc/ldap/slapd.conf``);
- The new one, based on a configuration directory (generally ``/etc/ldap/slapd.d``).

Depending on the configuration method you use with your OpenLDAP installation, you need to chose how to add the canaille schemas:

Old fashion: Copy the schemas in your filesystem
------------------------------------------------

.. code-block:: bash

    test -d /etc/openldap/schema && sudo cp "$CANAILLE_INSTALL_DIR/env/lib/python*/site-packages/canaille/backends/ldap/schemas/*" /etc/openldap/schema
    test -d /etc/ldap/schema && sudo cp "$CANAILLE_INSTALL_DIR/env/lib/python*/site-packages/canaille/backends/ldap/schemas/*" /etc/ldap/schema
    sudo service slapd restart

New fashion: Use slapadd to add the schemas
-------------------------------------------

Be careful to stop your ldap server before running ``slapadd``

.. code-block:: bash

    sudo service slapd stop
    sudo -u openldap slapadd -n0 -l "$CANAILLE_INSTALL_DIR/env/lib/python*/site-packages/canaille/backends/ldap/schemas/*.ldif"
    sudo service slapd start

How to manually generate the OIDC keypair?
==========================================

.. note::

   The keypair generation can be automatically done using the :ref:`install command <cli_install>`.

Canaille needs a key pair to sign OIDC tokens.
You can customize those commands, as long as they match the ``JWT`` section of your configuration file.

.. code-block:: bash

    sudo openssl genrsa -out "$CANAILLE_CONF_DIR/private.pem" 4096
    sudo openssl rsa -in "$CANAILLE_CONF_DIR/private.pem" -pubout -outform PEM -out "$CANAILLE_CONF_DIR/public.pem"
