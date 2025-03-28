def setup_security(app):
    try:
        from flask_talisman import Talisman
    except ImportError:
        return

    is_https = not app.config["TESTING"]
    csp = {
        "default-src": "'self'",
        "font-src": "'self' data:",
    }
    Talisman(
        app,
        content_security_policy=csp,
        force_https=is_https,
        session_cookie_secure=is_https,
    )
