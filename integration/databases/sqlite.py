from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from integration.runners import DockerRunner

if TYPE_CHECKING:
    from integration.runners.base import CanailleRunner


class SQLiteConfig:
    """SQLite database configuration provider."""

    def get_config(
        self, workdir: Path, build_type: str, request: pytest.FixtureRequest
    ) -> str:
        if build_type == "docker":
            db_path = f"{DockerRunner.CONTAINER_MOUNT}/canaille.sqlite"
        else:
            db_path = workdir / "canaille.sqlite"

        return f"""\
DATABASE = "sql"

[CANAILLE_SQL]
DATABASE_URI = "sqlite:///{db_path}"
"""

    def setup(
        self,
        runner: "CanailleRunner",
        config_path: Path,
        workdir: Path,
    ) -> None:
        result = runner.run_command(["db", "upgrade"], config_path, workdir)
        if result.returncode != 0:
            pytest.fail(f"DB upgrade failed:\n{result.stdout}\n{result.stderr}")
