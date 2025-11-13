import importlib.metadata
import multiprocessing
import sys

import click
from flask.cli import FlaskGroup
from flask.cli import ScriptInfo

from canaille import create_app

version = importlib.metadata.version("canaille")


def create_cli_app():  # pragma: no cover
    # Force the non-application of migrations
    return create_app(init_backend=False)


class LazyFlaskGroup(FlaskGroup):
    """FlaskGroup that registers commands lazily after app creation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._registered_features = None

    def _register_commands(self, ctx):
        """Register commands conditionally based on app features."""
        app = ctx.ensure_object(ScriptInfo).load_app()

        # Re-register commands if app features change (needed for tests with different configs)
        current_features = (app.features.has_oidc,)
        if self._registered_features == current_features:
            return

        import canaille.app.commands
        import canaille.backends.commands
        import canaille.core.commands

        canaille.app.commands.register(self)
        canaille.backends.commands.register(self)
        canaille.core.commands.register(self)
        if app.features.has_oidc:  # pragma: no cover
            import canaille.oidc.commands

            canaille.oidc.commands.register(self)

        self._registered_features = current_features

    def get_command(self, ctx, cmd_name):
        self._register_commands(ctx)
        return super().get_command(ctx, cmd_name)

    def list_commands(self, ctx):
        self._register_commands(ctx)
        return super().list_commands(ctx)


@click.group(
    cls=LazyFlaskGroup,
    create_app=create_cli_app,
    add_version_option=False,
    add_default_commands=False,
)
@click.version_option(version, prog_name="Canaille")
def cli():
    """Canaille management utilities."""


if __name__ == "__main__":  # pragma: no cover
    # Needed by pyinstaller (not just on Windows)
    # https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#multi-processing
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        multiprocessing.freeze_support()

    cli()
