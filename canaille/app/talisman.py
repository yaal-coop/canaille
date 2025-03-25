from flask_talisman import Talisman


def setup_talisman(app):
    csp = {
        "default-src": "'self'",
        "font-src": "'self' data:",
    }
    Talisman(app, content_security_policy=csp, force_https=not app.config["TESTING"])
