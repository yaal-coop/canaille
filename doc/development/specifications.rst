Specifications
##############

This page details which specifications are implemented in Canaille, and compares Canaille with other well-known identity providers.

State of the specs in Canaille
==============================

OAuth2
------

- ✅ `RFC6749: OAuth 2.0 Framework <https://tools.ietf.org/html/rfc6749>`_
- ✅ `RFC6750: OAuth 2.0 Bearer Tokens <https://tools.ietf.org/html/rfc6750>`_
- ✅ `RFC7009: OAuth 2.0 Token Revocation <https://tools.ietf.org/html/rfc7009>`_
- ✅ `RFC7523: JWT Profile for OAuth 2.0 Client Authentication and Authorization Grants <https://tools.ietf.org/html/rfc7523>`_
- ✅ `RFC7591: OAuth 2.0 Dynamic Client Registration Protocol <https://tools.ietf.org/html/rfc7591>`_
- ✅ `RFC7592: OAuth 2.0 Dynamic Client Registration Management Protocol <https://tools.ietf.org/html/rfc7592>`_
- ✅ `RFC7636: Proof Key for Code Exchange by OAuth Public Clients <https://tools.ietf.org/html/rfc7636>`_
- ✅ `RFC7662: OAuth 2.0 Token Introspection <https://tools.ietf.org/html/rfc7662>`_
- ✅ `RFC8414: OAuth 2.0 Authorization Server Metadata <https://tools.ietf.org/html/rfc8414>`_
- ❌ `RFC8428: OAuth 2.0 Device Authorization Grant <https://tools.ietf.org/html/rfc8428>`_
- ❌ `RFC8693: OAuth 2.0 Token Exchange <https://tools.ietf.org/html/rfc8693>`_
- ❌ `RFC8705: OAuth 2.0 Mutual-TLS Client Authentication and Certificate-Bound Access Tokens <https://tools.ietf.org/html/rfc8705>`_
- ❌ `RFC8707: Resource Indicators for OAuth 2.0 <https://tools.ietf.org/html/rfc8707>`_
- ❌ `RFC9068: JSON Web Token (JWT) Profile for OAuth 2.0 Access Tokens <https://tools.ietf.org/html/rfc9068>`_
- ✅ `RFC9101: OAuth 2.0 JWT-Secured Authorization Request (JAR) <https://tools.ietf.org/html/rfc9101>`_
- ❌ `RFC9126: OAuth 2.0 Pushed Authorization Requests <https://tools.ietf.org/html/rfc9126>`_
- ✅ `RFC9207: OAuth 2.0 Authorization Server Issuer Identification <https://tools.ietf.org/html/rfc9207>`_
- ❌ `RFC9394: OAuth 2.0 Rich Authorization Requests <https://www.rfc-editor.org/rfc/rfc9396.html>`_
- ❌ `OAuth2 Multiple Response Types <https://openid.net/specs/oauth-v2-multiple-response-types-1_0.html>`_
- ❌ `OAuth2 Form Post Response Mode <https://openid.net/specs/oauth-v2-form-post-response-mode-1_0.html>`_

OpenID Connect
--------------

.. figure:: ../_static/oidc-certification.png
   :align: center

Since version 0.0.82, `Canaille is certified by the OpenID Foundation <https://openid.net/developers/certified-openid-connect-implementations/>`_
for the *Basic* and *Dynamic* profiles.

