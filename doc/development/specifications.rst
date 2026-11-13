Specifications
##############

This page details which specifications are implemented in Canaille, and compares Canaille with other well-known identity providers.

State of the specs in Canaille
==============================

OAuth2
------

🟡 means that the support is partial. The note tells what is missing.

- ✅ `RFC6749: OAuth 2.0 Framework <https://tools.ietf.org/html/rfc6749>`_
- ✅ `RFC6750: OAuth 2.0 Bearer Tokens <https://tools.ietf.org/html/rfc6750>`_
- ✅ `RFC7009: OAuth 2.0 Token Revocation <https://tools.ietf.org/html/rfc7009>`_
- ✅ `RFC7521: Assertion Framework for OAuth 2.0 Client Authentication and Authorization Grants <https://tools.ietf.org/html/rfc7521>`_
- ❌ `RFC7522: SAML 2.0 Profile for OAuth 2.0 Client Authentication and Authorization Grants <https://tools.ietf.org/html/rfc7522>`_
- ✅ `RFC7523: JWT Profile for OAuth 2.0 Client Authentication and Authorization Grants <https://tools.ietf.org/html/rfc7523>`_
- ✅ `RFC7591: OAuth 2.0 Dynamic Client Registration Protocol <https://tools.ietf.org/html/rfc7591>`_
- ✅ `RFC7592: OAuth 2.0 Dynamic Client Registration Management Protocol <https://tools.ietf.org/html/rfc7592>`_
- ✅ `RFC7636: Proof Key for Code Exchange by OAuth Public Clients <https://tools.ietf.org/html/rfc7636>`_
- ✅ `RFC7662: OAuth 2.0 Token Introspection <https://tools.ietf.org/html/rfc7662>`_
- ✅ `RFC8176: Authentication Method Reference Values <https://tools.ietf.org/html/rfc8176>`_
- ✅ `RFC8414: OAuth 2.0 Authorization Server Metadata <https://tools.ietf.org/html/rfc8414>`_
- ✅ `RFC8628: OAuth 2.0 Device Authorization Grant <https://tools.ietf.org/html/rfc8628>`_
- ❌ `RFC8693: OAuth 2.0 Token Exchange <https://tools.ietf.org/html/rfc8693>`_
- ❌ `RFC8705: OAuth 2.0 Mutual-TLS Client Authentication and Certificate-Bound Access Tokens <https://tools.ietf.org/html/rfc8705>`_
- ❌ `RFC8707: Resource Indicators for OAuth 2.0 <https://tools.ietf.org/html/rfc8707>`_
- ✅ `RFC9068: JSON Web Token (JWT) Profile for OAuth 2.0 Access Tokens <https://tools.ietf.org/html/rfc9068>`_
- ✅ `RFC9101: OAuth 2.0 JWT-Secured Authorization Request (JAR) <https://tools.ietf.org/html/rfc9101>`_
- ❌ `RFC9126: OAuth 2.0 Pushed Authorization Requests <https://tools.ietf.org/html/rfc9126>`_
- ✅ `RFC9207: OAuth 2.0 Authorization Server Issuer Identification <https://tools.ietf.org/html/rfc9207>`_
- ❌ `RFC9396: OAuth 2.0 Rich Authorization Requests <https://tools.ietf.org/html/rfc9396>`_
- ❌ `RFC9449: OAuth 2.0 Demonstrating Proof of Possession (DPoP) <https://tools.ietf.org/html/rfc9449>`_
- 🟡 `RFC9470: OAuth 2.0 Step Up Authentication Challenge Protocol <https://tools.ietf.org/html/rfc9470>`_:
  ``max_age`` is supported, but ``acr_values`` is not.
  Access tokens and introspection responses have no ``acr`` and ``auth_time`` claims.
- ❌ `RFC9701: JSON Web Token (JWT) Response for OAuth Token Introspection <https://tools.ietf.org/html/rfc9701>`_
- ❌ `RFC9728: OAuth 2.0 Protected Resource Metadata <https://tools.ietf.org/html/rfc9728>`_
- 🟡 `RFC10070: Updates to OAuth 2.0 JWT Client Authentication and Assertion-Based Authorization Grants <https://tools.ietf.org/html/rfc10070>`_:
  JWT authorization grants accept the issuer as audience.
  JWT client authentication still expects the token endpoint as audience.
- 🟡 `OAuth2 Multiple Response Types <https://openid.net/specs/oauth-v2-multiple-response-types-1_0.html>`_:
  all the response types are supported,
  but the authorization code flow ignores ``response_mode``.
