Single Sign-On
##############

Canaille implements several OAuth2 and OpenID Connect :doc:`specifications <../development/specifications>` that allow users to log themselves once on Canaille,
and have access to other applications without logging in anew.

Installation
============

To use the single sign-on feature, Canaille needs to be installed with the ``oidc`` :ref:`package extra <package_extras>`.
Then the feature is enabled by default, but can be disabled with the :attr:`~canaille.oidc.configuration.OIDCSettings.ENABLE_OIDC` configuration parameter.

Discovery endpoints
===================

The OAuth2 discovery endpoint is located at ``/.well-known/oauth-authorization-server`` and the OpenID Connect discovery endpoint is located at ``/.well-known/openid-configuration``.

Dynamic client registration
===========================

The easiest way to register a client is to let the client register itself.
You can either provide a registration token to the client by adding it to the :attr:`~canaille.oidc.configuration.OIDCSettings.DYNAMIC_CLIENT_REGISTRATION_TOKENS` configuration parameter, or enable registration for all clients without token by enabling :attr:`~canaille.oidc.configuration.OIDCSettings.DYNAMIC_CLIENT_REGISTRATION_OPEN`.

Manual client registration
==========================

.. screenshot:: |canaille|/admin/client/add
   :context: admin
   :align: right
   :width: 275px

   The client addition page.

Users with the right :attr:`~ canaille.core.configuration.Permission.MANAGE_OIDC` permission can manage OIDC clients through the web interface.

Here are some details about the fields in the client edition and registration form:

Name
----

This is the name that will be displayed on the web interface, and notably on the consent page.

Contacts
--------

Those are the email addresses of people responsible for the client.

URI
---

URL string of a web page providing information about the client.

Redirect URIs
-------------

URIs for use in redirect-based flows such as the authorization code and implicit flows.

Post logout redirect URIs
-------------------------

URIs that the client may redirect users to after logging them out.

.. _grant_types:

Grant types
-----------

Grant types that the client can use at the token endpoint.

- **password** allows clients to authenticate users by forwarding their password to the authorization server.
  This is considered an unsecured flow and is removed from the incoming OAuth 2.1 specification.
  Only enable this grant when the client don't support other more secured flow.
- **authorization code** redirects end-users to the authorization server, optionally ask for their consent, then redirect users to the client application with an *authorization code* that it can exchange in a second time with an *access token*.
  This is the most common grant type.
- **implicit** redirects end-users to the authorization server, optionally ask for their consent, then redirect users to the client application with an *access token*.
  This grant type is less secured than *authorization code*, and is only intended to be used for client applications that cannot guarantee the secrecy of their credentials, such as SPA.
- **hybrid** is a mix of *implicit* and *authorization code*, and share the security defaults of *implicit*.
- **refresh token** asks for a token that cannot be used to access protected resources, but can be used to get a new access token without user manual intervention.
  This is generally useful.
- **client credentials** is intended to be used for server-to-server applications, when no user interaction is expected. For example this is the grant type that should be used for :doc:`provisioning <provisioning>`.
- **JWT bearer** allows clients to exchange a JWT signed by the authorization server against an *access token*.

Scope
-----

Kind of information that the client can request about users.

- **openid** is needed for the client to be able to access the *UserInfo* endpoint.
- **profile** gives access to users :attr:`~canaille.core.models.User.name`,
  :attr:`family names <canaille.core.models.User.family_name>`,
  :attr:`given names <canaille.core.models.User.given_name>`,
  :attr:`display names <canaille.core.models.User.display_name>`,
  :attr:`photos <canaille.core.models.User.photo>`,
  :attr:`profile URLs <canaille.core.models.User.profile_url>`,
  :attr:`preferred languages <canaille.core.models.User.preferred_language>` and
  :attr:`last update dates <canaille.backends.models.Model.last_modified>`.
- **email** gives access to users :attr:`email addresses <canaille.core.models.User.emails>`.
- **groups** gives access to users :attr:`~canaille.core.models.User.groups`.
- **address** gives access to users :attr:`addresses <canaille.core.models.User.formatted_address>`.
- **phone** gives access to users :attr:`phone numbers <canaille.core.models.User.phone_numbers>`.

Response types
--------------

Response types that the client can use at the authorization endpoint.

- **code** is used in the **authorization code** and can be used in the **hybrid** authorization flows.
- **token** and **id_token** are used in the **implicit** and can be used in the **hybrid** authorization flows.

Token endpoint authentication method
------------------------------------

Authentication method that the client will use at the token endpoint.

- **none** indicate clients do not authenticate on the token endpoint.
  This is considered unsecured, and should only be used for **implicit** authorization flow.
- **client_secret_basic** expects clients to pass their credentials in the request headers.
- **client_secret_post** expects clients to pass their credentials in the POST payload of the request.
- **private_key_jwt** passes a JWT signed with the client private asymmetric keys in the request POST payload.
  This is considered very secure, more so if the client publishes its public keys on the internet using the :attr:`~canaille.oidc.basemodels.Client.jwks_uri` attributes.
- **client_secret_jwt** passes a JWT signed with the client :attr:`secret <canaille.oidc.basemodels.Client.client_secret>` attribute in the request POST payload.
  This is considered secured, although less than **private_key_jwt**, but this does not require the client to publish its asymmetric keys, so it might be more easier to set-up.

Audience
--------

The other clients that are intended to use the tokens emitted by this client.

Logo URI
--------

An URL for the logo of this client.

Terms of service URI
--------------------

URL to the terms of service of the client.

Policy URI
----------

URL to the privacy policy of the client.

Software ID
-----------

Unique identifier for this client, that should be stable in time and common for all identity providers.

Software Version
----------------

The version of the client.

JSON Web Keys
-------------

The public JSON Web Keys of the client.

JSON Web Keys URI
-----------------

The URI that points to the public JSON Web Keys of the client.

Trusted
-------

Whether the clients needs to display consent dialogs.

Server key management
=====================

Key generation
--------------

The :ref:`canaille jwk create <cli_jwk>` command can be used to generate JSON Web Keys.
To install a server key, put the output of the command in the :attr:`~canaille.oidc.configuration.OIDCSettings.ACTIVE_JWKS` configuration parameter.

Key rotation
------------

It is considered a good practice to rotate the authorization server keys on a regular basis.

Canaille has two configuration parameters for key management: :attr:`~canaille.oidc.configuration.OIDCSettings.ACTIVE_JWKS`
and :attr:`~canaille.oidc.configuration.OIDCSettings.INACTIVE_JWKS`.
Only the keys listed in the former are used to sign tokens, but keys listed in both are used to verify tokens.
The keys listed in both are displayed in the server JWKS endpoint, so clients can know that JWTs signed with *inactive keys* are still valid.

To rotate keys, simply pass a key from :attr:`~canaille.oidc.configuration.OIDCSettings.ACTIVE_JWKS`
to :attr:`~canaille.oidc.configuration.OIDCSettings.INACTIVE_JWKS` and restart Canaille.
After a few time, you can purge the inactive keys.
