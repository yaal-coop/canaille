Databases
#########

Canaille can read and save data in different databases.
This page presents the different database backends and their specificities:

Memory
======

Canaille comes with a lightweight inmemory backend by default.
It is used when no other backend has been configured.

This backend is only for test purpose and should not be used in production environments.

SQL
===

Canaille can use any database supported by `SQLAlchemy <https://www.sqlalchemy.org/>`_, such as
sqlite, postgresql or mariadb.

Configuration
-------------

It is used when the ``CANAILLE_SQL`` configuration parameter is defined. For instance:

.. code-block:: toml
    :caption: config.toml

    [CANAILLE_SQL]
    SQL_DATABASE_URI = "postgresql://user:password@localhost/database"

You can find more details on the SQL configuration in the :class:`dedicated section <canaille.backends.sql.configuration.SQLSettings>`.

Migrations
----------

By default, migrations are applied when you run the web application.
You can disable this behavior with the :attr:`~canaille.backends.sql.configuration.SQLSettings.AUTO_MIGRATE` setting.
Migrations are not automatically applied with the use of the CLI though.

Migrations are done with :doc:`flask-alembic <flask-alembic:use>`, that provides a dedicated CLI to manually tune migrations.
You can check the :doc:`flask-alembic documentation <flask-alembic:index>` and the ``canaille db`` command line if you are in trouble.

LDAP
====

Canaille can use OpenLDAP as its main database.
It is used when the ``CANAILLE_LDAP`` configuration parameter is defined. For instance:

.. code-block:: toml
    :caption: config.toml

    [CANAILLE_LDAP]
    URI = "ldap://ldap"
    ROOT_DN = "dc=example,dc=org"
    BIND_DN = "cn=admin,dc=example,dc=org"
    BIND_PW = "very-secret-password"

    USER_BASE = "ou=users,dc=example,dc=org"
    USER_CLASS = "inetOrgPerson"

    GROUP_BASE = "ou=groups,dc=example,dc=org"

If you want to use TOTP/HOTP authentication, you will need to add the ``oathHOTPToken`` class to the user:

.. code-block:: toml

   USER_CLASS = ["inetOrgPerson", "oathHOTPToken"]

You can find more details on the LDAP configuration in the :class:`dedicated section <canaille.backends.ldap.configuration.LDAPSettings>`.

.. note ::
   Currently, only the ``inetOrgPerson``, ``oathHOTPToken`` and ``groupOfNames`` schemas have been tested.
   If you want to use different schemas or LDAP servers, adaptations may be needed.
   Patches are welcome.

OpenLDAP overlays integration
-----------------------------

Canaille can integrate with several OpenLDAP overlays:

memberof / refint
~~~~~~~~~~~~~~~~~

`memberof <https://www.openldap.org/doc/admin26/overlays.html#Reverse%20Group%20Membership%20Maintenance>`_
and `refint <https://www.openldap.org/doc/admin26/overlays.html#Referential%20Integrity>`_
overlays are needed for the Canaille group membership to work correctly.

Here is a configuration example compatible with canaille:

.. literalinclude :: ../..//dev/ldif/memberof-config.ldif
   :language: ldif
   :caption: memberof-config.ldif

.. literalinclude :: ../..//dev/ldif/refint-config.ldif
   :language: ldif
   :caption: refint-config.ldif

You can adapt and load those configuration files with:

.. code-block:: bash

    # Adapt those commands according to your setup
    sudo ldapadd -Q -H ldapi:/// -Y EXTERNAL -f memberof-config.ldif
    sudo ldapadd -Q -H ldapi:/// -Y EXTERNAL -f refint-config.ldif

ppolicy
~~~~~~~

If the `ppolicy <https://www.ietf.org/archive/id/draft-behera-ldap-password-policy-11.html>`_ overlay is configured and the ``pwdEndTime`` attribute is available (since OpenLDAP 2.6), then account locking support will be enabled in canaille. To allow users to manage account expiration, they need to have a *write* permission on the :attr:`~canaille.core.models.User.lock_date` attribute.

Here is a configuration example compatible with canaille:

.. literalinclude :: ../../dev/ldif/ppolicy-config.ldif
   :language: ldif
   :caption: ppolicy-config.ldif

.. literalinclude :: ../../dev/ldif/ppolicy.ldif
   :language: ldif
   :caption: ppolicy.ldif

You can adapt and load those configuration files with:

.. code-block:: bash

    # Adapt those commands according to your setup
    sudo ldapadd -Q -H ldapi:/// -Y EXTERNAL -f ppolicy-config.ldif
    sudo ldapadd -Q -H ldapi:/// -Y EXTERNAL -f ppolicy.ldif

