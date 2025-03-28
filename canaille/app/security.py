def setup_security(app):
    try:
        from flask_talisman import Talisman
    except ImportError:
        return

    csp = {
        "default-src": "'self'",
        "font-src": "'self' data:",
    }
    Talisman(
        app,
        content_security_policy=csp,
        force_https=app.config["CANAILLE"]["FORCE_HTTPS"],
        session_cookie_secure=app.config["CANAILLE"]["FORCE_HTTPS"],
    )
