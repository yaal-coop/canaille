Installation
############

.. warning ::

    Canaille is under heavy development and may not fit a production environment yet.

The installation of canaille consist in several steps, some of which you can do manually or with command line tool:

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
- `sqlite` provides the dependencies to enable the SQLite backend;
- `postgresql` provides the dependencies to enable the PostgreSQL backend;
- `mysql` provides the dependencies to enable the MySQL backend;
- `sentry` provides sentry integration to watch Canaille exceptions;
- `otp` provides the dependencies to enable one-time password authentication;
- `sms` provides the dependencies to enable sms sending;
- `all` provides all the extras above.

They can be installed with:

.. code-block:: bash

   pip install "canaille[front,oidc,postgresql]"

Configure
=========

Choose a path where to store your configuration file. You can pass any configuration path with the ``CONFIG`` environment variable.

.. code-block:: bash

    export CANAILLE_CONF_DIR=/etc/canaille
    sudo mkdir --parents "$CANAILLE_CONF_DIR"
    sudo cp $CANAILLE_INSTALL_DIR/env/lib/python*/site-packages/canaille/config.sample.toml "$CANAILLE_CONF_DIR/config.toml"

You should then edit your configuration file to adapt the values to your needs. Look at the configuration details in the :doc:`configuration <../references/configuration>` page.

Install
=======

The :ref:`install command <cli_install>` will apply most of the things needed to get Canaille working.
Depending on the configured :doc:`database <databases>` it will create the SQL tables, or install the LDAP schemas for instance.

.. code-block:: bash

    export CONFIG="$CANAILLE_CONF_DIR/config.toml"
    "$CANAILLE_INSTALL_DIR/env/bin/canaille" install

Check
=====

After a manual installation, you can check your configuration file using the :ref:`check command <cli_install>`:

.. code-block:: bash

    "$CANAILLE_INSTALL_DIR/env/bin/canaille" check
