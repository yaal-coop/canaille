Alternatives
============

Here is a feature comparison with other OpenID Connect server software.

Projects and protocols
----------------------

Canaille voluntarily only implements the OpenID Connect protocol to keep its codebase simple.

.. list-table::
    :header-rows: 1
    :widths: 25 10 15 8 10 8 8 8 8 8 8

    * - Software
      - FLOSS
      - Language
      - LOC
      - Binary Size
      - OIDC
      - SAML
      - CAS
      - SCIM
      - LDAP
      - SQL
    * - Canaille
      - ✅
      - `Python <https://www.python.org/>`_
      - 16k
      - ~15MB
      - ✅
      - ❎
      - ❎
      - 🟠
      - ✅
      - ✅
    * - `Auth0 <https://auth0.com>`_
      - ❌
      - ❔
      - ❔
      - N/A (Cloud)
      - `✅ <https://auth0.com/docs/authenticate/protocols/openid-connect-protocol>`__
      - ☑️
      - ❎
      - `✅ <https://auth0.com/docs/authenticate/protocols/scim>`__
      - `✅ <https://auth0.com/docs/authenticate/identity-providers/enterprise-identity-providers/active-directory-ldap>`__
      - ❔
    * - `Authelia <https://authelia.com>`_
      - ✅
      - `Go <https://golang.org/>`_
      - `185k <https://openhub.net/p/authelia/analyses/latest/languages_summary>`_
      - ~25MB
      - `✅ <https://www.authelia.com/configuration/identity-providers/openid-connect/provider/>`__
      - ❎
      - ❎
      - `❌ <https://github.com/authelia/authelia/issues/7668>`__
      - `✅ <https://www.authelia.com/configuration/first-factor/ldap/>`__
      - `✅ <https://www.authelia.com/configuration/storage/postgres/>`__
    * - `Authentic2 <https://dev.entrouvert.org/projects/authentic>`_
      - ✅
      - `Python <https://www.python.org/>`_
      - `121k <https://openhub.net/p/authentic2/analyses/latest/languages_summary>`_
      - ~20MB
      - `✅ <https://authentic2.readthedocs.io/en/latest/overview.html#oauth2-openid-connect>`__
      - ☑️
      - ☑️
      - ❌
      - ✅
      - `✅ <https://authentic2.readthedocs.io/en/latest/installation.html#database>`__
    * - `Authentik <https://goauthentik.io>`_
      - ✅
      - `Python <https://www.python.org/>`_
      - `440k <https://openhub.net/p/authentik/analyses/latest/languages_summary>`_
      - ~800MB (Docker)
      - `✅ <https://docs.goauthentik.io/add-secure-apps/providers/oauth2>`__
      - ☑️
      - ❎
      - `✅ <https://docs.goauthentik.io/add-secure-apps/providers/scim/>`__
      - `✅ <https://docs.goauthentik.io/add-secure-apps/providers/ldap/>`__
      - `✅ <https://docs.goauthentik.io/core/architecture>`__
    * - `Authgear <https://authgear.com>`_
      - ✅
      - `Go <https://golang.org/>`_
      - 856k
      - ~50MB
      - ✅
      - `☑️ <https://docs.authgear.com/get-started/single-sign-on-with-saml/saml-attribute-mapping>`__
      - ❎
      - ❌
      - `✅ <https://www.authgear.com/post/ldap-explained-a-comprehensive-guide-with-authgear-integration>`__
      - ✅
    * - `CAS <https://apereo.github.io/cas>`_
      - ✅
      - `Java <https://www.java.com/>`_
      - `900k <https://openhub.net/p/apereo-cas/analyses/latest/languages_summary>`_
      - ~150MB (WAR)
      - `✅ <https://apereo.github.io/cas/development/authentication/OIDC-Authentication.html>`__
      - ☑️
      - ☑️
      - ✅
      - `✅ <https://apereo.github.io/cas/development/authentication/LDAP-Authentication.html>`__
      - ❌
    * - `Connect2id <https://connect2id.com>`_
      - ❌
      - ❔
      - ❔
      - ~80MB (JAR)
      - `✅ <https://connect2id.com/products/server/docs/api/authorization>`__
      - ☑️
      - ❎
      - ❌
      - ✅
      - ✅
    * - `FusionAuth <https://fusionauth.io>`_
      - ❌
      - `Java <https://www.java.com/>`_
      - ❔
      - ~200MB (ZIP)
      - `✅ <https://fusionauth.io/docs/v1/tech/oauth/>`__
      - `☑️ <https://fusionauth.io/docs/v1/tech/samlv2/>`__
      - ❎
      - `✅ <https://fusionauth.io/docs/lifecycle/migrate-users/scim/>`__
      - `✅ <https://fusionauth.io/docs/lifecycle/migrate-users/connectors/ldap-connector>`__
      - `✅ <https://fusionauth.io/docs/get-started/download-and-install/database>`__
    * - `Gluu <https://gluu.org>`_
      - ✅
      - `Java <https://www.java.com/>`_
      - `636k <https://openhub.net/p/gluu/analyses/latest/languages_summary>`_
      - ~2GB (Container)
      - `✅ <https://gluu.org/docs/gluu-server/4.0/admin-guide/openid-connect/>`__
      - ☑️
      - ☑️
      - `✅ <https://gluu.org/docs/gluu-server/4.1/user-management/scim2/>`__
      - `✅ <https://gluu.org/docs/gluu-server/4.0/reference/schema/>`__
      - ✅
    * - `Hydra + Kratos <https://ory.sh>`_
      - ✅
      - `Go <https://golang.org/>`_
      - `119k <https://openhub.net/p/ory-hydra/analyses/latest/languages_summary>`_
      - ~40MB (2 binaries)
      - `✅ <https://www.ory.sh/docs/hydra/concepts/openid-connect-oidc>`__
      - ☑️
      - ❎
      - `❌ <https://github.com/ory/hydra/issues/320>`__
      - `✅ <https://www.ory.sh/docs/kratos/>`__
      - `✅ <https://www.ory.sh/docs/hydra/self-hosted/dependencies-environment>`__
    * - `Kanidm <https://kanidm.com>`_
      - ✅
      - `Rust <https://www.rust-lang.org/>`_
      - 387k
      - ~30MB
      - `✅ <https://kanidm.github.io/kanidm/master/integrations/oauth2.html>`__
      - ❎
      - ❎
      - `🟠 <https://kanidm.github.io/kanidm/stable/supported_features.html>`__
      - `✅ <https://kanidm.github.io/kanidm/stable/integrations/ldap.html>`__
      - `✅ <https://kanidm.github.io/kanidm/stable/database_maintenance.html>`__
    * - `Keycloak <https://keycloak.org>`_
      - ✅
      - `Java <https://www.java.com/>`_
      - `1.1M <https://openhub.net/p/keycloak/analyses/latest/languages_summary>`_
      - ~250MB (JAR)
      - `✅ <https://www.keycloak.org/securing-apps/oidc-layers>`__
      - ☑️
      - ☑️
      - `✅ <https://github.com/Captain-P-Goldfish/scim-for-keycloak>`__
      - `✅ <https://www.keycloak.org/docs/latest/server_admin/index.html>`__
      - `✅ <https://www.keycloak.org/server/db>`__
    * - `LemonLDAP <https://lemonldap-ng.org>`_
      - ✅
      - `Perl <https://www.perl.org/>`_
      - `410k <https://openhub.net/p/lemonldap-ng/analyses/latest/languages_summary>`_
      - ~50MB (Package)
      - `✅ <https://lemonldap-ng.org/documentation/2.0/idpopenidconnect.html>`__
      - ☑️
      - ☑️
      - `❌ <https://gitlab.ow2.org/lemonldap-ng/lemonldap-ng/-/issues/526>`__
      - `✅ <https://lemonldap-ng.org/documentation/2.0/authldap.html>`__
      - `✅ <https://lemonldap-ng.org/documentation/2.0/sqlconfbackend.html>`__
    * - `Logto <https://logto.io>`_
      - ✅
      - `TypeScript <https://www.typescriptlang.org/>`_
      - 387k
      - ~100MB (Docker)
      - ✅
      - `☑️ <https://docs.logto.io/integrations/saml-sso>`__
      - ❎
      - ❌
      - `❌ <https://github.com/logto-io/logto/issues/1588>`__
      - ✅
    * - `Okta <https://okta.com>`_
      - ❌
      - ❔
      - ❔
      - N/A (Cloud)
      - `✅ <https://developer.okta.com/docs/reference/api/oidc/>`__
      - ☑️
      - ❎
      - `✅ <https://developer.okta.com/docs/concepts/scim/>`__
      - `✅ <https://help.okta.com/en-us/content/topics/directory/ldap-interface-main.htm>`__
      - `✅ <https://help.okta.com/oag/en-us/content/topics/access-gateway/task-add-db-datastore.htm>`__
    * - `SimpleIdServer <https://simpleidserver.com>`_
      - ✅
      - `C# <https://docs.microsoft.com/en-us/dotnet/csharp/>`_
      - 829k
      - ~120MB (.NET)
      - `✅ <https://simpleidserver.com/docs/iam/openid/>`__
      - ❎
      - ❎
      - `✅ <https://simpleidserver.com/docs/scim/quickstart/>`__
      - ❌
      - `✅ <https://simpleidserver.com/docs/6.0.0/idserver/persistence/entityframework/>`__
    * - `SuperTokens <https://supertokens.com>`_
      - ✅
      - `Java <https://www.java.com/>`_
      - 451k
      - ~100MB (JAR)
      - `✅ <https://supertokens.com/docs/authentication/social/custom-providers>`__
      - `☑️ <https://supertokens.com/docs/thirdparty/common-customizations/saml/saml-login>`__
      - ❎
      - ✅
      - ❌
      - `✅ <https://supertokens.com/docs/deployment/self-host-supertokens>`__
    * - `WSO2 <https://wso2.com/identity-server/>`_
      - ✅
      - `Java <https://www.java.com/>`_
      - `1.4M <https://openhub.net/p/wso2-identity-server/analyses/latest/languages_summary>`_
      - ~500MB (ZIP)
      - `✅ <https://is.docs.wso2.com/en/6.0.0/references/concepts/authentication/intro-oidc/>`__
      - ☑️
      - ❎
      - `✅ <https://is.docs.wso2.com/en/6.0.0/apis/scim2-rest-apis/>`__
      - `✅ <https://is.docs.wso2.com/en/7.0.0/guides/users/user-stores/primary-user-store/configure-a-read-write-ldap-user-store/>`__
      - `✅ <https://is.docs.wso2.com/en/7.0.0/deploy/configure/databases/>`__
    * - `Zitadel <https://zitadel.com>`_
      - ✅
      - `Go <https://golang.org/>`_
      - `760k <https://openhub.net/p/zitadel/analyses/latest/languages_summary>`_
      - ~60MB
      - `✅ <https://zitadel.com/docs/guides/integrate/login/oidc>`__
      - ☑️
      - ❎
      - `✅ <https://zitadel.com/docs/apis/scim2>`__
      - ❌
      - `✅ <https://zitadel.com/docs/self-hosting/manage/database>`__

