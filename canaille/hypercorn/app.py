import uuid

from asgiref.wsgi import WsgiToAsgi
from werkzeug.middleware.proxy_fix import ProxyFix

import canaille


def create_app(
    config=None, backend=None, env_file=".env", wrap_asgi=True
):  # pragma: no cover
    """Create a Hypercorn-ready ASGI application with proxy support.

    This function creates a Flask application and applies the ProxyFix middleware
    if PROXY_MODE is configured, then wraps it with WsgiToAsgi for ASGI compatibility.

    :param config: Optional configuration dict to pass to create_app
    :param backend: Optional backend to pass to create_app
    :param env_file: Environment file to load
    :param wrap_asgi: If True, wrap the Flask app with WsgiToAsgi
    :return: ASGI application (WsgiToAsgi wrapped Flask app) or Flask app if wrap_asgi=False
    """
    app = canaille.create_app(config=config, backend=backend, env_file=env_file)

    if app.config["SECRET_KEY"] is None:
        app.logger.warning("Missing 'SECRET_KEY' configuration parameter.")
        app.config["SECRET_KEY"] = str(uuid.uuid4())

    if app.config["CANAILLE_HYPERCORN"]["PROXY_MODE"]:
        trusted_hops = app.config["CANAILLE_HYPERCORN"]["PROXY_TRUSTED_HOPS"] or 1

        # Apply ProxyFix at WSGI level so Flask's url_for() generates correct URLs
        # x_for=trusted_hops: trust X-Forwarded-For with N proxies
        # x_proto=trusted_hops: trust X-Forwarded-Proto with N proxies
        # x_host=trusted_hops: trust X-Forwarded-Host with N proxies
        # x_port=trusted_hops: trust X-Forwarded-Port with N proxies
        # x_prefix=trusted_hops: trust X-Forwarded-Prefix with N proxies
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=trusted_hops,
            x_proto=trusted_hops,
            x_host=trusted_hops,
            x_port=trusted_hops,
            x_prefix=trusted_hops,
        )

    if wrap_asgi:
        return WsgiToAsgi(app)

    return app


app = create_app()  # pragma: no cover
