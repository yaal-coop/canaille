import uuid

from asgiref.wsgi import WsgiToAsgi
from hypercorn.middleware import ProxyFixMiddleware  # pragma: no cover

import canaille


def create_app(config=None, backend=None, env_file=".env"):  # pragma: no cover
    app = canaille.create_app(config=config, backend=backend, env_file=env_file)

    if app.config["SECRET_KEY"] is None:
        app.logger.warning("Missing 'SECRET_KEY' configuration parameter.")
        app.config["SECRET_KEY"] = str(uuid.uuid4())

    if proxy_mode := app.config["CANAILLE_HYPERCORN"]["PROXY_MODE"]:
        trusted_hops = app.config["CANAILLE_HYPERCORN"]["PROXY_TRUSTED_HOPS"] or 1
        app = ProxyFixMiddleware(
            WsgiToAsgi(app), mode=proxy_mode, trusted_hops=trusted_hops
        )

    return app


app = create_app()
