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
    ROOT_DN = "dc=mydomain,dc=tld"
    BIND_DN = "cn=admin,dc=mydomain,dc=tld"
    BIND_PW = "very-secret-password"

    USER_BASE = "ou=users,dc=mydomain,dc=tld"
    USER_CLASS = "inetOrgPerson"
    USER_FILTER = "(|(uid={{ login }})(mail={{ login }}))"

    GROUP_BASE = "ou=groups,dc=mydomain,dc=tld"

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

.. literalinclude :: ../..//demo/ldif/memberof-config.ldif
   :language: ldif
   :caption: memberof-config.ldif

.. literalinclude :: ../..//demo/ldif/refint-config.ldif
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

.. literalinclude :: ../../demo/ldif/ppolicy-config.ldif
   :language: ldif
   :caption: ppolicy-config.ldif

.. literalinclude :: ../../demo/ldif/ppolicy.ldif
   :language: ldif
   :caption: ppolicy.ldif

You can adapt and load those configuration files with:

.. code-block:: bash

    # Adapt those commands according to your setup
    sudo ldapadd -Q -H ldapi:/// -Y EXTERNAL -f ppolicy-config.ldif
    sudo ldapadd -Q -H ldapi:/// -Y EXTERNAL -f ppolicy.ldif

otp
~~~~~~~

If the `otp <https://www.openldap.org/software/man.cgi?query=slapo-otp>`_ overlay is configured, you will be able to add one-time password authentication in canaille.

Here is a configuration example compatible with canaille:

.. literalinclude :: ../../demo/ldif/otp-config.ldif
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
