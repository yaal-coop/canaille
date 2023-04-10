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

:SENTRY_DSN:
    *Optional.* A DSN to a sentry instance.
    This needs the ``sentry_sdk`` python package to be installed.
    This is useful if you want to collect the canaille exceptions in a production environment.

:HIDE_INVALID_LOGINS:
    *Optional.* Wether to tell the users if a username exists during failing login attempts.
    Defaults to ``True``. This may be a security issue to disable this, as this give a way to malicious people to if an account exists on this canaille instance.

:ENABLE_PASSWORD_RECOVERY:
    *Optional* Wether the password recovery feature is enabled or not.
    Defaults to ``True``.

:INVITATION_EXPIRATION:
    *Optional* The validity duration of registration invitations, in seconds.
    Defaults to 2 days.

LOGGING
-------

:LEVEL:
    *Optional.* The logging level. Must be an either *DEBUG*, *INFO*, *WARNING*, *ERROR* or *CRITICAL*. Defults to *WARNING*.

:PATH:
    *Optional.* The log file path. If not set, logs are written in the standard error output.

BACKENDS.LDAP
-------------

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
    Can be a list of classes.
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
    Can be a list of classes.
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

    - **edit_self** to allow users to edit their own profile
    - **use_oidc** to allow OpenID Connect authentication
    - **manage_oidc** to allow OpenID Connect client managements
    - **manage_users** to allow other users management
    - **manage_groups** to allow group edition and creation
    - **delete_account** allows a user to delete his own account. If used with *manage_users*, the user can delete any account
    - **impersonate_users** to allow a user to take the identity of another user

:READ:
    *Optional.* A list of attributes of ``USER_CLASS`` the user will be able to see, but not edit.
    If the users has the ``edit_self`` permission, they will be able to see those fields on their own account.
    If the users has the ``manage_users`` permission, the user will be able to see this fields on other users profile.
    If the list containts the special ``groups`` field, the user will be able to see the groups he belongs to.

:WRITE:
    *Optional.* A list of attributes of ``USER_CLASS`` the user will be able to edit.
    If the users has the ``edit_self`` permission, they will be able to edit those fields on their own account.
    If the users has the ``manage_users`` permission, they will be able to edit those fields on other users profile.
    If the list containts the special ``groups`` field, the user will be able to edit the groups he belongs to.

OIDC
----

:DYNAMIC_CLIENT_REGISTRATION_OPEN:
    *Optional.* Wether a token is needed for the RFC7591 dynamical client registration.
    If true, no token is needed to register a client.
    If false, dynamical client registration needs a token defined
    in `DYNAMIC_CLIENT_REGISTRATION_TOKENS``
    Defaults to ``False``

:DYNAMIC_CLIENT_REGISTRATION_TOKENS:
    *Optional.* A list of tokens that can be used for dynamic client registration

OIDC.JWT
--------
Canaille needs a key pair to sign the JWT. The installation command will generate a key pair for you, but you can also do it manually.

:PRIVATE_KEY:
    **Required.** The path to the private key.
    e.g. ``/path/to/canaille/conf/private.pem``

:PUBLIC_KEY:
    **Required.** The path to the public key.
    e.g. ``/path/to/canaille/conf/private.pem``

:ISS:
    *Optional.* The URI of the identity provider.
    Defaults to ``SERVER_NAME`` if set, else the current domain will be used.
    e.g. ``https://auth.mydomain.tld``

:KTY:
    *Optional.* The key type parameter.
    Defaults to ``RSA``.

:ALG:
    *Optional.* The key algorithm.
    Defaults to ``RS256``.

:EXP:
    *Optional.* The time the JWT will be valid, in seconds.
    Defaults to ``3600``

OIDC.JWT.MAPPINGS
-----------------

A mapping where keys are JWT claims, and values are LDAP user object attributes.
Attributes are rendered using jinja2, and can use a ``user`` variable.

:SUB:
    *Optional.* Defaults to ``{{ user.user_name[0] }}``

:NAME:
    *Optional.* Defaults to ``{{ user.cn[0] }}``

:PHONE_NUMBER:
    *Optional.* Defaults to ``{{ user.phone_number[0] }}``

:EMAIL:
    *Optional.* Defaults to ``{{ user.mail[0] }}``

:GIVEN_NAME:
    *Optional.* Defaults to ``{{ user.given_name[0] }}``

:FAMILY_NAME:
    *Optional.* Defaults to ``{{ user.family_name[0] }}``

:PREFERRED_USERNAME:
    *Optional.* Defaults to ``{{ user.display_name[0] }}``

:LOCALE:
    *Optional.* Defaults to ``{{ user.locale }}``

:ADDRESS:
    *Optional.* Defaults to ``{{ user.address[0] }}``

:PICTURE:
    *Optional.* Defaults to ``{% if user.photo %}{{ url_for('account.photo', user_name=user.user_name[0], field='photo', _external=True) }}{% endif %}``

:WEBSITE:
    *Optional.* Defaults to ``{{ user.profile_url[0] }}``


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

:SSL:
    Whether the SMTP connection use SSL.
    Default to ``False``

:LOGIN:
    The SMTP server authentication login.
    *Optional.*

:PASSWORD:
    The SMTP server authentication password.
    *Optional.*

:FROM_ADDR:
    *Optional.* The mail address to use as the sender for Canaille emails.
    Defaults to `admin@<HOSTNAME>` where `HOSTNAME` is the current hostname.
