import pathlib

import click
from honcho.command import main

CURRENT_DIR = pathlib.Path(__file__).parent


@click.command()
@click.option("--backend", default="sql", help="The Canaille backend to use.")
def devserver(backend):
    argv = [
        "--env",
        str(CURRENT_DIR.parent / ".env"),
        "--procfile",
        str(CURRENT_DIR / f"Procfile-{backend}"),
        "start",
    ]
    main(argv)


if __name__ == "__main__":
    devserver()
