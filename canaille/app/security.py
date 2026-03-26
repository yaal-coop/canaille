def setup_security(app) -> None:
    try:
        from flask_talisman import Talisman
    except ImportError:
        return

    csp = {
        "default-src": "'self'",
        "font-src": "'self' data:",
        "img-src": "'self' blob: data: https:",
    }
    Talisman(
        app,
        content_security_policy=csp,
        force_https=app.config["CANAILLE"]["FORCE_HTTPS"],
        session_cookie_secure=app.config["CANAILLE"]["FORCE_HTTPS"],
    )
