import uuid

from canaille import create_app  # pragma: no cover

app = create_app(env_file=".env")  # pragma: no cover

if app.config["SECRET_KEY"] is None:  # pragma: no cover
    app.logger.warning("Missing 'SECRET_KEY' configuration parameter.")
    app.config["SECRET_KEY"] = str(uuid.uuid4())
