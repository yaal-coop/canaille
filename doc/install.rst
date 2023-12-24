Installation
############

.. warning ::

    Canaille is under heavy development and may not fit a production environment yet.

The installation of canaille consist in several steps, some of which you can do manually or with command line tool:

.. contents::
   :local:

Get the code
============

As the moment there is no distribution package for canaille. However, it can be installed with the ``pip`` package manager.
Let us choose a place for the canaille environment, like ``/opt/canaille/env``.

.. code-block:: bash

    export CANAILLE_INSTALL_DIR=/opt/canaille
    sudo mkdir --parents "$CANAILLE_INSTALL_DIR"
    sudo virtualenv --python=python3 "$CANAILLE_INSTALL_DIR/env"
    sudo "$CANAILLE_INSTALL_DIR/env/bin/pip" install "canaille[all]"

Extras
------

Canaille provides different package options:

- `front` provides all the things needed to produce the user interface;
- `oidc` provides the dependencies to perform OAuth2/OIDC authentication;
- `ldap` provides the dependencies to enable the LDAP backend;
- `sentry` provides sentry integration to watch Canaille exceptions;
- `all` provides all the extras above.

Configuration
=============

Choose a path where to store your configuration file. You can pass any configuration path with the ``CONFIG`` environment variable.

.. code-block:: bash

    export CANAILLE_CONF_DIR=/etc/canaille
    sudo mkdir --parents "$CANAILLE_CONF_DIR"
    sudo cp $CANAILLE_INSTALL_DIR/env/lib/python*/site-packages/canaille/config.sample.toml "$CANAILLE_CONF_DIR/config.toml"

You should then edit your configuration file to adapt the values to your needs. Look at the configuration details in the :doc:`configuration` page.

Install and check
=================

Automatic schemas installation
------------------------------

If you want to install the LDAP schemas yourself, then you can jump to the manual installation section.

.. code-block:: bash

    env CONFIG="$CANAILLE_CONF_DIR/config.toml" "$CANAILLE_INSTALL_DIR/env/bin/canaille" install


Manual schemas installation
---------------------------

LDAP schemas
^^^^^^^^^^^^

As of OpenLDAP 2.4, two configuration methods are available:

- The `deprecated <https://www.openldap.org/doc/admin24/slapdconf2.html>`_ one, based on a configuration file (generally ``/etc/ldap/slapd.conf``);
- The new one, based on a configuration directory (generally ``/etc/ldap/slapd.d``).

Depending on the configuration method you use with your OpenLDAP installation, you need to chose how to add the canaille schemas:

Old fashion: Copy the schemas in your filesystem
""""""""""""""""""""""""""""""""""""""""""""""""

.. code-block:: bash

    test -d /etc/openldap/schema && sudo cp "$CANAILLE_INSTALL_DIR/env/lib/python*/site-packages/canaille/backends/ldap/schemas/*" /etc/openldap/schema
    test -d /etc/ldap/schema && sudo cp "$CANAILLE_INSTALL_DIR/env/lib/python*/site-packages/canaille/backends/ldap/schemas/*" /etc/ldap/schema
    sudo service slapd restart

New fashion: Use slapadd to add the schemas
"""""""""""""""""""""""""""""""""""""""""""

Be careful to stop your ldap server before running ``slapadd``

.. code-block:: bash

    sudo service slapd stop
    sudo -u openldap slapadd -n0 -l "$CANAILLE_INSTALL_DIR/env/lib/python*/site-packages/canaille/backends/ldap/schemas/*.ldif"
    sudo service slapd start

Generate the key pair
---------------------

You must generate a keypair that canaille will use to sign tokens.
You can customize those commands, as long as they match the ``JWT`` section of your configuration file.

.. code-block:: bash

    sudo openssl genrsa -out "$CANAILLE_CONF_DIR/private.pem" 4096
    sudo openssl rsa -in "$CANAILLE_CONF_DIR/private.pem" -pubout -outform PEM -out "$CANAILLE_CONF_DIR/public.pem"

Configuration check
^^^^^^^^^^^^^^^^^^^

After a manual installation, you can check your configuration file with the following command:

.. code-block:: bash

    env CONFIG="$CANAILLE_CONF_DIR/config.toml" "$CANAILLE_INSTALL_DIR/env/bin/canaille" check
