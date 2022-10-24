All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

[0.0.12] - 2022-xx-xx
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
