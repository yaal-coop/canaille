import sys

from flask import Flask


def create_app(
    config: dict | None = None,
    backend=None,
    init_backend=None,
    env_file: str | None = None,
    env_prefix: str = "",
):
    """Application entry point.

    :param config: A configuration dict. This will take priority over any other configuration method.
    :param backend: An optional backend to force. If unset backend will be initialized according to the configuration.
    :param env_file: The path to an environment var file in which configuration can be loaded.
    :param env_prefix: The prefix to configuration environment vars.
    """
    from canaille.app.otp import setup_otp

    from .app.configuration import setup_config
    from .app.features import setup_features
    from .app.flask import setup_flask
    from .app.flask import setup_flask_blueprints
    from .app.flask import setup_flask_converters
    from .app.i18n import setup_i18n
    from .app.logging import setup_logging
    from .app.sentry import setup_sentry
    from .app.talisman import setup_talisman
    from .app.templating import setup_jinja
    from .app.templating import setup_themer
    from .backends import setup_backend

    app = Flask(__name__)
    with app.app_context():
        if not setup_config(
            app=app,
            config=config,
            env_file=env_file,
            env_prefix=env_prefix,
        ):  # pragma: no cover
            sys.exit(1)

    sentry_sdk = setup_sentry(app)
    try:
        setup_logging(app)
        backend = setup_backend(app, backend, init_backend)
        setup_features(app)
        setup_talisman(app)
        setup_flask_converters(app)
        setup_flask_blueprints(app)
        setup_jinja(app)
        setup_i18n(app)
        setup_themer(app)
        setup_flask(app)
        setup_otp(app)

        if app.features.has_oidc:  # pragma: no branch
            from .oidc.oauth import setup_oauth

            setup_oauth(app)

        if app.features.has_scim_client:
            from .scim.client import setup_scim_client

            setup_scim_client()

    except Exception as exc:  # pragma: no cover
        if sentry_sdk:
            sentry_sdk.capture_exception(exc)
        raise

    return app
