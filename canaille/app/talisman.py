from flask_talisman import Talisman


def setup_talisman(app):
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