- ✅ `OpenID Connect Core <https://openid.net/specs/openid-connect-core-1_0.html>`_
- ✅ `OpenID Connect Discovery <https://openid.net/specs/openid-connect-discovery-1_0.html>`_
- ✅ `OpenID Connect Dynamic Client Registration <https://openid.net/specs/openid-connect-registration-1_0.html>`_
- ✅ `OpenID Connect RP Initiated Logout <https://openid.net/specs/openid-connect-rpinitiated-1_0.html>`_
- ❌ `OpenID Connect Session Management <https://openid.net/specs/openid-connect-session-1_0.html>`_
- ❌ `OpenID Connect Front Channel Logout <https://openid.net/specs/openid-connect-frontchannel-1_0.html>`_
- ❌ `OpenID Connect Back Channel Logout <https://openid.net/specs/openid-connect-backchannel-1_0.html>`_
- ❌ `OpenID Connect Back Channel Authentication Flow <https://openid.net/specs/openid-client-initiated-backchannel-authentication-core-1_0.html>`_
- ❌ `OpenID Connect Core Error Code unmet_authentication_requirements <https://openid.net/specs/openid-connect-unmet-authentication-requirements-1_0.html>`_
- ✅ `Initiating User Registration via OpenID Connect 1.0 <https://openid.net/specs/openid-connect-prompt-create-1_0.html>`_
- ❌  `OpenID Connect Profile for SCIM Services <https://openid.net/specs/openid-connect-scim-profile-1_0.html>`_

SCIM
----

Canaille provides a basic SCIM server implementation.

- 🟠 `RFC7642: System for Cross-domain Identity Management: Definitions, Overview, Concepts, and Requirements <https://www.rfc-editor.org/rfc/rfc7642>`_
- 🟠 `RFC7643: System for Cross-domain Identity Management: Core Schema <https://www.rfc-editor.org/rfc/rfc7642>`_
- 🟠 `RFC7644: System for Cross-domain Identity Management: Protocol <https://www.rfc-editor.org/rfc/rfc7642>`_

Client-side implementation (i.e. broadcasting changes on users and groups among clients) and advanced features will be implemented in the future.

What's implemented
~~~~~~~~~~~~~~~~~~

Endpoints:

- /Users (GET, POST)
- /Users/<user_id> (GET, PUT, DELETE)
- /Groups (GET, POST)
- /Groups/<user_id> (GET, PUT, DELETE)
- /ServiceProviderConfig (GET)
- /Schemas (GET)
- /Schemas/<schema_id> (GET)
- /ResourceTypes (GET)
- /ResourceTypes/<resource_type_id> (GET)

Features:

- :rfc:`pagination <7644#section-3.4.2.4>`

.. _scim_unimplemented:

What is not implemented yet
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Endpoints:

- :rfc:`/Me <7644#section-3.11>` (GET, POST, PUT, PATCH, DELETE)
- :rfc:`/Bulk <7644#section-3.11>` (POST)
- :rfc:`/.search <7644#section-3.4.3>` (POST)

Features

- :rfc:`filtering <7644#section-3.4.2.2>`
- :rfc:`sorting <7644#section-3.4.2.3>`
- :rfc:`attributes selection <7644#section-3.4.2.5>`
- :rfc:`ETags <7644#section-3.14>`

Comparison with other providers
===============================

Here is a feature comparison with other OpenID Connect server software.

Canaille voluntarily only implements the OpenID Connect protocol to keep its codebase simple.