Authentication Methods
----------------------

Here is the support for the most common authentication methods.

.. list-table::
    :header-rows: 1
    :widths: 25 10 10 10 10 10 10

    * - Software
      - Password
      - TOTP
      - HOTP
      - SMS
      - Email
      - WebAuthn
    * - Canaille
      - `✅ <../features.html#user-authentication>`__
      - `✅ <../features.html#multi-factor-authentication>`__
      - `✅ <../features.html#multi-factor-authentication>`__
      - `✅ <../features.html#multi-factor-authentication>`__
      - `✅ <../features.html#multi-factor-authentication>`__
      - ❌
    * - `Auth0 <https://auth0.com>`_
      - `✅ <https://auth0.com/docs/authenticate/login/auth0-universal-login>`__
      - `✅ <https://auth0.com/docs/secure/multi-factor-authentication/authenticate-using-ropg-flow-with-mfa/enroll-and-challenge-otp-authenticators>`__
      - `✅ <https://auth0.com/blog/what-is-a-one-time-password-otp/>`__
      - `✅ <https://auth0.com/docs/authenticate/passwordless>`__
      - `✅ <https://auth0.com/docs/authenticate/passwordless>`__
      - `✅ <https://auth0.com/docs/secure/multi-factor-authentication>`__
    * - `Authelia <https://authelia.com>`_
      - `✅ <https://www.authelia.com/configuration/first-factor/>`__
      - `✅ <https://www.authelia.com/configuration/second-factor/time-based-one-time-password/>`__
      - ❌
      - ❌
      - 🟠
      - `✅ <https://www.authelia.com/overview/authentication/security-key/>`__
    * - `Authentic2 <https://dev.entrouvert.org/projects/authentic>`_
      - `✅ <https://authentic2.readthedocs.io/en/latest/overview.html#authentication>`__
      - ✅
      - ✅
      - ✅
      - ✅
      - ❌
    * - `Authentik <https://goauthentik.io>`_
      - ✅
      - ✅
      - ❌
      - ✅
      - ✅
      - ✅
    * - `Authgear <https://authgear.com>`_
      - `✅ <https://www.authgear.com/post/top-three-types-of-user-authentication-methods>`__
      - `✅ <https://www.authgear.com/post/what-is-totp>`__
      - `❌ <https://www.authgear.com/post/what-is-totp>`__
      - `✅ <https://www.authgear.com/post/sms-otp-vulnerabilities-and-alternatives>`__
      - `✅ <https://www.authgear.com/post/top-three-types-of-user-authentication-methods>`__
      - `✅ <https://www.authgear.com/post/top-three-types-of-user-authentication-methods>`__
    * - `CAS <https://apereo.github.io/cas>`_
      - ✅
      - `✅ <https://apereo.github.io/cas/development/mfa/Configuring-Multifactor-Authentication.html>`__
      - `✅ <https://apereo.github.io/cas/development/mfa/Configuring-Multifactor-Authentication.html>`__
      - `✅ <https://apereo.github.io/cas/development/authentication/Passwordless-Authentication.html>`__
      - `✅ <https://apereo.github.io/cas/development/authentication/Passwordless-Authentication.html>`__
      - `✅ <https://apereo.github.io/cas/development/mfa/Configuring-Multifactor-Authentication.html>`__
    * - `Connect2id <https://connect2id.com>`_
      - `🟠 <https://connect2id.com/products/server/user-authentication>`__
      - 🟠
      - 🟠
      - 🟠
      - 🟠
      - 🟠
    * - `FusionAuth <https://fusionauth.io>`_
      - `✅ <https://fusionauth.io/docs/lifecycle/authenticate-users/>`__
      - `✅ <https://fusionauth.io/articles/security/time-based-one-time-passwords-totp>`__
      - ❌
      - `✅ <https://fusionauth.io/docs/lifecycle/authenticate-users/multi-factor-authentication>`__
      - `✅ <https://fusionauth.io/docs/lifecycle/authenticate-users/multi-factor-authentication>`__
      - `✅ <https://fusionauth.io/docs/lifecycle/authenticate-users/multi-factor-authentication>`__
    * - `Gluu <https://gluu.org>`_
      - ✅
      - `✅ <https://gluu.org/docs/gluu-server/4.1/authn-guide/otp/>`__
      - `✅ <https://gluu.org/docs/gluu-server/4.1/authn-guide/otp/>`__
      - `✅ <https://gluu.org/docs/gluu-server/3.1.1/authn-guide/sms-otp/>`__
      - ✅
      - `✅ <https://gluu.org/docs/gluu-server/4.1/authn-guide/fido2/>`__
    * - `Hydra + Kratos <https://ory.sh>`_
      - `✅ <https://www.ory.sh/docs/kratos/>`__
      - `✅ <https://www.ory.sh/docs/kratos/mfa/totp>`__
      - ❌
      - `✅ <https://www.ory.sh/docs/kratos/mfa/mfa-via-sms>`__
      - `✅ <https://www.ory.sh/docs/kratos/passwordless/one-time-code>`__
      - `✅ <https://www.ory.sh/docs/kratos/mfa/overview>`__
    * - `Kanidm <https://kanidm.com>`_
      - ✅
      - ✅
      - ❌
      - ❌
      - ❌
      - ✅
    * - `Keycloak <https://keycloak.org>`_
      - ✅
      - ✅
      - ✅
      - `🟠 <https://medium.com/@shreyasmk.mathur/mastering-multi-factor-authentication-in-keycloak-sms-email-and-totp-setup-guide-957305b92be1>`__
      - `🟠 <https://medium.com/@mesutpiskin/two-factor-authentication-via-email-in-keycloak-custom-auth-spi-935bbb3952a8>`__
      - ✅
    * - `LemonLDAP <https://lemonldap-ng.org>`_
      - `✅ <https://lemonldap-ng.org/documentation/2.0/secondfactor.html>`__
      - `✅ <https://lemonldap-ng.org/documentation/2.0/totp2f.html>`__
      - `❌ <https://lemonldap-ng.org/documentation/2.0/totp2f.html>`__
      - `✅ <https://lemonldap-ng.org/documentation/2.0/external2f.html>`__
      - `✅ <https://lemonldap-ng.org/documentation/2.0/secondfactor.html>`__
      - `✅ <https://lemonldap-ng.org/documentation/2.0/webauthn2f.html>`__
    * - `Logto <https://logto.io>`_
      - ✅
      - `✅ <https://docs.logto.io/end-user-flows/mfa>`__
      - ❌
      - `✅ <https://logto.io/products/passwordless>`__
      - `✅ <https://logto.io/products/passwordless>`__
      - `✅ <https://logto.io/products/passwordless>`__
    * - `Okta <https://okta.com>`_
      - `✅ <https://developer.okta.com/docs/reference/api/authn/>`__
      - `✅ <https://help.okta.com/en-us/content/topics/security/mfa-totp-seed.htm>`__
      - `✅ <https://developer.okta.com/docs/api/openapi/okta-management/management/tag/UserFactor/>`__
      - `✅ <https://developer.okta.com/docs/api/openapi/okta-management/management/tag/UserFactor/>`__
      - `✅ <https://developer.okta.com/docs/api/openapi/okta-management/management/tag/UserFactor/>`__
      - `✅ <https://developer.okta.com/docs/guides/authenticators-web-authn/>`__
    * - `SimpleIdServer <https://simpleidserver.com>`_
      - `✅ <https://simpleidserver.com/docs/idserver/quickstart/createidserverwithui/>`__
      - `✅ <https://simpleidserver.com/docs/userguide/authentication/forms/>`__
      - `✅ <https://simpleidserver.com/docs/userguide/authentication/forms/>`__
      - `✅ <https://simpleidserver.com/docs/userguide/authentication/forms/>`__
      - `✅ <https://simpleidserver.com/docs/userguide/authentication/forms/>`__
      - `✅ <https://simpleidserver.com/docs/userguide/authentication/forms/>`__
    * - `SuperTokens <https://supertokens.com>`_
      - `✅ <https://supertokens.com/docs/authentication/>`__
      - `✅ <https://supertokens.com/docs/additional-verification/mfa/totp/totp-for-all-users>`__
      - ❌
      - ✅
      - ✅
      - `✅ <https://supertokens.com/blog/phishing-resistant-mfa>`__
    * - `WSO2 <https://wso2.com/identity-server/>`_
      - ✅
      - `✅ <https://is.docs.wso2.com/en/7.0.0/guides/authentication/mfa/add-totp-login/>`__
      - ❌
      - `✅ <https://is.docs.wso2.com/en/6.0.0/guides/mfa/2fa-sms-otp/>`__
      - `✅ <https://is.docs.wso2.com/en/6.0.0/guides/mfa/2fa-totp/>`__
      - `✅ <https://is.docs.wso2.com/en/7.0.0/guides/authentication/mfa/>`__
    * - `Zitadel <https://zitadel.com>`_
      - ✅
      - `✅ <https://zitadel.com/docs/guides/integrate/login-ui/mfa>`__
      - ❌
      - `🟠 <https://zitadel.com/blog/authentication-methods>`__
      - `✅ <https://zitadel.com/docs/guides/integrate/login-ui/mfa>`__
      - `✅ <https://zitadel.com/docs/concepts/features/passkeys>`__

