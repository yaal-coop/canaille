[0.0.59] - 2025-01-10
---------------------

Fixed
^^^^^
- Fix password fields auto-refilling when input is reset. :issue:`218` :pr:`215`
- Fix HTMX integration with the email confirmation form. :pr:`216`

Changed
^^^^^^^
- Bump to HTMX 2.0.4

[0.0.58] - 2025-01-10
---------------------

Added
^^^^^
- ``--version`` option to the CLI. :pr:`209`
- Password hashing scheme customization with the :attr:`~canaille.backends.sql.configuration.SQLSettings.PASSWORD_SCHEMES` parameter. :issue:`175`
- `canaille dump` command option to perform full database dumps.
- Automatic SQL database migrations. :issue:`217` :pr:`214`

Changed
^^^^^^^
- CLI commands dump hashed passwords. :issue:`214`

Fixed
^^^^^^^
- A bug on updating user's settings. :issue:`206`

[0.0.57] - 2024-12-31
---------------------

Added
^^^^^
- Intruder lockout :issue:`173`
- :attr:`~canaille.core.configuration.CoreSettings.ENABLE_INTRUDER_LOCKOUT`
  :issue:`173`
- Multi-factor authentication :issue:`47`
- :attr:`~canaille.core.configuration.CoreSettings.OTP_METHOD` and
  :attr:`~canaille.core.configuration.CoreSettings.EMAIL_OTP` and
  :attr:`~canaille.core.configuration.CoreSettings.SMS_OTP` and
  :attr:`~canaille.core.configuration.CoreSettings.SMPP`
  :issue:`47`
- Password compromission check :issue:`179`
- :attr:`~canaille.core.configuration.CoreSettings.ADMIN_EMAIL` and
  :attr:`~canaille.core.configuration.CoreSettings.ENABLE_PASSWORD_COMPROMISSION_CHECK` and
  :attr:`~canaille.core.configuration.CoreSettings.PASSWORD_COMPROMISSION_CHECK_API_URL`
  :issue:`179`
- Implement OIDC client_credentials flow. :issue:`207`
- Button in the client admin page to create client tokens.
- Basic SCIM implementation. :issue:`116` :pr:`197`
- Password expiry policy :issue:`176`
- :attr:`~canaille.core.configuration.CoreSettings.PASSWORD_LIFETIME`

Changed
^^^^^^^
- PostgreSQL and MySQL extras does not rely on libraries that need to be compiled.
- ``.env`` files are not loaded by default. The ``ENV_FILE`` env var must be passed so ``.env`` files are loaded.

[0.0.56] - 2024-11-07
---------------------

Fixed
^^^^^
- With LDAP backend, updating another user groups could result in a permission lost for the editor. :issue:`202`

Added
^^^^^
- :attr:`~canaille.core.configuration.CoreSettings.MAX_PASSWORD_LENGTH` and
  :attr:`~canaille.core.configuration.CoreSettings.MIN_PASSWORD_LENGTH` configuration options :issue:`174`
- Password strength visual indicator. :issue:`174`
- Security events logs. :issue:`177`
- Support for Python 3.13. :pr:`186`

Changed
^^^^^^^
- Update to `HTMX` 2.0.3. :pr:`184`
- Migrate the Python project management tool from poetry to uv. :pr:`187`
- The ``sql`` package extra is now split between ``sqlite``, ``postgresql`` and ``mysql``.

Removed
^^^^^^^
- End support for Python 3.9. :pr:`179`

[0.0.55] - 2024-08-30
---------------------

Changed
^^^^^^^
- Use poetry-core build backend. :pr:`178`

[0.0.54] - 2024-07-25
---------------------

Added
^^^^^
- Group member removal can be achieved from the group edition page. :issue:`192`
- Model management commands. :issue:`117` :issue:`54`

Changed
^^^^^^^
- Model `identifier_attributes` are fixed.
- Bump to `HTMX` 1.9.12. :pr:`172`

Fixed
^^^^^

- Dark theme colors for better readability.
- Crash for passwordless users at login when no SMTP server was configured.

[0.0.53] - 2024-04-22
---------------------

