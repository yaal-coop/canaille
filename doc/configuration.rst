Configuration
#############

Here are the different options you can have in your configuration file.

.. contents::
   :local:

Sections
========

Miscellaneous
-------------
Canaille is based on Flask, so any `flask configuration <https://flask.palletsprojects.com/en/1.1.x/config/#builtin-configuration-values>`_ option will be usable with canaille:



:SECRET_KEY:
    **Required.** The Flask secret key. You should set a random string here.

:NAME:
    *Optional.* The name of your organization. If not set `Canaille` will be used.

:LOGO:
    *Optional.* The URL ot the logo of your organization. The default is the canaille logo.

:FAVICON:
    *Optional.* An URL to a favicon. The default is the value of ``LOGO``.

:THEME:
    *Optional.* The name or the path to a canaille theme.
    If the value is just a name, the theme should be in a directory with that namein the *themes* directory.

:LANGUAGE:
    *Optional.* The locale code of the language to use. If not set, the language of the browser will be used.

:OAUTH2_METADATA_FILE:
    *Optional.* The path to the OAUTH2 metadata file.
    If not set the file will be looked for in the same directory as the configuration file.

:OIDC_METADATA_FILE:
    *Optional.* The path to the OpenID Connect metadata file.
    If not set the file will be looked for in the same directory as the configuration file.

:SENTRY_DSN:
    *Optional.* A DSN to a sentry instance.
    This needs the ``sentry_sdk`` python package to be installed.
    This is useful if you want to collect the canaille exceptions in a production environment.

:HIDE_INVALID_LOGINS:
    *Optional.* Wether to tell the users if a username exists during failing login attempts.
    Defaults to ``True``. This may be a security issue to disable this, as this give a way to malicious people to guess who has an account on this canaille instance.

LOGGING
-------

:LEVEL:
    *Optional.* The logging level. Must be an either *DEBUG*, *INFO*, *WARNING*, *ERROR* or *CRITICAL*. Defults to *WARNING*.

:PATH:
    *Optional.* The log file path. If not set, logs are written in the standard error output.

LDAP
----

:URI:
    **Required.** The URI to the LDAP server.
    e.g. ``ldaps://ldad.mydomain.tld``

:ROOT_DN:
    **Required.** The root DN of your LDAP server.
    e.g. ``dc=mydomain,dc=tld``

:BIND_DN:
    **Required.** The LDAP DN to bind with.
    e.g. ``cn=admin,dc=mydomain,dc=tld``

:BIND_PW:
    **Required.** The LDAP user associated with ``BIND_DN``.

:TIMEOUT:
    *Optional.* The time to wait for the LDAP server to respond before considering it is not functional.

:USER_BASE:
    **Required.** The DN of the node in which users will be searched for, and created.
    e.g. ``ou=users,dc=mydomain,dc=tld``

:USER_CLASS:
    *Optional.* The LDAP object class to filter existing users, and create new users.
    Defaults to ``inetOrgPerson``.

:USER_ID_ATTRIBUTE:
    *Optional.* The attribute to identify an object in the User DN.
    For example, if it has the value ``uid``, users DN will be in the form ``uid=foobar,ou=users,dc=mydomain,dc=tld``.
    Defaults to ``cn``.

:USER_FILTER:
    *Optional.* The filter to match users on sign in.
    Supports a variable {login} that can be used to compare against several LDAP attributes.
    Defaults to ``(|(uid={login})(mail={login}))``

:GROUP_BASE:
    **Required.** The DN where of the node in which LDAP groups will be created and searched for.
    e.g. ``ou=groups,dc=mydomain,dc=tld``

:GROUP_CLASS:
    *Optional.* The LDAP object class to filter existing groups, and create new groups.
    Defaults to ``groupOfNames``

:GROUP_ID_ATTRIBUTE:
    *Optional.* The attribute to identify an object in a group DN.
    For example, if it has the value ``cn``, groups DN will be in the form ``cn=foobar,ou=users,dc=mydomain,dc=tld``.
    Defaults to ``cn``

:GROUP_NAME_ATTRIBUTE:
    *Optional.* The attribute to identify a group in the web interface.
    Defaults to ``cn``

:GROUP_USER_FILTER:
    *Optional.* A filter to check if a user belongs to a group. A 'user' variable is available.
    Defaults to ``member={user.dn}``

