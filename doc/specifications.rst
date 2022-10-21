Specifications
##############

State of the specs in Canaille
==============================

OAUTH2
------

- ✅ `RFC6749: OAuth 2.0 Framework <OAUTH2_Framework>`_
- ✅ `RFC6750: OAuth 2.0 Bearer Tokens <OAUTH2_Bearer_Tokens>`_
- ✅ `RFC7662: OAuth 2.0 Token Revocation <OAUTH2_Token_Revocation>`_
- ❌ `OAUTH2 Multiple Response Types <OAUTH2_Multiple_Response_Types>`_
- ❌ `OAUTH2 Form Post Response Mode <OAUTH2_Form_Post_Response_Mode>`_

OpenID Connect
--------------

- ✅ `OpenID Connect Core <OIDC_Core>`_
- ✅ `OpenID Connect Discovery <OIDC_Discovery>`_
- ❌ `OpenID Connect Dynamic Client Registration <OIDC_Dynamic_Client_Registration>`_
- ✅ `OpenID Connect RP Initiated Logout <OIDC_RP_Initiated_Logout>`_
- ❌ `OpenID Connect Session Management <OIDC_Session_Management>`_
- ❌ `OpenID Connect Front Channel Logout <OIDC_Front_Channel_Logout>`_
- ❌ `OpenID Connect Back Channel Logout <OIDC_Back_Channel_Logout>`_
- ❌ `OpenID Connect Back Channel Authentication Flow <OIDC_Back_Channel_Authentication_Flow>`_

.. _OAUTH2_Framework: https://tools.ietf.org/html/rfc6749
.. _OAUTH2_Bearer_Tokens: https://tools.ietf.org/html/rfc6750
.. _OAUTH2_Token_Revocation: https://tools.ietf.org/html/rfc7662
.. _OAUTH2_Multiple_Response_Types: https://openid.net/specs/oauth-v2-multiple-response-types-1_0.html
.. _OAUTH2_Form_Post_Response_Mode: https://openid.net/specs/oauth-v2-form-post-response-mode-1_0.html

.. _OIDC_Core: https://openid.net/specs/openid-connect-core-1_0.html
.. _OIDC_Discovery: https://openid.net/specs/openid-connect-discovery-1_0.html
.. _OIDC_Dynamic_Client_Registration: https://openid.net/specs/openid-connect-registration-1_0.html
.. _OIDC_RP_Initiated_Logout: https://openid.net/specs/openid-connect-rpinitiated-1_0.html
.. _OIDC_Session_Management: https://openid.net/specs/openid-connect-session-1_0.html
.. _OIDC_Front_Channel_Logout: https://openid.net/specs/openid-connect-frontchannel-1_0.html
.. _OIDC_Back_Channel_Logout: https://openid.net/specs/openid-connect-backchannel-1_0.html
.. _OIDC_Back_Channel_Authentication_Flow: https://openid.net/specs/openid-client-initiated-backchannel-authentication-core-1_0.html

Comparison with other providers
===============================

Here is a feature comparison with other OpenID Connect server software.

Canaille voluntarily only implements the OpenID Connect protocol to keep its codebase simple.
We are currently working on supporting SQL databases backends.

+---------------+-------+-----------+------+---------------------------+--------------+
| Software      | Project                  | Protocols implementations | Backends     |
|               +-------+-----------+------+------+------+-------------+------+-------+
|               | FLOSS | Language  | LOC  | OIDC | SAML | CAS         | LDAP | SQL   |
+===============+=======+===========+======+======+======+=============+======+=======+
| Canaille      | ✅    | Python    | 10k  | ✅   | ❌   | ❌          | ✅   | ❌    |
+---------------+-------+-----------+------+------+------+-------------+------+-------+
| `Auth0`_      | ❌    | ❔        | ❔   | ✅   | ✅   | ❌          | ✅   | ❔    |
+---------------+-------+-----------+------+------+------+-------------+------+-------+
| `Authelia`_   | ✅    | Go        | 50k  | ✅   | ❌   | ❌          | ✅   | ✅    |
+---------------+-------+-----------+------+------+------+-------------+------+-------+
| `Authentic2`_ | ✅    | Python    | 65k  | ✅   | ✅   | ✅          | ✅   | ✅    |
+---------------+-------+-----------+------+------+------+-------------+------+-------+
| `Authentik`_  | ✅    | Python    | 55k  | ✅   | ✅   | ❌          | ✅   | ✅    |
+---------------+-------+-----------+------+------+------+-------------+------+-------+
| `CAS`_        | ✅    | Java      | 360k | ✅   | ✅   | ✅          | ✅   | ❌    |
+---------------+-------+-----------+------+------+------+-------------+------+-------+
| `Connect2id`_ | ❌    | ❔        | ❔   | ✅   | ✅   | ❌          | ✅   | ✅    |
+---------------+-------+-----------+------+------+------+-------------+------+-------+
| `Gluu`_       | ✅    | Java      | ❔   | ✅   | ✅   | ✅          | ✅   | ❔    |
+---------------+-------+-----------+------+------+------+-------------+------+-------+
| `Hydra`_      | ✅    | Go        | 50k  | ✅   | ✅   | ❌          | ✅   | ✅    |
+---------------+-------+-----------+------+------+------+-------------+------+-------+
| `Keycloak`_   | ✅    | Java      | 600k | ✅   | ✅   | ✅          | ✅   | ✅    |
+---------------+-------+-----------+------+------+------+-------------+------+-------+
| `LemonLDAP`_  | ✅    | Perl      | 130k | ✅   | ✅   | ✅          | ✅   | ✅    |
+---------------+-------+-----------+------+------+------+-------------+------+-------+
| `Okta`_       | ❌    | ❔        | ❔   | ✅   | ✅   | ❌          | ✅   | ✅    |
+---------------+-------+-----------+------+------+------+-------------+------+-------+

.. _Auth0: https://auth0.com
.. _Authelia: https://authelia.com
.. _Authentic2: https://dev.entrouvert.org/projects/authentic
.. _Authentik: https://goauthentik.io
.. _CAS: https://apereo.github.io/cas
.. _Connect2id: https://connect2id.com
.. _Gluu: https://gluu.org
.. _Hydra: https://ory.sh
.. _Keycloak: https://keycloak.org
.. _LemonLDAP: https://lemonldap-ng.org
.. _Okta: https://okta.com
