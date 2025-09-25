import uuid

from hypercorn.middleware import ProxyFixMiddleware  # pragma: no cover

from canaille import create_app  # pragma: no cover

app = create_app(env_file=".env")  # pragma: no cover

if app.config["SECRET_KEY"] is None:  # pragma: no cover
    app.logger.warning("Missing 'SECRET_KEY' configuration parameter.")
    app.config["SECRET_KEY"] = str(uuid.uuid4())

if proxy_mode := app.config["CANAILLE_HYPERCORN"]["PROXY_MODE"]:  # pragma: no cover
    trusted_hops = app.config["CANAILLE_HYPERCORN"]["PROXY_TRUSTED_HOPS"] or 1
    app = ProxyFixMiddleware(app, mode=proxy_mode, trusted_hops=trusted_hops)