ACL
---
You can define access controls that define what users can do on canaille
An access control consists in a ``FILTER`` to match users, a list of ``PERMISSIONS`` that users will be able to perform, and fields users will be able
to ``READ`` and ``WRITE``. Users matching several filters will cumulate permissions.

The 'READ' and 'WRITE' attributes are the LDAP attributes of the user
object that users will be able to read and/or write.

:FILTER:
    *Optional.* A filter to test on the users to test if they belong to this ACL.
    If absent, all the users will have the permissions in this ACL.
    e.g. ``uid=admin`` or ``memberof=cn=admin,ou=groups,dc=mydomain,dc=tld``

:PERMISSIONS:
    *Optional.* A list of items the users in the access control will be able to manage. Values can be:

    - **use_oidc** to allow OpenID Connect authentication
    - **manage_oidc** to allow OpenID Connect client managements
    - **manage_users** to allow other users management
    - **manage_groups** to allow group edition and creation
    - **delete_account** allows a user to delete his own account. If used with *manage_users*, the user can delete any account
    - **impersonate_users** to allow a user to take the identity of another user

:READ:
    *Optional.* A list of attributes of ``USER_CLASS`` the user will be able to see, but not edit.
    If the user has the ``manage_users`` permission, he will be able to see this fields on other users profile.
    If the list containts the special ``groups`` field, the user will be able to see the groups he belongs to.

:WRITE:
    *Optional.* A list of attributes of ``USER_CLASS`` the user will be able to edit.
    If the user has the ``manage_users`` permission, he will be able to edit this fields on other users profile.
    If the list containts the special ``groups`` field, the user will be able to edit the groups he belongs to.


JWT
---
Canaille needs a key pair to sign the JWT. The installation command will generate a key pair for you, but you can also do it manually.

:PRIVATE_KEY:
    **Required.** The path to the private key.
    e.g. ``/path/to/canaille/conf/private.pem``

:PUBLIC_KEY:
    **Required.** The path to the public key.
    e.g. ``/path/to/canaille/conf/private.pem``

:KTY:
    *Optional.* The key type parameter.
    Defaults to ``RSA``.

:ALG:
    *Optional.* The key algorithm.
    Defaults to ``RS256``.

:EXP:
    *Optional.* The time the JWT will be valid, in seconds.
    Defaults to ``3600``

JWT.MAPPINGS
------------

A mapping where keys are JWT claims, and values are LDAP user object attributes.
Attributes are rendered using jinja2, and can use a ``user`` variable.

:SUB:
    *Optional.* Defaults to ``{{ user.uid[0] }}``

:NAME:
    *Optional.* Defaults to ``{{ user.cn[0] }}``

:PHONE_NUMBER:
    *Optional.* Defaults to ``{{ user.telephoneNumber[0] }}``

:EMAIL:
    *Optional.* Defaults to ``{{ user.mail[0] }}``

:GIVEN_NAME:
    *Optional.* Defaults to ``{{ user.givenName[0] }}``

:FAMILY_NAME:
    *Optional.* Defaults to ``{{ user.sn[0] }}``

:PREFERRED_USERNAME:
    *Optional.* Defaults to ``{{ user.displayName[0] }}``

:LOCALE:
    *Optional.* Defaults to ``{{ user.preferredLanguage[0] }}``

:ADDRESS:
    *Optional.* Defaults to ``{{ user.postalAddress[0] }}``

:PICTURE:
    *Optional.* Defaults to ``{% if user.jpegPhoto %}{{ url_for('account.photo', uid=user.uid[0], field='jpegPhoto', _external=True) }}{% endif %}``


SMTP
----
Canaille needs you to configure a SMTP server to send some mails, including the *I forgot my password* and the *invitation* mails.
Without this section Canaille will still be usable, but all the features related to mail will be disabled.

:HOST:
    The SMTP server to connect to.
    Defaults to ``localhost``

:PORT:
    The port to use with the SMTP connection.
    Defaults to ``25``

:TLS:
    Whether the SMTP connection use TLS.
    Default to ``False``

:LOGIN:
    The SMTP server authentication login.
    *Optional.*

:PASSWORD:
    The SMTP server authentication password.
    *Optional.*

:FROM_ADDR:
    *Required.* The mail address to use as the sender for Canaille emails.
