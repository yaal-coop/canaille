All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

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
