Comparison
==========

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
      - 16k
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
      - `✅ <https://auth0.com/docs/authenticate/protocols/openid-connect-protocol>`__
      - ✅
      - ❌
      - `✅ <https://auth0.com/docs/authenticate/protocols/scim>`__
      - `✅ <https://auth0.com/docs/authenticate/identity-providers/enterprise-identity-providers/active-directory-ldap>`__
      - ❔
    * - `Authelia <https://authelia.com>`_
      - ✅
      - `Go <https://golang.org/>`_
      - `185k <https://openhub.net/p/authelia/analyses/latest/languages_summary>`_
      - `✅ <https://www.authelia.com/configuration/identity-providers/openid-connect/provider/>`__
      - ❌
      - ❌
      - `❌ <https://github.com/authelia/authelia/issues/7668>`__
      - `✅ <https://www.authelia.com/configuration/first-factor/ldap/>`__
      - `✅ <https://www.authelia.com/configuration/storage/postgres/>`__
    * - `Authentic2 <https://dev.entrouvert.org/projects/authentic>`_
      - ✅
      - `Python <https://www.python.org/>`_
      - `121k <https://openhub.net/p/authentic2/analyses/latest/languages_summary>`_
      - `✅ <https://authentic2.readthedocs.io>`__
      - ✅
      - ✅
      - ❌
      - `✅ <https://authentic2.readthedocs.io/en/latest/>`__
      - `✅ <https://authentic2.readthedocs.io/en/latest/installation.html>`__
    * - `Authentik <https://goauthentik.io>`_
      - ✅
      - `Python <https://www.python.org/>`_
      - `440k <https://openhub.net/p/authentik/analyses/latest/languages_summary>`_
      - `✅ <https://docs.goauthentik.io/add-secure-apps/providers/oauth2>`__
      - ✅
      - ❌
      - `✅ <https://docs.goauthentik.io/add-secure-apps/providers/scim/>`__
      - `✅ <https://docs.goauthentik.io/add-secure-apps/providers/ldap/>`__
      - `✅ <https://docs.goauthentik.io/docs/core/architecture>`__
    * - `Authgear <https://authgear.com>`_
      - ✅
      - `Go <https://golang.org/>`_
      - 856k
      - `✅ <https://github.com/authgear/authgear-server>`__
      - `✅ <https://docs.authgear.com/get-started/single-sign-on-with-saml/saml-attribute-mapping>`__
      - ❌
      - ❌
      - `✅ <https://www.authgear.com/post/ldap-explained-a-comprehensive-guide-with-authgear-integration>`__
      - `✅ <https://github.com/authgear/authgear-server>`__
    * - `CAS <https://apereo.github.io/cas>`_
      - ✅
      - `Java <https://www.java.com/>`_
      - `900k <https://openhub.net/p/apereo-cas/analyses/latest/languages_summary>`_
      - `✅ <https://apereo.github.io/cas/development/authentication/OIDC-Authentication.html>`__
      - ✅
      - ✅
      - `✅ <https://apereo.github.io/cas/7.0.x/integration/SCIM-Provisioning.html>`__
      - `✅ <https://apereo.github.io/cas/development/authentication/LDAP-Authentication.html>`__
      - ❌
    * - `Connect2id <https://connect2id.com>`_
      - ❌
      - ❔
      - ❔
      - `✅ <https://connect2id.com/products/server/docs>`__
      - ✅
      - ❌
      - ❌
      - ✅
      - ✅
    * - `FusionAuth <https://fusionauth.io>`_
      - ❌
      - `Java <https://www.java.com/>`_
      - ❔
      - `✅ <https://fusionauth.io/docs/v1/tech/oauth/>`__
      - `✅ <https://fusionauth.io/docs/v1/tech/samlv2/>`__
      - ❌
      - `✅ <https://fusionauth.io/docs/lifecycle/migrate-users/scim/>`__
      - `✅ <https://fusionauth.io/docs/lifecycle/migrate-users/connectors/ldap-connector>`__
      - `✅ <https://fusionauth.io/docs/get-started/download-and-install/database>`__
    * - `Gluu <https://gluu.org>`_
      - ✅
      - `Java <https://www.java.com/>`_
      - `636k <https://openhub.net/p/gluu/analyses/latest/languages_summary>`_
      - `✅ <https://gluu.org/docs/gluu-server/4.0/admin-guide/openid-connect/>`__
      - ✅
      - ✅
      - `✅ <https://gluu.org/docs/gluu-server/4.1/user-management/scim2/>`__
      - `✅ <https://gluu.org/docs/gluu-server/4.0/reference/schema/>`__
      - ❔
    * - `Hydra <https://ory.sh>`_
      - ✅
      - `Go <https://golang.org/>`_
      - `119k <https://openhub.net/p/ory-hydra/analyses/latest/languages_summary>`_
      - `✅ <https://www.ory.sh/docs/hydra/concepts/openid-connect-oidc>`__
      - ✅
      - ❌
      - `❌ <https://github.com/ory/hydra/issues/320>`__
      - `✅ <https://github.com/i-core/werther>`__
      - `✅ <https://www.ory.sh/docs/hydra/self-hosted/dependencies-environment>`__
    * - `Kanidm <https://kanidm.com>`_
      - ✅
      - `Rust <https://www.rust-lang.org/>`_
      - 387k
      - `✅ <https://kanidm.github.io/kanidm/master/integrations/oauth2.html>`__
      - ❌
      - ❌
      - `🟠 <https://kanidm.github.io/kanidm/stable/supported_features.html>`__
      - `✅ <https://kanidm.github.io/kanidm/stable/integrations/ldap.html>`__
      - `✅ <https://kanidm.github.io/kanidm/stable/database_maintenance.html>`__
    * - `Keycloak <https://keycloak.org>`_
      - ✅
      - `Java <https://www.java.com/>`_
      - `1.1M <https://openhub.net/p/keycloak/analyses/latest/languages_summary>`_
      - `✅ <https://www.keycloak.org/securing-apps/oidc-layers>`__
      - ✅
      - ✅
      - `✅ <https://github.com/Captain-P-Goldfish/scim-for-keycloak>`__
      - `✅ <https://www.keycloak.org/docs/latest/server_admin/index.html>`__
      - `✅ <https://www.keycloak.org/server/db>`__
    * - `LemonLDAP <https://lemonldap-ng.org>`_
      - ✅
      - `Perl <https://www.perl.org/>`_
      - `410k <https://openhub.net/p/lemonldap-ng/analyses/latest/languages_summary>`_
      - `✅ <https://lemonldap-ng.org/documentation/2.0/idpopenidconnect.html>`__
      - ✅
      - ✅
      - `❌ <https://gitlab.ow2.org/lemonldap-ng/lemonldap-ng/-/issues/526>`__
      - `✅ <https://lemonldap-ng.org/documentation/2.0/authldap.html>`__
      - `✅ <https://lemonldap-ng.org/documentation/2.0/sqlconfbackend.html>`__
    * - `Logto <https://logto.io>`_
      - ✅
      - `TypeScript <https://www.typescriptlang.org/>`_
      - 387k
      - `✅ <https://docs.logto.io/>`__
      - `✅ <https://docs.logto.io/integrations/saml-sso>`__
      - ❌
      - ❌
      - `❌ <https://github.com/logto-io/logto/issues/1588>`__
      - `✅ <https://github.com/logto-io/logto>`__
    * - `node-oidc-provider <https://github.com/panva/node-oidc-provider>`_
      - ✅
      - `JavaScript <https://developer.mozilla.org/en-US/docs/Web/JavaScript>`_
      - `42k <https://openhub.net/p/node-oidc-provider>`_
      - `✅ <https://github.com/panva/node-oidc-provider>`__
      - ❌
      - ❌
      - ❌
      - `🟠 <https://github.com/EduID-Mobile/ldap-oidc-provider>`__
      - `🟠 <https://github.com/panva/node-oidc-provider/blob/main/docs/README.md#adapter>`__
    * - `Okta <https://okta.com>`_
      - ❌
      - ❔
      - ❔
      - `✅ <https://developer.okta.com/docs/reference/api/oidc/>`__
      - ✅
      - ❌
      - `✅ <https://developer.okta.com/docs/concepts/scim/>`__
      - `✅ <https://help.okta.com/en-us/content/topics/directory/ldap-interface-main.htm>`__
      - `✅ <https://help.okta.com/oag/en-us/content/topics/access-gateway/task-add-db-datastore.htm>`__
    * - `OpenIddict <https://openiddict.com>`_
      - ✅
      - `C# <https://docs.microsoft.com/en-us/dotnet/csharp/>`_
      - 265k
      - `✅ <https://documentation.openiddict.com/>`__
      - ❌
      - ❌
      - ❌
      - ❌
      - `✅ <https://documentation.openiddict.com/integrations/entity-framework-core>`__
    * - `SimpleIdServer <https://simpleidserver.com>`_
      - ✅
      - `C# <https://docs.microsoft.com/en-us/dotnet/csharp/>`_
      - 829k
      - `✅ <https://simpleidserver.com/docs/iam/openid/>`__
      - ❌
      - ❌
      - `✅ <https://simpleidserver.com/docs/scim/quickstart/>`__
      - ❌
      - `✅ <https://simpleidserver.com/docs/6.0.0/idserver/persistence/entityframework/>`__
    * - `SuperTokens <https://supertokens.com>`_
      - ✅
      - `Java <https://www.java.com/>`_
      - 451k
      - `✅ <https://supertokens.com/docs/authentication/social/custom-providers>`__
      - `✅ <https://supertokens.com/docs/thirdparty/common-customizations/saml/saml-login>`__
      - ❌
      - `✅ <https://github.com/supertokens/jackson-supertokens-express>`__
      - ❌
      - `✅ <https://supertokens.com/docs/deployment/self-host-supertokens>`__
    * - `WSO2 <https://wso2.com/identity-server/>`_
      - ✅
      - `Java <https://www.java.com/>`_
      - `1.4M <https://openhub.net/p/wso2-identity-server/analyses/latest/languages_summary>`_
      - `✅ <https://is.docs.wso2.com/en/6.0.0/references/concepts/authentication/intro-oidc/>`__
      - ✅
      - ❌
      - `✅ <https://is.docs.wso2.com/en/6.0.0/apis/scim2-rest-apis/>`__
      - `✅ <https://is.docs.wso2.com/en/7.0.0/guides/users/user-stores/primary-user-store/configure-a-read-write-ldap-user-store/>`__
      - `✅ <https://is.docs.wso2.com/en/7.0.0/deploy/configure/databases/>`__
    * - `Zitadel <https://zitadel.com>`_
      - ✅
      - `Go <https://golang.org/>`_
      - `760k <https://openhub.net/p/zitadel/analyses/latest/languages_summary>`_
      - `✅ <https://zitadel.com/docs/guides/integrate/login/oidc>`__
      - ✅
      - ❌
      - `✅ <https://zitadel.com/docs/apis/scim2>`__
      - ❌
      - `✅ <https://zitadel.com/docs/self-hosting/manage/database>`__
