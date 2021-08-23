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

.. code-block:: console

    sudo slapadd -n0 -l schemas/*.ldif
    sudo service slapd restart

Web interface
=============

Then you can deploy the code either by copying the git repository or installing the pip package:

.. code-block:: console

    pip install canaille

Finally you have to run the website in a WSGI server:

.. code-block:: console

    pip install gunicorn
    gunicorn "canaille:create_app()"

Recurrent jobs
==============

You might want to clean up your database to avoid it growing too much. You can regularly delete
expired tokens and authorization codes with:

.. code-block:: console

    env CONFIG=/path/to/config.toml FASK_APP=canaille flask clean
