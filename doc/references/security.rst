Security
########

Using Canaille allows to easily set-up good security practices.

ANSSI recommendation
====================

The French security agency (ANSSI) describe a `list of security recommendations <https://cyber.gouv.fr/publications/recommandations-relatives-lauthentification-multifacteur-et-aux-mots-de-passe>`__ about authentication and password management. Here is a summary of how Canaille implements those recommendations:

**Legend:**

- ✅ Implemented by Canaille
- 🟧 Partially implemented by Canaille
- ❌ Not implemented by Canaille
- ⬜ Not relevant for Canaille (organizational/user/infrastructure responsibility)

.. list-table:: ANSSI authentication recommendations implementation status
   :header-rows: 1
   :widths: 10 60 25 5

   * - ID
     - ANSSI Recommendation
     - Canaille implementation
     - Status
   * - R1
     - Favor multi-factor authentication. Use multiple authentication factors from different categories (knowledge, possession, inherence).
     - Canaille supports :ref:`multi-factor authentication <feature_mfa>`.
     - ✅
   * - R2
     - Favor the use of strong authentication methods. Use cryptographic mechanisms compliant with `RGS <https://cyber.gouv.fr/le-referentiel-general-de-securite-rgs>`__ and its annexes.
     - Canaille implements :ref:`TOTP <feature_mfa>` which uses strong cryptographic mechanisms. :issue:`WebAuthn support is planned<296>`.
     - ✅
   * - R3
     - Conduct a risk analysis. Perform risk analysis to determine appropriate authentication methods based on security needs.
     - This is an organizational responsibility, not specific to Canaille implementation.
     - ⬜
   * - R4
     - Create authentication factors in a controlled environment. Create and deliver factors in a secure environment consistent with the expected security level.
     - This is an organizational and operational responsibility.
     - ⬜
   * - R5
     - Generate random elements with a robust generator. Use a random number generator compliant with `RGS <https://cyber.gouv.fr/le-referentiel-general-de-securite-rgs>`__ annex B1.
     - Canaille uses :mod:`Python's cryptographically secure random generators <secrets>`.
     - ✅
   * - R6
     - Deliver authentication factors through secure channels. Favor hand delivery or use channels protected for integrity, authenticity and confidentiality.
     - This is an organizational responsibility for credential distribution.
     - ⬜
   * - R7
     - Implement an authentication factor renewal process. Allow users to renew their authentication factors.
     - Users can update their password, email address and phone numbers. The can manage their :ref:`TOTP <feature_mfa>` devices in their profile.
     - ✅
   * - R8
     - Do not use SMS as a means of receiving an authentication factor.
     - SMS authentication is available in Canaille, but disabled by default.
       It is still offered as a convenient alternative in low-security contexts.
     - ✅
   * - R9
     - Preserve usage history of authentication factors. Log authentication-related events to detect abnormal behavior.
     - Canaille logs authentication events and login attempts.
     - ✅
   * - R10
     - Limit authentication attempts over time.
     - Canaille implements :ref:`intruder lockout <feature_intruder_lockout>` with progressive delays after failed attempts.
       See :attr:`~canaille.core.configuration.CoreSettings.ENABLE_INTRUDER_LOCKOUT`.
     - ✅
   * - R11
     - Perform authentication through a secure channel. Use protocols like TLS or IPsec to protect authentication communications.
     - This is handled by the web server configuration.
     - ⬜
   * - R12
     - Limit the validity duration of authenticated sessions. Set maximum session duration and force periodic re-authentication.
     - Canaille limits session duration. The default value of 1 year is customizable. See :attr:`~canaille.app.configuration.RootSettings.PERMANENT_SESSION_LIFETIME`.
     - ✅
   * - R13
     - Protect authentication data stored by the verifier. Ensure confidentiality and integrity protection of stored authentication data.
     - Canaille properly hashes passwords using secure algorithms. See :attr:`~canaille.backends.sql.configuration.SQLSettings.PASSWORD_SCHEMES`.
     - ✅
   * - R14
     - Do not provide information about authentication failure. In case of multi-factor failure, do not reveal which factor caused the failure.
     - Canaille verifies each factor one by one.
     - ❌
   * - R15
     - Define expiration delays for authentication factors. Set expiration dates to limit fraudulent use.
     - Canaille implements expiration for email and SMS codes, as well as TOTP.
       HOTP codes don't expire, but they are not used by default when selecting OTP authentication factor.
       Password can have an expiration date, but this not recommended for common user accounts by R24.
       See :attr:`~canaille.core.configuration.CoreSettings.OTP_LIFETIME`, :attr:`~canaille.core.configuration.CoreSettings.TOTP_LIFETIME` and :attr:`~canaille.core.configuration.CoreSettings.PASSWORD_LIFETIME`.
     - ✅
   * - R16
     - Define a usage policy for authentication factors. Establish usage conditions and procedures for loss or compromise cases.
     - This is an organizational policy responsibility.
     - ⬜
   * - R17
     - Raise user awareness about authentication security. Implement awareness campaigns about risks (phishing, etc.).
     - This is an organizational training responsibility.
     - ⬜
   * - R18
     - Enable factor revocation and distribute revocation information.
     - All the authentication factors can be reset, but the way by which users ask for a revokation is the responsibility of the organization.
     - ✅
   * - R19
     - Define appropriate revocation processing delays. Adapt revocation delays to threats facing the system.
     - This is an organizational policy decision.
     - ⬜
   * - R20
     - Implement a password security policy. Define a policy adapted to context and security objectives.
     - The formal definition of the security is the responsibility of the organization, but any part of the policy can be customized in Canaille. See following recommendations. Canaille provides good-enough defaults for all the points.
     - ✅
   * - R21
     - Enforce minimum password length. Define minimum length based on target security level.
     - Password length is configurable. See :attr:`~canaille.core.configuration.CoreSettings.MIN_PASSWORD_LENGTH` setting.
     - ✅
   * - R22
     - Do not enforce maximum password length. Allow the use of long passphrases.
     - Canaille supports long passwords, but sets a great-enough upper limit to prevent DOS attacks by providing too heavy payloads.
       See :attr:`~canaille.core.configuration.CoreSettings.MAX_PASSWORD_LENGTH`.
     - ✅
   * - R23
     - Implement password complexity rules. Impose constraints on character types used.
     - Canaille does not enforce character type complexity requirements. See the :issue:`related issue <297>`.
     - ❌
   * - R24
     - Do not enforce expiration delays by default on non-sensitive accounts.
       Avoid automatic expiration for standard user accounts if passwords are robust.
     - Canaille does not enforce password expiration by default.
     - ✅
   * - R25
     - Enforce expiration delays on privileged account passwords.
       Set expiration (1-3 years) for administrator accounts.
     - Password expiration :attr:`can be customized <canaille.core.configuration.CoreSettings.MAX_PASSWORD_LENGTH>` but Canaille does not differentiate password policies between regular and privileged accounts.
     - 🟧
   * - R26
     - Immediately revoke passwords in case of suspected or confirmed compromise.
       Renew all affected passwords within a day in case of incident.
     - This is an operational incident response procedure.
     - ⬜
   * - R27
     - Implement password strength control. Automatically check strength during creation/renewal.
     - Canaille implements password strength validation using the zxcvbn algorithm, with a visual strength indicator during password entry.
       Additionally, passwords are tested against the `Have I Been Pwned <https://haveibeenpwned.com>`__ database.
       However, Canaille don't look for reuse of old passwords, or :issue:`personal information in the current password <298>`.
     - 🟧
   * - R28
     - Use a long random salt. Use a random salt of at least 128 bits for each account.
     - Canaille uses proper salting for password hashing with all supported :attr:`~canaille.backends.sql.configuration.SQLSettings.PASSWORD_SCHEMES`.
     - ✅
   * - R29
     - Use memory-hard password derivation function to store passwords. Use scrypt or Argon2 for password storage.
     - Canaille supports Argon2 and other secure algorithms via :attr:`~canaille.backends.sql.configuration.SQLSettings.PASSWORD_SCHEMES`.
     - ✅
   * - R29-
     - Use iterative password derivation function to store passwords. Alternative: use PBKDF2 if memory-hard functions are difficult to implement.
     - Canaille supports PBKDF2 and uses the ``pbkdf2_sha512`` scheme by default.
       See :attr:`~canaille.backends.sql.configuration.SQLSettings.PASSWORD_SCHEMES`.
     - ✅
   * - R30
     - Provide an access recovery method. Implement recovery procedures for forgotten/lost credentials.
     - Canaille can provide password recovery via email by configuration.
       Defining the password recovery policy is the responsibility of the organization.
       See :attr:`~canaille.core.configuration.CoreSettings.ENABLE_PASSWORD_RECOVERY`.
     - ✅
   * - R31
     - Provide a password vault. Supply and train users on password manager usage.
     - This is an organizational responsibility to provide password managers.
     - ⬜
   * - R32-R38
     -
     - The recommendations R32 to R38 target end-users.
     - ⬜
   * - R39
     - Use a possession factor integrating a qualified security component. Favor components that have received ANSSI security approval.
     - :issue:`WebAuthn support is planned <296>` but not yet implemented.
     - ❌
   * - R39-
     - Use a possession factor integrating a security component. Alternative: use at minimum an integrated security component.
     - :issue:`WebAuthn support is planned <296>` but not yet implemented.
     - ❌
   * - R39--
     - Use a possession factor even without security component. As last resort, use additional protection measures (encryption, access restrictions).
     - :ref:`TOTP <feature_mfa>` can work with software authenticators as a possession factor via :attr:`~canaille.core.configuration.CoreSettings.OTP_METHOD`.
     - ✅
   * - R40
     - Do not use an inherent factor as sole authentication factor. Avoid biometrics alone for authentication.
     - Canaille does not implement biometric authentication. :issue:`WebAuthn support is planned <296>`.
     - ❌
   * - R41
     - Use an inherent factor only associated with a strong factor. In multi-factor, accompany biometrics with a cryptographic factor compliant with `RGS <https://cyber.gouv.fr/le-referentiel-general-de-securite-rgs>`__.
     - Biometric authentication via :issue:`WebAuthn support is planned <296>` but not yet implemented.
     - ❌
   * - R42
     - Favor in-person meeting when registering an inherent factor. Perform face-to-face identity verification for biometric enrollment.
     - This is an organizational enrollment procedure responsibility.
     - ⬜
