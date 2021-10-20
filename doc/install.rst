Installation
############

⚠ Canaille is under heavy development and may not fit a production environment yet. ⚠

First you need to install the schemas into your LDAP server. There are several ways to achieve this:

LDAP schemas
============

As of OpenLDAP 2.4, two configuration methods are available:

- The `deprecated <https://www.openldap.org/doc/admin24/slapdconf2.html>`_ one, based on a configuration file (generally `/etc/ldap/slapd.conf`);
- The new one, based on a configuration directory (generally `/etc/ldap/slapd.d`).

Depending on the configuration method you use with your OpenLDAP installation, you need to chose how to add the canaille schemas:

Old fashion: Copy the schemas in your filesystem
------------------------------------------------

.. code-block:: console

    test -d /etc/openldap/schema && sudo cp schemas/* /etc/openldap/schema
    test -d /etc/ldap/schema && sudo cp schemas/* /etc/ldap/schema
    sudo service slapd restart

New fashion: Use slapadd to add the schemas
-------------------------------------------

Be careful to stop your ldap server before running `slapadd`

.. code-block:: console

    sudo service slapd stop
    sudo slapadd -n0 -l schemas/*.ldif
    sudo service slapd start

Canaille installation
=====================

Choose a path to store the canaille sources, for instance `/opt/canaille`. The install canaille there in a virtualenv.

.. code-block:: console

    sudo mkdir /etc/canaille
    sudo virtualenv /etc/canaille
    sudo /etc/canaille/bin/pip install canaille


Configuration
=============

Choose a path to store your configuration, for instance `/etc/canaille` and then copy the sample configuration there. You should also generate a keypair that canaille will use to sign tokens.

.. code-block:: console

    sudo mkdir /etc/canaille

    sudo openssl genrsa -out private.pem 4096
    sudo openssl rsa -in private.pem -pubout -outform PEM -out public.pem

    sudo cp canaille/conf/config.sample.toml /etc/canaille/config.toml
    sudo cp canaille/conf/openid-configuration.sample.json /etc/canaille/openid-configuration.json

Then check your configuration file with the following command:

.. code-block:: console

    env CONFIG=/etc/canaille/config.toml /opt/canaille/bin/canaille check


Web interface
=============

Finally you have to run the website in a WSGI server:

.. code-block:: console

    sudo /opt/canaille/bin/pip install gunicorn
    gunicorn "canaille:create_app()"

Recurrent jobs
==============

You might want to clean up your database to avoid it growing too much. You can regularly delete
expired tokens and authorization codes with:

.. code-block:: console

    env CONFIG=/etc/canaille/config.toml FASK_APP=canaille /opt/canaille/bin/canaille clean