Added
^^^^^
- `env_prefix` `create_app`` variable can select the environment var prefix.

[0.0.52] - 2024-04-22
---------------------

Added
^^^^^
- `env_file` create_app variable can customize/disable the .env file.

Changed
^^^^^^^
- Locked users cannot be impersonated anymore.
- Minimum Python requirement is 3.9.

[0.0.51] - 2024-04-09
---------------------

Changed
^^^^^^^
- Display the menu bar on error pages.

[0.0.50] - 2024-04-09
---------------------

Added
^^^^^
- Sign in/out events are logged in. :issue:`177`

Fixed
^^^^^
- `HTMX` and `JAVASCRIPT` configuration settings.
- Compatibility with old sessions IDs.

[0.0.49] - 2024-04-08
---------------------

Fixed
^^^^^
- LDAP user group removal.
- Display an error message when trying to remove the last user from a group.

[0.0.48] - 2024-04-08
---------------------

Fixed
^^^^^
- LDAP ``objectClass`` guessing exception.

[0.0.47] - 2024-04-08
---------------------

Fixed
^^^^^
- Lazy permission loading exception.

[0.0.46] - 2024-04-08
---------------------

Fixed
^^^^^
- Saving an object with the LDAP backend keeps the ``objectClass`` un-managed by Canaille. :pr:`171`

[0.0.45] - 2024-04-04
---------------------

Changed
^^^^^^^
- Internal indexation mechanism of ``MemoryModel``.

[0.0.44] - 2024-03-29
---------------------

Fixed
^^^^^
- Fix the default LDAP ``USER_FILTER`` value.
- Fix the OIDC feature detection.

[0.0.43] - 2024-03-29
---------------------

.. warning::

    Configuration files must be updated.

Added
^^^^^

- Add ``created`` and ``last_modified`` datetime for all models.
- Sitemap to the documentation. :pr:`169`
- Configuration management with `pydantic-settings`. :issue:`138` :pr:`170`

Changed
^^^^^^^

- Use default Python logging configuration format. :issue:`188` :pr:`165`
- Bump to `HTMX` 1.99.11. :pr:`166`
- Use the standard tomllib Python module instead of `toml` starting from Python 3.11. :pr:`167`
- Use shibuya as the documentation theme :pr:`168`

[0.0.42] - 2023-12-29
---------------------

Fixed
^^^^^

- Avoid to fail on imports if ``cryptography`` is missing.

[0.0.41] - 2023-12-25
---------------------

Added
^^^^^

- OIDC support for the ``create`` value of the ``prompt`` parameter. :issue:`185` :pr:`164`

Fixed
^^^^^

- Correctly set up :attr:`~canaille.oidc.basemodels.Client.audience` during OIDC dynamic registration.
- ``post_logout_redirect_uris`` was ignored during OIDC dynamic registration.
- Group field error prevented the registration form validation.

[0.0.40] - 2023-12-22
---------------------

Added
^^^^^

- The ``THEME`` setting can be a relative path.

[0.0.39] - 2023-12-15
---------------------

Fixed
^^^^^

- Crash when no ACL were defined.
- OIDC Userinfo endpoint is also available in POST.
- Fix redirection after password reset. :issue:`159`

[0.0.38] - 2023-12-15
---------------------

Changed
^^^^^^^

- Convert all the `PNG` pictures in `Webp`. :pr:`162`
- Update to Flask 3. :issue:`161` :pr:`163`

[0.0.37] - 2023-12-01
---------------------

Fixed
^^^^^

- Handle 4xx and 5xx error codes with HTMX. :issue:`171` :pr:`161`

[0.0.36] - 2023-12-01
---------------------

Fixed
^^^^^

- Avoid crashing when LDAP groups references unexisting users.
- Password reset and initialization mails were only sent to the
  preferred user email address.
- Password reset and initialization mails were not sent at all the user
  addresses if one email address could not be reached.
- Password comparison was too permissive on login.
- Encrypt passwords in the SQL backend.

[0.0.35] - 2023-11-25
---------------------

Added
^^^^^

- Refresh token grant supports other client authentication methods. :pr:`157`
- Implement a SQLAlchemy backend. :issue:`30` :pr:`158`

Changed
^^^^^^^

- Model attributes cardinality is closer to SCIM model. :pr:`155`
- Bump to `HTMX` 1.9.9. :pr:`159`

Fixed
^^^^^

- Disable `HTMX` boosting during the OIDC dance. :pr:`160`

[0.0.34] - 2023-10-02
---------------------

Fixed
^^^^^

- Canaille installations without account lockabilty could not
  delete users. :pr:`153`

Added
^^^^^

- If users register or authenticate during a OAuth Authorization
  phase, they get redirected back to that page afterwards.
  :issue:`168` :pr:`151`
- The `flask-babel` and `pytz` libraries are now part of the `front` packaging extras.
- Bump to `fomantic-ui` 2.9.3. :pr:`152`
- Bump to `HTMX` 1.9.6. :pr:`154`
- Support for Python 3.12. :pr:`155`

[0.0.33] - 2023-08-26
---------------------

Fixed
^^^^^

- OIDC jwks endpoint do not return empty `kid` claim.

Added
^^^^^

- Documentation details on the Canaille models.

[0.0.32] - 2023-08-17
---------------------

Added
^^^^^

- Additional inmemory backend. :issue:`30` :pr:`149`
- Installation extras. :issue:`167` :pr:`150`

[0.0.31] - 2023-08-15
---------------------

Added
^^^^^

- Configuration option to disable the forced usage of OIDC `nonce` parameter. :pr:`143`
- Validate phone numbers with a regex. :pr:`146`
- Email verification. :issue:`41` :pr:`147`
- Account registration. :issue:`55` :pr:`133` :pr:`148`

Fixed
^^^^^

- The `check` command uses the default configuration values.

Changed
^^^^^^^

- Modals do not need use Javascript at the moment. :issue:`158` :pr:`144`

[0.0.30] - 2023-07-06
---------------------

.. warning::

    Configuration files must be updated.
    Check the new format with ``git diff 0.0.29 0.0.30 canaille/conf/config.sample.toml``

Added
^^^^^

- Configuration option to disable Javascript. :pr:`141`

Changed
^^^^^^^

- The configuration parameter ``USER_FILTER`` is parsed with Jinja.
- Configuration use ``PRIVATE_KEY_FILE`` instead of ``PRIVATE_KEY`` and ``PUBLIC_KEY_FILE`` instead of ``PUBLIC_KEY``.

[0.0.29] - 2023-06-30
---------------------

Fixed
^^^^^

- Disabled `HTMX` boosting on OIDC forms to avoid errors.

[0.0.28] - 2023-06-30
---------------------

Fixed
^^^^^

- A template variable was misnamed.

[0.0.27] - 2023-06-29
---------------------

.. warning::

    Configuration files must be updated.
    Check the new format with ``git diff 0.0.26 0.0.27 canaille/conf/config.sample.toml``

Added
^^^^^

- Configuration entries can be loaded from files if the entry key has a *_FILE* suffix
  and the entry value is the path to the file. :issue:`134` :pr:`134`
- Field list support. :issue:`115` :pr:`136`
- Pages are boosted with `HTMX`. :issue:`144` :issue:`145` :pr:`137`

Changed
^^^^^^^

- Bump to jquery 3.7.0. :pr:`138`

Fixed
^^^^^

- Profile edition when the user RDN was not ``uid``. :issue:`148` :pr:`139`

Removed
^^^^^^^

- Stop support for Python 3.7. :pr:`131`

[0.0.26] - 2023-06-03
---------------------

Added
^^^^^

- Implemented account expiration based on OpenLDAP ppolicy overlay. Needs OpenLDAP 2.5+.
  :issue:`13` :pr:`118`
- Timezone configuration entry. :issue:`137` :pr:`130`

Fixed
^^^^^

- Avoid setting ``None`` in JWT claims when they have no value.
- Display password recovery button on OIDC login page. :pr:`129`

[0.0.25] - 2023-05-05
---------------------

.. warning::

   Configuration files must be updated.
    Check the new format with ``git diff 0.0.25 0.0.24 canaille/conf/config.sample.toml``

Changed
^^^^^^^

- Renamed user model attributes to match SCIM naming convention. :pr:`123`
- Moved OIDC related configuration entries in ``OIDC``.
- Moved ``LDAP`` configuration entry to ``BACKENDS.LDAP``.
- Bumped to `HTMX` 1.9.0. :pr:`124`
- ACL filters are no more LDAP filters but user attribute mappings. :pr:`125`
- Bumped to `HTMX` 1.9.2. :pr:`127`

Fixed
^^^^^

- ``OIDC.JWT.MAPPING`` configuration entry is really optional now.
- Fixed empty model attributes registration. :pr:`125`
- Password initialization mails were not correctly sent. :pr:`128`

[0.0.24] - 2023-04-07
---------------------

Fixed
^^^^^

- Fixed avatar update. :pr:`122`

[0.0.23] - 2023-04-05
---------------------

Added
^^^^^

- Organization field. :pr:`116`
- ETag and Last-Modified headers on user photos. :pr:`116`
- Dynamic form validation. :pr:`120`

Changed
^^^^^^^

- UX rework. Submenu addition. :pr:`114`
- Properly handle LDAP date timezones. :pr:`117`

Fixed
^^^^^

- CSRF protection on every forms. :pr:`119`

[0.0.22] - 2023-03-13
---------------------

Fixed
^^^^^
- The `Faker` library is not imported anymore when the `clean` command is called.

[0.0.21] - 2023-03-12
---------------------

Added
^^^^^

- Display TOS and policy URI on the consent list page. :pr:`102`
- Admin token deletion. :pr:`100` :pr:`101`
- Revoked consents can be restored. :pr:`103`
- Pre-consented clients are displayed in the user consent list,
  and their consents can be revoked. :issue:`69` :pr:`103`
- A ``populate`` command can be used to fill the database with
  random users generated with faker. :pr:`105`
- SMTP SSL support. :pr:`108`
- Server side pagination. :issue:`114` :pr:`111`
- Department number support. :issue:`129`
- Address edition support (but not in the OIDC claims yet). :pr:`112`
- Title edition support. :pr:`113`

Fixed
^^^^^

- Client deletion also deletes related :class:`~canaille.oidc.basemodels.Consent`, :class:`~canaille.oidc.basemodels.Token` and
  :class:`~canaille.oidc.basemodels.AuthorizationCode` objects. :issue:`126` :pr:`98`

Changed
^^^^^^^

- Removed the `DataTables` Javascript library.

[0.0.20] - 2023-01-28
---------------------

Added
^^^^^

- Spanish translation. :pr:`85` :pr:`88`
- Dedicated connectivity test email. :pr:`89`
- Update to jquery 3.6.3. :pr:`90`
- Update to fomantic-ui 2.9.1. :pr:`90`
- Update to DataTables 1.13.1. :pr:`90`

Fixed
^^^^^

- Fix typos and grammar errors. :pr:`84`
- Fix wording and punctuations. :pr:`86`
- Fix HTML lang tag. :issue:`122` :pr:`87`
- Automatically trims the HTML translated strings. :pr:`91`
- Fixed dynamic registration scope management. :issue:`123` :pr:`93`

[0.0.19] - 2023-01-14
---------------------

Fixed
^^^^^

- Ensures the token `expires_in` claim and the `access_token` `exp` claim
  have the same value. :pr:`83`

[0.0.18] - 2022-12-28
---------------------

Fixed
^^^^^

- OIDC end_session was not returning the ``state`` parameter in the
  ``post_logout_redirect_uri``. :pr:`82`

[0.0.17] - 2022-12-26
---------------------

Fixed
^^^^^

- Fixed group deletion button. :pr:`80`
- Fixed post requests in oidc clients views. :pr:`81`

[0.0.16] - 2022-12-15
---------------------

Fixed
^^^^^

- Fixed LDAP operational attributes handling.

[0.0.15] - 2022-12-15
---------------------

Added
^^^^^

- User can chose their display name. :pr:`77`
- Bumped to Authlib 1.2. :pr:`78`
- Implemented :rfc:`RFC7592 <7592>` OAuth 2.0 Dynamic Client Registration Management
  Protocol. :pr:`79`
- Add the ``nonce`` parameter to the ``claims_supported`` server metadata list.

[0.0.14] - 2022-11-29
---------------------

Fixed
^^^^^
- Fixed translation catalogs packaging.

[0.0.13] - 2022-11-21
---------------------

Fixed
^^^^^

- Fixed a bug on the contacts field in the admin client form following
  the LDAP schema update of 0.0.12.
- Fixed a bug happening during RP initiated logout on clients without
  `post_logout_redirect_uri` defined.
- Gitlab CI fix. :pr:`64`
- Fixed `client_secret` display on the client administration page. :pr:`65`
- Fixed non-square logo CSS. :pr:`67`
- Fixed schema path on installation. :pr:`68`
- Fixed RFC7591 ``software_statement`` claim support. :pr:`70`
- Fixed client preconsent disabling. :pr:`72`

Added
^^^^^

- Python 3.11 support. :pr:`61`
- ``apparmor`` slapd configuration instructions in the documentation page for contributions. :pr:`66`
- ``preferredLanguage`` attribute support. :pr:`75`

Changed
^^^^^^^

- Replaced the use of the deprecated `FLASK_ENV` environment variable by
  `FLASK_DEBUG`.
- Dynamically generate the server metadata. Users won't have to copy and
  manually edit ``oauth-authorizationserver.json`` and
  ``openid-configuration.json``. :pr:`71`
- The `FROM_ADDR` configuration option is not mandatory anymore. :pr:`73`
- The `JWT.ISS` configuration option is not mandatory anymore. :pr:`74`

[0.0.12] - 2022-10-24
---------------------

Added
^^^^^

- Basic WebFinger endpoint. :pr:`59`
- Bumped to FomanticUI 2.9.0.
- Implemented Dynamic Client Registration. :pr:`60`

[0.0.11] - 2022-08-11
---------------------

Added
^^^^^

- Default theme has a dark variant. :pr:`57`

Fixed
^^^^^

- Fixed missing ``canaille`` binary. :pr:`58`

[0.0.10] - 2022-07-07
---------------------

Fixed
^^^^^

- Online demo. :pr:`55`
- The consent page was displaying scopes not supported by clients. :pr:`56`
- Fixed end session when user are already disconnected.

[0.0.9] - 2022-06-05
--------------------

Added
^^^^^

- ``DISABLE_PASSWORD_RESET`` configuration option to disable password recovery. :pr:`46`
- ``edit_self`` ACL permission to control user self edition. :pr:`47`
- `RP-initiated logout` implementation. :pr:`54`

Changed
^^^^^^^

- Bumped to Authlib 1. :pr:`48`
- Various documentation improvements. :pr:`50`
- Use poetry instead of setuptools as project management tool. :pr:`51`
- Additional tests for the OIDC ``nonce`` parameter. :pr:`52`

Fixed
^^^^^
- ``HIDE_INVALID_LOGIN`` behavior and default value.
- Compiled translation catalogs are not versioned anymore. :pr:`49` :pr:`53`

[0.0.8] - 2022-03-15
--------------------

Fixed
^^^^^

- Fixed dependencies.

[0.0.7] - 2022-03-15
--------------------

Fixed
^^^^^

- Fixed spaces and escaped special char in LDAP ``cn/dn`` attributes. :pr:`43`

[0.0.6] - 2022-03-08
--------------------

Changed
^^^^^^^

- Access token are JWT. :pr:`38`

Fixed
^^^^^

- Default groups on invitations. :pr:`41`
- LDAP schemas are shipped within the Canaille package. :pr:`42`

[0.0.5] - 2022-02-17
--------------------

Changed
^^^^^^^

- LDAP model objects have new identifiers. :pr:`37`

Fixed
^^^^^

- Admin menu dropdown display. :pr:`39`
- ``GROUP_ID_ATTRIBUTE`` configuration typo. :pr:`40`

[0.0.4] - 2022-02-16
--------------------

Added
^^^^^

- Client pre-authorization. :pr:`11`
- LDAP permissions check with the check command. :pr:`12`
- Update consents when a scope required is larger than the scope of an already
  given consent. :pr:`13`
- Theme customization. :pr:`15`
- Logging configuration. :pr:`16`
- Installation command. :pr:`17`
- Invitation links. :pr:`18`
- Advanced permissions. :pr:`20`
- An option to not use OIDC. :pr:`23`
- Disable some features when no SMTP server is configured. :pr:`24`
- Login placeholder dynamically generated according to the configuration. :pr:`25`
- Added an option to tune object IDs. :pr:`26`
- Avatar support. :pr:`27`
- Dynamical and configurable JWT claims. :pr:`28`
- UI improvements. :pr:`29`
- Invitation links expiration. :pr:`30`
- Invitees can choose their IDs. :pr:`31`
- LDAP backend refactoring. :pr:`35`

Fixed
^^^^^

- Fixed ghost members in a group. :pr:`14`
- Fixed email sender names. :pr:`19`
- Fixed filter being not escaped. :pr:`21`
- Demo script good practices. :pr:`32`
- Binary path for Debian. :pr:`33`
- Last name was not mandatory in the forms while this was mandatory
  in the LDAP server. :pr:`34`
- Spelling typos. :pr:`36`

[0.0.3] - 2021-10-13
--------------------

Added
^^^^^

- Two-steps sign-in. :issue:`49`
- Tokens can have several audiences. :issue:`62` :pr:`9`
- Configuration check command. :issue:`66` :pr:`8`
- Groups management. :issue:`12` :pr:`6`

Fixed
^^^^^

- Introspection access bugfix. :issue:`63` :pr:`10`
- Introspection sub claim. :issue:`64` :pr:`7`

[0.0.2] - 2021-01-06
--------------------

Added
^^^^^

- Login page is responsive. :issue:`1`
- Adapt mobile keyboards to login page fields. :issue:`2`
- Password recovery interface. :issue:`3`
- User profile interface. :issue:`4`
- Renamed the project *Canaille*. :issue:`5`
- Command to remove old tokens. :issue:`17`
- Improved password recovery email. :issue:`14` :issue:`26`
- Use Flask `SERVER_NAME` configuration variable instead of `URL`. :issue:`24`
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
^^^^^

- Form translations. :issue:`19` :issue:`23`
- Avoid to use Google Fonts. :issue:`21`

Removed
^^^^^^^

- 'My tokens' page. :issue:`22`

[0.0.1] - 2020-10-21
--------------------

Added
^^^^^

- Initial release.