.. list-table::
    :header-rows: 1
    :widths: 25 10 15 10 8 8 8 8 8 8

    * - Software
      - FLOSS
      - Language
      - LOC
      - OIDC
      - SAML
      - CAS
      - SCIM
      - LDAP
      - SQL
    * - Canaille
      - ✅
      - `Python <https://www.python.org/>`_
      - 10k
      - ✅
      - ❌
      - ❌
      - 🟠
      - ✅
      - ✅
    * - `Auth0 <https://auth0.com>`_
      - ❌
      - ❔
      - ❔
      - ✅
      - ✅
      - ❌
      - ✅
      - ✅
      - ❔
    * - `Authelia <https://authelia.com>`_
      - ✅
      - `Go <https://golang.org/>`_
      - `185k <https://openhub.net/p/authelia/analyses/latest/languages_summary>`_
      - ✅
      - ❌
      - ❌
      - ❌
      - ✅
      - ✅
    * - `Authentic2 <https://dev.entrouvert.org/projects/authentic>`_
      - ✅
      - `Python <https://www.python.org/>`_
      - `121k <https://openhub.net/p/authentic2/analyses/latest/languages_summary>`_
      - ✅
      - ✅
      - ✅
      - ❌
      - ✅
      - ✅
    * - `Authentik <https://goauthentik.io>`_
      - ✅
      - `Python <https://www.python.org/>`_
      - `440k <https://openhub.net/p/authentik/analyses/latest/languages_summary>`_
      - ✅
      - ✅
      - ❌
      - ✅
      - ✅
      - ✅
    * - `CAS <https://apereo.github.io/cas>`_
      - ✅
      - `Java <https://www.java.com/>`_
      - `900k <https://openhub.net/p/apereo-cas/analyses/latest/languages_summary>`_
      - ✅
      - ✅
      - ✅
      - ✅
      - ✅
      - ❌
    * - `Connect2id <https://connect2id.com>`_
      - ❌
      - ❔
      - ❔
      - ✅
      - ✅
      - ❌
      - ❌
      - ✅
      - ✅
    * - `FreeIPA <https://freeipa.org>`_
      - ✅
      - `Python <https://www.python.org/>`_
      - `585k <https://openhub.net/p/freeipa/analyses/latest/languages_summary>`_
      - ❌
      - ❌
      - ❌
      - ❌
      - ✅
      - ❌
    * - `Gluu <https://gluu.org>`_
      - ✅
      - `Java <https://www.java.com/>`_
      - `636k <https://openhub.net/p/gluu/analyses/latest/languages_summary>`_
      - ✅
      - ✅
      - ✅
      - ✅
      - ✅
      - ❔
    * - `Hydra <https://ory.sh>`_
      - ✅
      - `Go <https://golang.org/>`_
      - `119k <https://openhub.net/p/ory-hydra/analyses/latest/languages_summary>`_
      - ✅
      - ✅
      - ❌
      - ❌
      - ✅
      - ✅
    * - `Kanidm <https://kanidm.com>`_
      - ✅
      - `Rust <https://www.rust-lang.org/>`_
      - ❔
      - ✅
      - ❌
      - ❌
      - 🟠
      - ✅
      - ✅
    * - `Keycloak <https://keycloak.org>`_
      - ✅
      - `Java <https://www.java.com/>`_
      - `1.1M <https://openhub.net/p/keycloak/analyses/latest/languages_summary>`_
      - ✅
      - ✅
      - ✅
      - ✅
      - ✅
      - ✅
    * - `LemonLDAP <https://lemonldap-ng.org>`_
      - ✅
      - `Perl <https://www.perl.org/>`_
      - `410k <https://openhub.net/p/lemonldap-ng/analyses/latest/languages_summary>`_
      - ✅
      - ✅
      - ✅
      - ❌
      - ✅
      - ✅
    * - `Okta <https://okta.com>`_
      - ❌
      - ❔
      - ❔
      - ✅
      - ✅
      - ❌
      - ✅
      - ✅
      - ✅
    * - `SimpleIdServer <https://simpleidserver.com>`_
      - ✅
      - `C# <https://docs.microsoft.com/en-us/dotnet/csharp/>`_
      - ❔
      - ✅
      - ❌
      - ❌
      - ✅
      - ❌
      - ✅
    * - `WSO2 <https://wso2.com/identity-server/>`_
      - ✅
      - `Java <https://www.java.com/>`_
      - `1.4M <https://openhub.net/p/wso2-identity-server/analyses/latest/languages_summary>`_
      - ✅
      - ✅
      - ❌
      - ✅
      - ✅
      - ✅
    * - `Zitadel <https://zitadel.com>`_
      - ✅
      - `Go <https://golang.org/>`_
      - `760k <https://openhub.net/p/zitadel/analyses/latest/languages_summary>`_
      - ✅
      - ✅
      - ❌
      - ✅
      - ❌
      - ✅