otp
~~~

If the `otp <https://www.openldap.org/software/man.cgi?query=slapo-otp>`_ overlay is configured, you will be able to add one-time password authentication in canaille.

Here is a configuration example compatible with canaille:

.. literalinclude :: ../../dev/ldif/otp-config.ldif
   :language: ldif
   :caption: otp-config.ldif

You can adapt and load this configuration file with:

.. code-block:: bash

    # Adapt this command according to your setup
    sudo ldapadd -Q -H ldapi:/// -Y EXTERNAL -f otp-config.ldif

You will also need to add the ``oathHOTPToken`` class to the user:

.. code-block:: toml
    :caption: config.toml

    [CANAILLE_LDAP]
    ...
    USER_CLASS = ["inetOrgPerson", "oathHOTPToken"]

.. _ldap_manual_schema_installation:

Manual schema installation
--------------------------

Schema installation can be automatically done using the :ref:`install command <cli_install>`.
If for some reason you prefer to install schemas manually, here is how to do.
First of all, you need to locate the ``oauth2-openldap.ldif`` on your system, or copy it from the Canaille repository.

Using ``ldapadd``
~~~~~~~~~~~~~~~~~

.. code-block:: bash

    sudo ldapadd -Q -H ldapi:/// -Y EXTERNAL -f /path/to/oauth2-openldap.ldif

Using ``slapadd``
~~~~~~~~~~~~~~~~~

Be careful to stop your ldap server before running ``slapadd``

.. code-block:: bash

    sudo service slapd stop
    sudo -u openldap slapadd -n0 -l /path/to/oauth2-openldap.ldif
    sudo service slapd start

.. _ldap_schema_update:

Schema update
-------------

OpenLDAP provides no way of migrating schemas.
Canaille provides its own LDAP OIDC schemas, luckily they are quite stable, but fixes may happen.
Updating LDAP schemas may be a tricky operation, the safest way to achieve this is to follow those steps:

Backup and purge
~~~~~~~~~~~~~~~~

First, let us backup the OIDC objects and then remove them from the database.
Please perform your own backups too, in case something unexpected happens.

.. code-block:: console
    :caption: Backup and purge OIDC related objects

    canaille dump client authorizationcode consent token > dump.json
    canaille delete client --noconfirm
    canaille delete authorizationcode --noconfirm
    canaille delete consent --noconfirm
    canaille delete token --noconfirm

Delete the old schema
~~~~~~~~~~~~~~~~~~~~~

You can use the ``ldapdelete`` command to remove the old schema.

In the following command, you might adapt the schema DN, for instance use ``cn={4}oauth,cn=schema,cn=config`` instead of ``cn=oauth,cn=schema,cn=config``.

.. code-block:: console
    :caption: Removing the old schema with ldapdelete

    sudo ldapdelete -Q -H ldapi:/// -Y EXTERNAL "cn=oauth,cn=schema,cn=config"

For good measure, you may then restart your ldap server.

Alternatively you could use the ``slapmodify`` command.
It is supposed to be executed while your LDAP server is turned off.

.. code-block:: console
    :caption: Removing the old schema with slapmodify

    sudo slapmodify -n0 <<EOL
    dn: cn=oauth,cn=schema,cn=config
    changetype: delete
    EOL

Add the new schema
~~~~~~~~~~~~~~~~~~

To add the new schema, run the :ref:`install command <cli_install>` or follow instructions on the :ref:`ldap_manual_schema_installation` section.

Restore the data
~~~~~~~~~~~~~~~~

Now that the schemas are updated, you can restore the saved data:

.. code-block:: console
    :caption: Restore OIDC related objects

    canaille restore < dump.json

Dump and restore
================

Backups
-------

The :ref:`cli_dump` and :ref:`cli_restore` commands can be used to dump all the Canaille objects, or load them in the current database.
Those commands can be used for backuping Canaille data.

.. _database_migration:

Migration
---------

The dump format is the same whatever database backend is used, and thus it can be used to migrate from a database backend to another.
To achieve a migration, you need to have two configuration files prepared for the source database and the destination database.
For instance, if you want to migrate from a LDAP database to a SQL database, you can execute something like this:

.. code-block:: console
    :caption: Migrating data from a LDAP directory to a SQL database

    env CONFIG=sql-config.toml canaille install
    env CONFIG=ldap -config.toml canaille dump | env CONFIG=sql-config.toml canaille restore
