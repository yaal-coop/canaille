import sys

import click
from flask import current_app
from flask.cli import with_appcontext
from pydanclick import from_pydantic

from canaille.hypercorn.configuration import HypercornSettings

try:
    import hypercorn  # noqa: F401

    HAS_HYPERCORN = True
except ImportError:  # pragma: no cover
    HAS_HYPERCORN = False


if HAS_HYPERCORN:  # pragma: no cover
    from hypercorn.config import Config
    from hypercorn.run import run as hypercorn_run

    # hotfix for until we can configure this by tweaking HypercornSettings
    # until then, it is needed to set-up the options explicitly
    # https://github.com/felix-martel/pydanclick/issues/30
    @click.command()
    @click.option("--bind", multiple=True, help="The TCP host/address to bind to.")
    @click.option(
        "--insecure-bind",
        multiple=True,
        help="The TCP host/address to bind to for insecure connections.",
    )
    @click.option("--quic-bind", multiple=True, help="The UDP socket to bind for QUIC.")
    @click.option(
        "--alpn-protocols", multiple=True, help="The ALPN protocols to advertise."
    )
    @click.option(
        "--alt-svc-headers",
        multiple=True,
        help="The alt-svc header values to advertise.",
    )
    @click.option(
        "--server-names", multiple=True, help="A comma separated list of server names."
    )
    @from_pydantic(
        "settings",
        HypercornSettings,
        exclude=[
            "BIND",
            "INSECURE_BIND",
            "QUIC_BIND",
            "ALPN_PROTOCOLS",
            "ALT_SVC_HEADERS",
            "SERVER_NAMES",
        ],
    )
    @with_appcontext
    def run(
        bind,
        insecure_bind,
        quic_bind,
        alpn_protocols,
        alt_svc_headers,
        server_names,
        settings: HypercornSettings,
    ):
        """Run Canaille in a hypercorn application server.

        Configuration is loaded from environment variables with CANAILLE_HYPERCORN_ prefix,
        and can be overridden with command-line options.

        Have a look at the :doc:`Hypercorn configuration documentation <hypercorn:how_to_guides/configuring>` to find how to configure it.
        """
        config_dict = current_app.config["CANAILLE_HYPERCORN"]
        cli_config = settings.model_dump(exclude_unset=True)

        # Add manual list options
        if bind:
            cli_config["BIND"] = list(bind)
        if insecure_bind:
            cli_config["INSECURE_BIND"] = list(insecure_bind)
        if quic_bind:
            cli_config["QUIC_BIND"] = list(quic_bind)
        if alpn_protocols:
            cli_config["ALPN_PROTOCOLS"] = list(alpn_protocols)
        if alt_svc_headers:
            cli_config["ALT_SVC_HEADERS"] = list(alt_svc_headers)
        if server_names:
            cli_config["SERVER_NAMES"] = list(server_names)

        merged_config = {**config_dict, **cli_config}
        lowercase_config = {
            key.lower(): value
            for key, value in merged_config.items()
            if value is not None and value != []
        }
        config_obj = Config.from_mapping(lowercase_config)

        config_obj.application_path = "canaille.hypercorn.app:app"
        exitcode = hypercorn_run(config_obj)
        sys.exit(exitcode)
