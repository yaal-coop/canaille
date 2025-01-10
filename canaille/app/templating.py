import os

import flask

try:
    import flask_themer
except ImportError:
    flask_themer = None


if flask_themer:
    render_template = flask_themer.render_template

    def setup_themer(app):
        theme_config = app.config["CANAILLE"]["THEME"]
        additional_themes_dir = (
            os.path.abspath(os.path.dirname(theme_config))
            if theme_config and os.path.exists(theme_config)
            else None
        )
        themer = flask_themer.Themer(
            app,
            loaders=[flask_themer.FileSystemThemeLoader(additional_themes_dir)]
            if additional_themes_dir
            else None,
        )

        @themer.current_theme_loader
        def get_current_theme():
            # if config['THEME'] may be a theme name or a path
            return app.config["CANAILLE"]["THEME"].split("/")[-1]


else:  # pragma: no cover
    render_template = flask.render_template


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
            "logo_url": app.config["CANAILLE"]["LOGO"],
            "favicon_url": app.config["CANAILLE"]["FAVICON"]
            or app.config["CANAILLE"]["LOGO"],
            "website_name": app.config["CANAILLE"]["NAME"],
            "user": current_user(),
            "menu": True,
            "request_is_boosted": request_is_boosted(),
            "request_is_partial": request_is_partial(),
            "features": app.features,
        }