OAuth2/OIDC Specifications Compatibility
----------------------------------------

.. list-table::
    :header-rows: 1
    :widths: 25 6 6 6 6 6 6 6 6 6 6 6 6 6

    * - Software
      - `Token Revocation <https://tools.ietf.org/html/rfc7009>`_
      - `Dynamic Registration <https://tools.ietf.org/html/rfc7591>`_
      - `Dynamic Management <https://tools.ietf.org/html/rfc7592>`_
      - `PKCE <https://tools.ietf.org/html/rfc7636>`_
      - `Token Introspection <https://tools.ietf.org/html/rfc7662>`_
      - `Discovery <https://tools.ietf.org/html/rfc8414>`_
      - `Device Flow <https://tools.ietf.org/html/rfc8628>`_
      - `Token Exchange <https://tools.ietf.org/html/rfc8693>`_
      - `MTLS <https://tools.ietf.org/html/rfc8705>`_
      - `JAR <https://tools.ietf.org/html/rfc9101>`_
      - `PAR <https://tools.ietf.org/html/rfc9126>`_
      - `RAR <https://tools.ietf.org/html/rfc9396>`_
      - `DPoP <https://tools.ietf.org/html/rfc9449>`_
    * - Canaille
      - `✅ <../development/specifications.html>`__
      - `✅ <../development/specifications.html>`__
      - `✅ <../development/specifications.html>`__
      - `✅ <../development/specifications.html>`__
      - `✅ <../development/specifications.html>`__
      - `✅ <../development/specifications.html>`__
      - ❌
      - ❌
      - ❌
      - `✅ <../development/specifications.html>`__
      - ❌
      - ❌
      - ❌
    * - `Auth0 <https://auth0.com>`_
      - `✅ <https://auth0.com/docs/secure/tokens/access-tokens/revoke-access-tokens>`__
      - `✅ <https://auth0.com/docs/get-started/applications/dynamic-client-registration>`__
      - ❌
      - `✅ <https://auth0.com/docs/get-started/authentication-and-authorization-flow/authorization-code-flow-with-pkce>`__
      - ❌
      - ✅
      - `✅ <https://auth0.com/docs/get-started/authentication-and-authorization-flow/device-authorization-flow>`__
      - ❌
      - `✅ <https://auth0.com/docs/get-started/applications/machine-to-machine-applications/certificate-credentials>`__
      - `✅ <https://auth0.com/docs/secure/attack-protection/request-object>`__
      - `✅ <https://auth0.com/docs/get-started/authentication-and-authorization-flow/pushed-authorization-requests>`__
      - `✅ <https://auth0.com/docs/get-started/authentication-and-authorization-flow/authorization-code-flow/authorization-code-flow-with-rar>`__
      - ❌
    * - `Authelia <https://authelia.com>`_
      - `✅ <https://www.authelia.com/integration/openid-connect/introduction/#support-chart>`__
      - ❌
      - ❌
      - `✅ <https://www.authelia.com/integration/openid-connect/introduction/#support-chart>`__
      - `✅ <https://www.authelia.com/integration/openid-connect/introduction/#support-chart>`__
      - `✅ <https://www.authelia.com/integration/openid-connect/introduction/#support-chart>`__
      - `✅ <https://www.authelia.com/integration/openid-connect/introduction/#support-chart>`__
      - ❌
      - ❌
      - `🟠 <https://www.authelia.com/integration/openid-connect/introduction/#support-chart>`__
      - `✅ <https://www.authelia.com/integration/openid-connect/introduction/#support-chart>`__
      - ❌
      - ❌
    * - `Authentic2 <https://dev.entrouvert.org/projects/authentic>`_
      - ✅
      - ✅
      - ❌
      - ✅
      - ✅
      - ✅
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Authentik <https://goauthentik.io>`_
      - ✅
      - `✅ <https://docs.goauthentik.io/add-secure-apps/providers/oauth2/>`__
      - ❌
      - `✅ <https://docs.goauthentik.io/add-secure-apps/providers/oauth2/>`__
      - ✅
      - `✅ <https://docs.goauthentik.io/add-secure-apps/providers/oauth2/>`__
      - `✅ <https://docs.goauthentik.io/add-secure-apps/providers/oauth2/device_flow>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Authgear <https://authgear.com>`_
      - ✅
      - ✅
      - ✅
      - ✅
      - ❌
      - ✅
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `CAS <https://apereo.github.io/cas>`_
      - `✅ <https://apereo.github.io/cas/development/authentication/OIDC-Authentication.html>`__
      - `✅ <https://apereo.github.io/cas/development/authentication/OIDC-Authentication.html>`__
      - ❌
      - `✅ <https://apereo.github.io/cas/development/authentication/OIDC-Authentication.html>`__
      - `✅ <https://apereo.github.io/cas/development/authentication/OIDC-Authentication.html>`__
      - `✅ <https://apereo.github.io/cas/development/authentication/OIDC-Authentication.html>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Connect2id <https://connect2id.com>`_
      - `✅ <https://connect2id.com/products/server/docs>`__
      - `✅ <https://connect2id.com/products/server/docs>`__
      - `✅ <https://connect2id.com/products/server/docs>`__
      - `✅ <https://connect2id.com/products/server/docs>`__
      - `✅ <https://connect2id.com/products/server/docs>`__
      - `✅ <https://connect2id.com/products/server/docs>`__
      - `✅ <https://connect2id.com/products/server/docs>`__
      - `✅ <https://connect2id.com/products/server/docs>`__
      - `✅ <https://connect2id.com/products/server/docs>`__
      - `✅ <https://connect2id.com/products/server/docs>`__
      - `✅ <https://connect2id.com/products/server/docs>`__
      - ❌
      - `✅ <https://connect2id.com/products/server/docs>`__
    * - `FusionAuth <https://fusionauth.io>`_
      - ❌
      - ❌
      - ❌
      - `✅ <https://fusionauth.io/docs/v1/tech/oauth/>`__
      - ❌
      - `✅ <https://fusionauth.io/docs/v1/tech/oauth/>`__
      - `✅ <https://fusionauth.io/docs/v1/tech/oauth/>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Gluu <https://gluu.org>`_
      - ✅
      - ✅
      - ✅
      - `✅ <https://gluu.org/docs/gluu-server/4.0/admin-guide/openid-connect/>`__
      - `✅ <https://gluu.org/docs/gluu-server/4.1/admin-guide/openid-connect/>`__
      - `✅ <https://gluu.org/docs/gluu-server/4.0/admin-guide/openid-connect/>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Hydra + Kratos <https://ory.sh>`_
      - `✅ <https://www.ory.sh/docs/hydra/guides/token-revocation>`__
      - ❌
      - ❌
      - `✅ <https://www.ory.sh/docs/hydra/concepts/oauth2#proof-key-for-code-exchange-pkce>`__
      - `✅ <https://www.ory.sh/docs/hydra/guides/token-introspection>`__
      - `✅ <https://www.ory.sh/docs/hydra/reference/api>`__
      - `✅ <https://www.ory.sh/docs/hydra/guides/device-authorization-grant>`__
      - ❌
      - `✅ <https://www.ory.sh/docs/hydra/guides/oauth2-client-authentication#jwt-client-authentication>`__
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Kanidm <https://kanidm.com>`_
      - ✅
      - ✅
      - ❌
      - `✅ <https://kanidm.github.io/kanidm/master/integrations/oauth2.html>`__
      - ❌
      - `✅ <https://kanidm.github.io/kanidm/master/integrations/oauth2.html>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Keycloak <https://keycloak.org>`_
      - `✅ <https://www.keycloak.org/securing-apps/specifications>`__
      - `✅ <https://www.keycloak.org/securing-apps/specifications>`__
      - `✅ <https://www.keycloak.org/securing-apps/specifications>`__
      - `✅ <https://www.keycloak.org/securing-apps/specifications>`__
      - `✅ <https://www.keycloak.org/securing-apps/specifications>`__
      - `✅ <https://www.keycloak.org/securing-apps/specifications>`__
      - `✅ <https://www.keycloak.org/securing-apps/specifications>`__
      - `✅ <https://www.keycloak.org/securing-apps/specifications>`__
      - `✅ <https://www.keycloak.org/securing-apps/specifications>`__
      - `✅ <https://www.keycloak.org/securing-apps/specifications>`__
      - `✅ <https://www.keycloak.org/securing-apps/specifications>`__
      - ❌
      - `🟠 <https://www.keycloak.org/securing-apps/specifications>`__
    * - `LemonLDAP <https://lemonldap-ng.org>`_
      - ✅
      - `✅ <https://lemonldap-ng.org/documentation/2.0/idpopenidconnect.html>`__
      - ❌
      - `✅ <https://lemonldap-ng.org/documentation/2.0/idpopenidconnect.html>`__
      - ✅
      - `✅ <https://lemonldap-ng.org/documentation/2.0/idpopenidconnect.html>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Logto <https://logto.io>`_
      - ✅
      - `✅ <https://docs.logto.io/integrations/vanilla-js/>`__
      - ❌
      - `✅ <https://docs.logto.io/docs/recipes/protect-your-api/>`__
      - ✅
      - `✅ <https://docs.logto.io/docs/recipes/protect-your-api/>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Okta <https://okta.com>`_
      - `✅ <https://developer.okta.com/docs/reference/api/oidc/#revoke>`__
      - ❌
      - ❌
      - `✅ <https://developer.okta.com/docs/guides/implement-grant-type/authcodepkce/main/>`__
      - `✅ <https://developer.okta.com/docs/reference/api/oidc/#introspect>`__
      - `✅ <https://developer.okta.com/docs/reference/api/oidc/#well-known-openid-configuration>`__
      - `✅ <https://developer.okta.com/docs/guides/device-authorization-grant/main/>`__
      - `✅ <https://developer.okta.com/docs/guides/token-exchange/main/>`__
      - ❌
      - `✅ <https://developer.okta.com/docs/reference/api/oidc/>`__
      - `✅ <https://developer.okta.com/docs/reference/api/oidc/>`__
      - `✅ <https://developer.okta.com/docs/reference/api/oidc/>`__
      - `✅ <https://developer.okta.com/docs/guides/dpop/main/>`__
    * - `SimpleIdServer <https://simpleidserver.com>`_
      - ✅
      - ✅
      - ❌
      - `✅ <https://simpleidserver.com/documentation/simpleidserver/configuration/clients>`__
      - ✅
      - `✅ <https://simpleidserver.com/documentation/simpleidserver/configuration/clients>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `SuperTokens <https://supertokens.com>`_
      - ✅
      - `✅ <https://supertokens.com/docs/authentication/social/custom-providers>`__
      - ❌
      - `✅ <https://supertokens.com/docs/thirdpartyemailpassword/common-customizations/core/api-keys>`__
      - ✅
      - `✅ <https://supertokens.com/docs/authentication/social/custom-providers>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `WSO2 <https://wso2.com/identity-server/>`_
      - `✅ <https://is.docs.wso2.com/en/7.0.0/apis/oauth2-token-revocation-endpoint/>`__
      - `✅ <https://is.docs.wso2.com/en/6.0.0/references/concepts/authentication/intro-oidc/>`__
      - ❌
      - `✅ <https://is.docs.wso2.com/en/6.0.0/references/concepts/authentication/intro-oidc/>`__
      - `✅ <https://is.docs.wso2.com/en/7.0.0/apis/oauth2-token-introspection-endpoint/>`__
      - `✅ <https://is.docs.wso2.com/en/6.0.0/references/concepts/authentication/intro-oidc/>`__
      - `✅ <https://is.docs.wso2.com/en/7.0.0/guides/access-delegation/device-flow/>`__
      - ❌
      - `✅ <https://is.docs.wso2.com/en/7.0.0/guides/access-delegation/oauth-mtls/>`__
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Zitadel <https://zitadel.com>`_
      - `✅ <https://zitadel.com/docs/apis/openidoauth/endpoints#revoke-token>`__
      - `✅ <https://zitadel.com/docs/guides/integrate/login/oidc>`__
      - ❌
      - `✅ <https://zitadel.com/docs/guides/integrate/login/oidc>`__
      - `✅ <https://zitadel.com/docs/apis/openidoauth/endpoints#introspect-token>`__
      - `✅ <https://zitadel.com/docs/apis/openidoauth/endpoints>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌


OpenID Connect Advanced Features
--------------------------------

.. list-table::
    :header-rows: 1
    :widths: 25 8 8 8 8 8 8 8 8 8 8

    * - Software
      - `OIDC Discovery <https://openid.net/specs/openid-connect-discovery-1_0.html>`_
      - `Dynamic Registration <https://openid.net/specs/openid-connect-registration-1_0.html>`__
      - `RP-Initiated Logout <https://openid.net/specs/openid-connect-rpinitiated-1_0.html>`_
      - `Session Management <https://openid.net/specs/openid-connect-session-1_0.html>`_
      - `Front-Channel Logout <https://openid.net/specs/openid-connect-frontchannel-1_0.html>`_
      - `Back-Channel Logout <https://openid.net/specs/openid-connect-backchannel-1_0.html>`_
      - `CIBA <https://openid.net/specs/openid-client-initiated-backchannel-authentication-core-1_0.html>`_
      - `Prompt=create <https://openid.net/specs/openid-connect-prompt-create-1_0.html>`_
      - `Self-Issued OP <https://openid.net/specs/openid-connect-self-issued-v2-1_0.html>`_
      - `Federation <https://openid.net/specs/openid-federation-1_0.html>`_
    * - Canaille
      - `✅ <../development/specifications.html>`__
      - `✅ <../development/specifications.html>`__
      - `✅ <../development/specifications.html>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - `✅ <../development/specifications.html>`__
      - ❌
      - ❌
    * - `Auth0 <https://auth0.com>`_
      - ✅
      - `✅ <https://auth0.com/docs/get-started/applications/application-types>`__
      - `✅ <https://auth0.com/docs/authenticate/login/logout/log-users-out-of-auth0>`__
      - ❌
      - ❌
      - `✅ <https://auth0.com/docs/authenticate/login/logout/back-channel-logout>`__
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Authelia <https://authelia.com>`_
      - ❌
      - `✅ <https://www.authelia.com/configuration/identity-providers/openid-connect/provider/>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Authentic2 <https://dev.entrouvert.org/projects/authentic>`_
      - ❌
      - ✅
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Authentik <https://goauthentik.io>`_
      - ❌
      - `✅ <https://docs.goauthentik.io/add-secure-apps/providers/oauth2/>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Authgear <https://authgear.com>`_
      - ❌
      - ✅
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `CAS <https://apereo.github.io/cas>`_
      - ❌
      - `✅ <https://apereo.github.io/cas/development/authentication/OIDC-Authentication.html>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Connect2id <https://connect2id.com>`_
      - ✅
      - `✅ <https://connect2id.com/products/server/docs/api/client-registration>`__
      - `✅ <https://connect2id.com/products/server/docs/guides/logout>`__
      - `✅ <https://connect2id.com/products/server/docs/guides/session-management>`__
      - `✅ <https://connect2id.com/products/server/docs/guides/logout>`__
      - `✅ <https://connect2id.com/products/server/docs/guides/logout>`__
      - `✅ <https://connect2id.com/products/server/docs/guides/ciba>`__
      - ❌
      - ❌
      - ❌
    * - `FusionAuth <https://fusionauth.io>`_
      - ❌
      - `✅ <https://fusionauth.io/docs/v1/tech/oauth/>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Gluu <https://gluu.org>`_
      - ✅
      - ✅
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Hydra + Kratos <https://ory.sh>`_
      - `✅ <https://www.ory.sh/docs/hydra/guides/oauth2-clients#dynamic-client-registration>`__
      - `✅ <https://www.ory.sh/docs/hydra/guides/logout>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Kanidm <https://kanidm.com>`_
      - ❌
      - ✅
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Keycloak <https://keycloak.org>`_
      - ✅
      - `✅ <https://www.keycloak.org/docs/latest/server_admin/index.html#_client-registration>`__
      - `✅ <https://www.keycloak.org/docs/latest/server_admin/index.html#_oidc-logout>`__
      - `✅ <https://www.keycloak.org/docs/latest/server_admin/index.html#_oidc-logout>`__
      - `✅ <https://www.keycloak.org/docs/latest/server_admin/index.html#_oidc-logout>`__
      - `✅ <https://www.keycloak.org/docs/latest/server_admin/index.html#_oidc-logout>`__
      - ❌
      - ❌
      - ❌
      - ❌
    * - `LemonLDAP <https://lemonldap-ng.org>`_
      - ❌
      - `✅ <https://lemonldap-ng.org/documentation/2.0/idpopenidconnect.html>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Logto <https://logto.io>`_
      - ❌
      - ✅
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Okta <https://okta.com>`_
      - `✅ <https://developer.okta.com/docs/reference/api/apps/#add-oauth-2-0-client-application>`__
      - `✅ <https://developer.okta.com/docs/reference/api/oidc/#logout>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `SimpleIdServer <https://simpleidserver.com>`_
      - ✅
      - ✅
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `SuperTokens <https://supertokens.com>`_
      - ❌
      - `✅ <https://supertokens.com/docs/authentication/social/custom-providers>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `WSO2 <https://wso2.com/identity-server/>`_
      - `✅ <https://is.docs.wso2.com/en/7.0.0/guides/applications/register-oidc-web-app/>`__
      - `✅ <https://is.docs.wso2.com/en/7.0.0/guides/authentication/oidc/add-logout/>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
    * - `Zitadel <https://zitadel.com>`_
      - ❌
      - `✅ <https://zitadel.com/docs/guides/integrate/login/oidc>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
      - ❌
