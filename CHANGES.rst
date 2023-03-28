All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

Added
*****

- Organization field. :pr:`116`
- ETag and Last-Modified headers on user photos. :pr:`116`

Changed
*******

- UX rework. Submenu addition. :pr:`114`
- Properly handle LDAP date timezones. :pr:`117`

Fixed
*****

- CSRF protection on every forms. :pr:`119`

[0.0.22] - 2023-03-13
=====================

Fixed
*****
- faker is not imported anymore when the `clean` command is called.

[0.0.21] - 2023-03-12
=====================

Added
*****

- Display TOS and policy URI on the consent list page. :pr:`102`
- Admin token deletion :pr:`100` :pr:`101`
- Revoked consents can be restored. :pr:`103`
- Pre-consented clients are displayed in the user consent list,
  and their consents can be revoked. :issue:`69` :pr:`103`
- A ``populate`` command can be used to fill the database with
  random users generated with faker. :pr:`105`
- SMTP SSL support. :pr:`108`
- Server side pagination. :issue:`114` :pr:`111`
- Department number support. :issue:`129`
- Address edition support (but not in the OIDC claims yet) :pr:`112`
- Title edition support :pr:`113`

Fixed
*****

- Client deletion also deletes related Consent, Token and
  AuthorizationCode objects. :issue:`126` :pr:`98`

Changed
*******

- Removed datatables.

[0.0.20] - 2023-01-28
=====================

Added
*****

- Spanish translation. :pr:`85` :pr:`88`
- Dedicated connectivity test email :pr:`89`
- Update to jquery 3.6.3 :pr:`90`
- Update to fomantic-ui 2.9.1 :pr:`90`
- Update to datatables 1.13.1 :pr:`90`

Fixed
*****

- Fix typos and grammar errors. :pr:`84`
- Fix wording and punctuations. :pr:`86`
- Fix HTML lang tag :issue:`122` :pr:`87`
- Automatically trims the HTML translated strings. :pr:`91`
- Fixed dynamic registration scope management. :issue:`123` :pr:`93`

[0.0.19] - 2023-01-14
=====================

Fixed
*****

- Ensures the token `expires_in` claim and the `access_token` `exp` claim
  have the same value. :pr:`83`

[0.0.18] - 2022-12-28
=====================

Fixed
*****

- OIDC end_session was not returning the ``state`` parameter in the
  ``post_logout_redirect_uri`` :pr:`82`

[0.0.17] - 2022-12-26
=====================

Fixed
*****

- Fixed group deletion button. :pr:`80`
- Fixed post requests in oidc clients views. :pr:`81`

[0.0.16] - 2022-12-15
=====================

Fixed
*****

- Fixed LDAP operational attributes handling.

[0.0.15] - 2022-12-15
=====================

Added
*****

- User can chose their favourite display name. :pr:`77`
- Bumped to authlib 1.2. :pr:`78`
- Implemented RFC7592 OAuth 2.0 Dynamic Client Registration Management
  Protocol :pr:`79`
- Added ``nonce`` to the ``claims_supported`` server metadata list.

[0.0.14] - 2022-11-29
=====================

Fixed
*****
- Fixed translation mo files packaging.

[0.0.13] - 2022-11-21
=====================

Fixed
*****

- Fixed a bug on the contacts field in the admin client form following
  the LDAP schema update of 0.0.12
- Fixed a bug happening during RP initiated logout on clients without
  `post_logout_redirect_uri` defined.
- Gitlab CI fix. :pr:`64`
- Fixed `client_secret` display on the client administration page. :pr:`65`
- Fixed non-square logo CSS. :pr:`67`
- Fixed schema path on installation. :pr:`68`
- Fixed RFC7591 ``software_statement`` claim support. :pr:`70`
- Fixed client preconsent disabling. :pr:`72`

Added
*****

- Python 3.11 support. :pr:`61`
- apparmor slapd configuration instructions in CONTRIBUTING.rst :pr:`66`
- ``preferredLanguage`` attribute support. :pr:`75`

Changed
*******

- Replaced the use of the deprecated `FLASK_ENV` environment variable by
  `FLASK_DEBUG`.
- Dynamically generate the server metadata. Users won't have to copy and
  manually edit ``oauth-authorizationserver.json`` and
  ``openid-configuration.json``. :pr:`71`
- The `FROM_ADDR` configuration option is not mandatory anymore. :pr:`73`
- The `JWT.ISS` configuration option is not mandatory anymore. :pr:`74`

[0.0.12] - 2022-10-24
=====================

Added
*****

- Basic WebFinger endpoint. :pr:`59`
- Bumped to FomanticUI 2.9.0 00ffffee
- Implemented Dynamic Client Registration :pr:`60`

[0.0.11] - 2022-08-11
=====================

Added
*****