- 🟡 `OAuth2 Form Post Response Mode <https://openid.net/specs/oauth-v2-form-post-response-mode-1_0.html>`_:
  only the implicit and hybrid flows support ``form_post``,
  and the server metadata does not list it.
- ❌ `JWT Secured Authorization Response Mode for OAuth 2.0 (JARM) <https://openid.net/specs/oauth-v2-jarm.html>`_
- ❌ `FAPI 2.0 Security Profile <https://openid.net/specs/fapi-security-profile-2_0-final.html>`_
- ❌ `FAPI 2.0 Message Signing <https://openid.net/specs/fapi-message-signing-2_0-final.html>`_

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
- ✅ `OpenID Connect Back Channel Logout <https://openid.net/specs/openid-connect-backchannel-1_0.html>`_
- ❌ `OpenID Connect Back Channel Authentication Flow <https://openid.net/specs/openid-client-initiated-backchannel-authentication-core-1_0.html>`_
- ❌ `OpenID Connect Core Error Code unmet_authentication_requirements <https://openid.net/specs/openid-connect-unmet-authentication-requirements-1_0.html>`_
- ✅ `Initiating User Registration via OpenID Connect 1.0 <https://openid.net/specs/openid-connect-prompt-create-1_0.html>`_
- ❌ `OpenID Connect Relying Party Metadata Choices <https://openid.net/specs/openid-connect-rp-metadata-choices-1_0-final.html>`_
- ❌ `OpenID Connect Ephemeral Subject Identifier <https://openid.net/specs/openid-connect-ephemeral-subject-identifier-1_0-final.html>`_
- ❌ `OpenID Federation <https://openid.net/specs/openid-federation-1_1.html>`_

Shared Signals
--------------

- ❌ `OpenID Shared Signals Framework <https://openid.net/specs/openid-sharedsignals-framework-1_0-final.html>`_
- ❌ `OpenID Continuous Access Evaluation Profile (CAEP) <https://openid.net/specs/openid-caep-1_0-final.html>`_
- ❌ `OpenID RISC Profile <https://openid.net/specs/openid-risc-1_0-final.html>`_

SCIM
----

Canaille provides a basic SCIM server implementation.

- ✅ `RFC7642: System for Cross-domain Identity Management: Definitions, Overview, Concepts, and Requirements <https://www.rfc-editor.org/rfc/rfc7642>`_
- ✅ `RFC7643: System for Cross-domain Identity Management: Core Schema <https://www.rfc-editor.org/rfc/rfc7643>`_
- ✅ `RFC7644: System for Cross-domain Identity Management: Protocol <https://www.rfc-editor.org/rfc/rfc7644>`_
- ❌ `RFC9865: Cursor-Based Pagination of SCIM Resources <https://www.rfc-editor.org/rfc/rfc9865>`_
- ❌ `RFC9944: Device Schema Extensions to the SCIM Model <https://www.rfc-editor.org/rfc/rfc9944>`_
- ❌ `RFC9967: SCIM Profile for Security Event Tokens <https://www.rfc-editor.org/rfc/rfc9967>`_

What's implemented
~~~~~~~~~~~~~~~~~~

Endpoints:

- /Users (GET, POST)
- /Users/<user_id> (GET, PUT, PATCH, DELETE)
- /Groups (GET, POST)
- /Groups/<group_id> (GET, PUT, PATCH, DELETE)
- /ServiceProviderConfig (GET)
- /Schemas (GET)
- /Schemas/<schema_id> (GET)
- /ResourceTypes (GET)
- /ResourceTypes/<resource_type_id> (GET)
- :rfc:`/.search <7644#section-3.4.3>` (POST), at the root and on /Users and /Groups
- :rfc:`/Me <7644#section-3.11>` (GET, PUT, PATCH, DELETE)
- :rfc:`/Bulk <7644#section-3.7>` (POST)

Features:

- :rfc:`filtering <7644#section-3.4.2.2>`
- :rfc:`sorting <7644#section-3.4.2.3>`
- :rfc:`pagination <7644#section-3.4.2.4>`
- :rfc:`ETags <7644#section-3.14>`
- :rfc:`attributes selection <7644#section-3.4.2.5>`

Known limits
~~~~~~~~~~~~

- With OpenLDAP, ``meta.created`` is precise to the second only, so it can differ
  from ``meta.lastModified`` on a resource that was never modified.
