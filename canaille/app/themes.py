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
