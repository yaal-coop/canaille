class Features:
    def __init__(self, app):
        self.app = app

    @property
    def has_smtp(self):
        """Indicate whether the mail sending feature is enabled.

        This feature is required to :attr:`validate user email addresses <canaille.app.features.Features.has_email_confirmation>`, send email OTP passwords etc.
        It is controlled by the :attr:`CANAILLE.SMTP <canaille.core.configuration.CoreSettings.SMTP>` configuration parameter.
        """
        return bool(self.app.config["CANAILLE"]["SMTP"])

    @property
    def has_password_recovery(self):
        """Indicate whether the password recovery feature is enabled.

        It is controlled by the :attr:`CANAILLE.ENABLE_PASSWORD_RECOVERY <canaille.core.configuration.CoreSettings.ENABLE_PASSWORD_RECOVERY>` configuration parameter.
        """
        return self.app.config["CANAILLE"]["ENABLE_PASSWORD_RECOVERY"]

    @property
    def has_intruder_lockout(self):
        """Indicate whether the intruder lockout feature is enabled.

        It is controlled by the :attr:`CANAILLE.ENABLE_INTRUDER_LOCKOUT <canaille.core.configuration.CoreSettings.ENABLE_INTRUDER_LOCKOUT>` configuration parameter.
        """

        return self.app.config["CANAILLE"]["ENABLE_INTRUDER_LOCKOUT"]

    @property
    def otp_method(self):
        return self.app.config["CANAILLE"]["OTP_METHOD"]

    @property
    def has_otp(self):
        """Indicate whether the OTP authentication factor is enabled.

        It is controlled by the :attr:`CANAILLE.OTP_METHOD <canaille.core.configuration.CoreSettings.OTP_METHOD>` configuration parameter,
        and needs the ``otp`` extra package to be installed.
        """

        try:
            import otpauth  # noqa: F401

            return bool(self.app.config["CANAILLE"]["OTP_METHOD"])
        except ImportError:  # pragma: no cover
            return False

    @property
    def has_email_otp(self):
        """Indicate whether the email OTP authentication factor is enabled.

        It is controlled by the :attr:`CANAILLE.EMAIL_OTP <canaille.core.configuration.CoreSettings.EMAIL_OTP>` configuration parameter.
        """

        return bool(self.app.config["CANAILLE"]["EMAIL_OTP"])

    @property
    def has_sms_otp(self):
        """Indicate whether the SMS OTP authentication factor is enabled.

        It is controlled by the :attr:`CANAILLE.SMS_OTP <canaille.core.configuration.CoreSettings.SMS_OTP>` configuration parameter,
        and needs the ``smpp`` extra package to be installed.
        """

        try:
            import smpplib  # noqa: F401

            return self.app.config["CANAILLE"]["SMS_OTP"]
        except ImportError:  # pragma: no cover
            return False

    @property
    def has_registration(self):
        """Indicate whether the user account registration is enabled.

        It is controlled by the :attr:`CANAILLE.ENABLE_REGISTRATION <canaille.core.configuration.CoreSettings.ENABLE_REGISTRATION>` configuration parameter.
        """

        return self.app.config["CANAILLE"]["ENABLE_REGISTRATION"]

    @property
    def has_account_lockability(self):
        """Indicate whether the user accounts can be locked.

        It depends on the backend used by Canaille.
        This is only disabled for OpenLDAP versions under 2.6.
        """

        return self.app.backend.instance.has_account_lockability()

    @property
    def has_email_confirmation(self):
        """Indicate whether the user email confirmation is enabled.

        It is controlled by the :attr:`CANAILLE.EMAIL_CONFIRMATION <canaille.core.configuration.CoreSettings.EMAIL_CONFIRMATION>` configuration parameter.
        """

        return self.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] is True or (
            self.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] is None and self.has_smtp
        )

    @property
    def has_oidc(self):
        """Indicate whether the OIDC feature is enabled.

        This feature is required to make Canaille an authorization server for other applications and enable SSO.
        It is controlled by the :class:`CANAILLE_OIDC <canaille.oidc.configuration.OIDCSettings>` configuration parameter,
        and needs the ``oidc`` extra package to be installed.
        """

        try:
            import authlib  # noqa: F401

            return "CANAILLE_OIDC" in self.app.config
        except ImportError:  # pragma: no cover
            return False

    @property
    def has_scim_server(self):
        """Indicate whether the SCIM server feature is enabled.

        This feature is required to make Canaille a provisioning server.
        It is controlled by the :attr:`CANAILLE_SCIM.ENABLE_SERVER <canaille.scim.configuration.SCIMSettings.ENABLE_SERVER>` configuration parameter,
        and needs the ``scim`` extra package to be installed.
        """

        try:
            import scim2_models  # noqa: F401

            return (
                "CANAILLE_SCIM" in self.app.config
                and self.app.config["CANAILLE_SCIM"]["ENABLE_SERVER"]
            )
        except ImportError:  # pragma: no cover
            return False


def setup_features(app):
    app.features = Features(app)
