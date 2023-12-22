import os

import flask

try:
    import flask_themer
except ImportError:
    flask_themer = None


if flask_themer:
    render_template = flask_themer.render_template

    def setup_themer(app):
        additional_themes_dir = (
            os.path.abspath(os.path.dirname(app.config["THEME"]))
            if app.config.get("THEME") and os.path.exists(app.config["THEME"])
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
            # if config['THEME'] may be a theme name or an absolute path
            return app.config.get("THEME", "default").split("/")[-1]

        @app.errorhandler(400)
        def bad_request(error):
            return render_template("error.html", description=error, error_code=400), 400

        @app.errorhandler(403)
        def unauthorized(error):
            return render_template("error.html", description=error, error_code=403), 403

        @app.errorhandler(404)
        def page_not_found(error):
            return render_template("error.html", description=error, error_code=404), 404

        @app.errorhandler(500)
        def server_error(error):  # pragma: no cover
            return render_template("error.html", description=error, error_code=500), 500

else:  # pragma: no cover
    render_template = flask.render_template

    def setup_themer(app):
        return
