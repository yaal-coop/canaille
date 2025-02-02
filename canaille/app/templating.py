import os

import flask
from flask import current_app

from canaille.app import DOCUMENTATION_URL

try:
    import flask_themer
except ImportError:
    flask_themer = None


def render_template(*args, **kwargs):
    if flask_themer and current_app.config["CANAILLE"]["THEME"]:
        return flask_themer.render_template(*args, **kwargs)

    return flask.render_template(*args, **kwargs)


def setup_themer(app):
    theme_path = app.config["CANAILLE"]["THEME"]

    if not theme_path:
        with app.app_context():

            @current_app.context_processor
            def global_processor():
                return {"theme": lambda theme: theme}

        return

    theme_path = os.path.abspath(theme_path)
    themes_dir, theme_name = theme_path.rsplit("/", 1)

    themer = flask_themer.Themer(
        app, loaders=[flask_themer.FileSystemThemeLoader(themes_dir)]
    )

    @themer.current_theme_loader
    def get_current_theme():
        return theme_name


def setup_jinja(app):
    from canaille.app.forms import password_strength_calculator

    app.jinja_env.filters["len"] = len
    app.jinja_env.filters["password_strength"] = password_strength_calculator
    app.jinja_env.policies["ext.i18n.trimmed"] = True

    @app.context_processor
    def global_processor():
        from canaille.app.flask import request_is_boosted
        from canaille.app.flask import request_is_partial
        from canaille.app.session import current_user

        return {
            "debug": app.debug or app.config.get("TESTING", False),
            "documentation_url": DOCUMENTATION_URL,
            "logo_url": app.config["CANAILLE"]["LOGO"],
            "favicon_url": app.config["CANAILLE"]["FAVICON"]
            or app.config["CANAILLE"]["LOGO"],
            "website_name": app.config["CANAILLE"]["NAME"],
            "user": current_user(),
            "menu": True,
            "request_is_boosted": request_is_boosted(),
            "request_is_partial": request_is_partial(),
            "features": app.features,
            "no_secret_key": app.no_secret_key,
        }
