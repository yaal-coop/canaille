Backends
#############

.. contents::
   :local:

LDAP
====

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
