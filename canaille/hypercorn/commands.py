import sys

import click
from flask.cli import with_appcontext

try:
    import hypercorn  # noqa: F401

    HAS_HYPERCORN = True
except ImportError:  # pragma: no cover
    HAS_HYPERCORN = False


if HAS_HYPERCORN:  # pragma: no cover

    @click.command()
    @with_appcontext
    @click.option(
        "--config",
        default=None,
        help="Path to a TOML hypercorn configuration file.",
        type=click.Path(),
    )
    def run(config: str | None):
        """Run Canaille in a hypercorn application server.

        Have a look at the :doc:`Hypercorn configuration documentation <hypercorn:how_to_guides/configuring>` to find how to configure it.
        """
        from hypercorn.config import Config
        from hypercorn.run import run as hypercorn_run

        config_obj = Config.from_toml(config) if config else Config()
        config_obj.application_path = "canaille.app.server:app"
        exitcode = hypercorn_run(config_obj)
        sys.exit(exitcode)