- Default theme has a dark variant. :pr:`57`

Fixed
*****

- Fixed missing ``canaille`` binary. :pr:`58`

[0.0.10] - 2022-07-07
=====================

Fixed
*****

- Online demo. :pr:`55`
- The consent page was displaying scopes not supported by clients. :pr:`56`
- Fixed end session when user are already disconnected.

[0.0.9] - 2022-06-05
====================

Added
*****

- ``DISABLE_PASSWORD_RESET`` configuration option to disable password recovery. :pr:`46`
- ``edit_self`` ACL permission to control user self edition. :pr:`47`
- Implemented RP-initiated logout :pr:`54`

Changed
*******

- Bumped to authlib 1 :pr:`48`
- documentation improvements :pr:`50`
- use poetry instead of setuptools :pr:`51`
- additional nonce tests :pr:`52`

Fixed
*****
- ``HIDE_INVALID_LOGIN`` behavior and default value.
- mo files are not versionned anymore :pr:`49` :pr:`53`

[0.0.8] - 2022-03-15
====================

Fixed
*****

- Fixed dependencies

[0.0.7] - 2022-03-15
====================

Fixed
*****

- Fixed spaces and escaped special char in ldap cn/dn :pr:`43`

[0.0.6] - 2022-03-08
====================

Changed
*******

- Access token are JWT. :pr:`38`

Fixed
*****

- Default groups on invitations :pr:`41`
- Schemas are shipped within the canaille package :pr:`42`

[0.0.5] - 2022-02-17
====================

Changed
*******

- LDAP model objects have new identifiers :pr:`37`

Fixed
*****

- Admin menu dropdown display :pr:`39`
- `GROUP_ID_ATTRIBUTE` configuration typo :pr:`40`

[0.0.4] - 2022-02-16
====================

Added
*****

- Client preauthorization :pr:`11`
- LDAP permissions check with the check command :pr:`12`
- Update consents when a scope required is larger than the scope of an already
  given consent :pr:`13`
- Theme customization :pr:`15`
- Logging configuration :pr:`16`
- Installation command :pr:`17`
- Invitation links :pr:`18`
- Advanced permissions :pr:`20`
- An option to not use OIDC :pr:`23`
- Disable some features when no SMTP server is configured :pr:`24`
- Login placeholder dynamically generated according to the configuration :pr:`25`
- Added an option to tune object IDs :pr:`26`
- Avatar support :pr:`27`
- Dynamical and configurable JWT claims :pr:`28`
- UI improvemnts :pr:`29`
- Invitation links expiration :pr:`30`
- Invitees can choose their IDs :pr:`31`
- LDAP backend refactoring :pr:`35`

Fixed
*****

- Fixed ghost members in a group :pr:`14`
- Fixed email sender names :pr:`19`
- Fixed filter being not escaped :pr:`21`
- Demo script good practices :pr:`32`
- Binary path for Debian :pr:`33`
- Last name was not mandatory in the forms while this was mandatory
  in the LDAP server :pr:`34`
- Spelling typos :pr:`36`

[0.0.3] - 2021-10-13
====================

Added
*****

- Two-steps sign-in :issue:`49`
- Tokens can have several audiences. :issue:`62` :pr:`9`
- Configuration check command. :issue:`66` :pr:`8`
- Groups managament. :issue:`12` :pr:`6`

Fixed
*****

- Introspection access bugfix. :issue:`63` :pr:`10`
- Introspection sub claim. :issue:`64` :pr:`7`

[0.0.2] - 2021-01-06
====================

Added
*****

- Login page is responsive. :issue:`1`
- Adapt mobile keyboards to login page fields. :issue:`2`
- Password recovery interface. :issue:`3`
- User profile interface. :issue:`4`
- Renamed the project *canaille*. :issue:`5`
- Command to remove old tokens. :issue:`17`
- Improved password recovery email. :issue:`14` :issue:`26`
- Use flask `SERVER_NAME` configuration variable instead of `URL`. :issue:`24`
- Improved consents page. :issue:`27`
- Admin user page. :issue:`8`
- Project logo. :pr:`29`
- User account self-deletion can be enabled in the configuration with `SELF_DELETION`. :issue:`35`
- Admins can impersonate users. :issue:`39`
- Forgotten page UX improvement. :pr:`43`
- Admins can remove clients. :pr:`45`
- Option `HIDE_INVALID_LOGIN` that can be unactivated to let the user know if
  the login he attempt to sign in with exists or not. :pr:`48`
- Password initialization mail. :pr:`51`

Fixed
*****

- Form translations. :issue:`19` :issue:`23`
- Avoid to use Google Fonts. :issue:`21`

Removed
*******

- 'My tokens' page. :issue:`22`

[0.0.1] - 2020-10-21
====================

Added
*****

- Initial release.
