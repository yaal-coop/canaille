Backends
#############

.. contents::
   :local:

Canaille can read and save data in different databases:

Memory
======

Canaille comes with a lightweight inmemory backend by default.
This backend is only for test purpose and should not be used in production environments.

It is used when the ``BACKENDS`` configuration parameter is unset or empty.

SQL
===

Canaille can use any database supported by `SQLAlchemy <https://www.sqlalchemy.org/>`_, such as
sqlite, postgresql or mariadb.

It is used when the ``BACKENDS.SQL`` configuration parameter is defined.

LDAP
====

Canaille can use OpenLDAP as its main database.
It is used when the ``BACKENDS.SQL`` configuration parameter is defined.

.. note ::
   Currently, only the ``inetOrgPerson`` and ``groupOfNames`` schemas have been tested.
   If you want to use different schemas or LDAP servers, adaptations may be needed.
   Patches are welcome.

Canaille can integrate with several OpenLDAP overlays:

memberof / refint
-----------------

*memberof* and *refint* overlays are needed for the Canaille group membership to work correctly.

Here is a configuration example compatible with canaille:

.. literalinclude :: ../demo/ldif/memberof-config.ldif
   :language: ldif

.. literalinclude :: ../demo/ldif/refint-config.ldif
   :language: ldif

ppolicy
-------

If *ppolicy* is configured and the ``pwdEndTime`` attribute is available (since OpenLDAP 2.6), then account locking support will be enabled in canaille. To allow users to manage account expiration, they need to have a *write* permission on the ``lock_date`` attribute.

Here is a configuration example compatible with canaille:

.. literalinclude :: ../demo/ldif/ppolicy-config.ldif
   :language: ldif

.. literalinclude :: ../demo/ldif/ppolicy.ldif
   :language: ldif
