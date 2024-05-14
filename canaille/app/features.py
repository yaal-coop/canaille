class Features:
    def __init__(self, app):
        self.app = app

    @property
    def has_smtp(self):
        return bool(self.app.config["CANAILLE"]["SMTP"])

    @property
    def has_oidc(self):
        return "CANAILLE_OIDC" in self.app.config

    @property
    def has_password_recovery(self):
        return self.app.config["CANAILLE"]["ENABLE_PASSWORD_RECOVERY"]

    @property
    def has_registration(self):
        return self.app.config["CANAILLE"]["ENABLE_REGISTRATION"]

    @property
    def has_account_lockability(self):
        return self.app.backend.instance.has_account_lockability()

    @property
    def has_email_confirmation(self):
        return self.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] is True or (
            self.app.config["CANAILLE"]["EMAIL_CONFIRMATION"] is None and self.has_smtp
        )


def setup_features(app):
    app.features = Features(app)
