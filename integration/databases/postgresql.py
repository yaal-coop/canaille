from pathlib import Path
from typing import TYPE_CHECKING

import psycopg2
import pytest

if TYPE_CHECKING:
    from integration.runners.base import CanailleRunner


class PostgreSQLConfig:
    """PostgreSQL database configuration provider."""

    def get_config(
        self, workdir: Path, build_type: str, request: pytest.FixtureRequest
    ) -> str:
        postgresql_proc = request.getfixturevalue("postgresql_proc")

        conn = psycopg2.connect(
            host=postgresql_proc.host,
            port=postgresql_proc.port,
            user=postgresql_proc.user,
            dbname="postgres",
        )
        conn.autocommit = True
        cursor = conn.cursor()
        db_name = f"canaille_integration_{build_type}"
        cursor.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        cursor.execute(f'CREATE DATABASE "{db_name}"')
        cursor.close()
        conn.close()

        uri = f"postgresql://{postgresql_proc.user}@{postgresql_proc.host}:{postgresql_proc.port}/{db_name}"
        return f"""\
DATABASE = "sql"

[CANAILLE_SQL]
DATABASE_URI = "{uri}"
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
