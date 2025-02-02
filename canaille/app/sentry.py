def setup_sentry(app):  # pragma: no cover
    if not app.config["CANAILLE"]["SENTRY_DSN"]:
        return None

    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

    except Exception:
        return None

    sentry_sdk.init(
        dsn=app.config["CANAILLE"]["SENTRY_DSN"], integrations=[FlaskIntegration()]
    )
    return sentry_sdk
