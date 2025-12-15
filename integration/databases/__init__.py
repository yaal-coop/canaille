from pathlib import Path
from typing import TYPE_CHECKING
from typing import Protocol

import pytest

if TYPE_CHECKING:
    from integration.runners.base import CanailleRunner


class DatabaseConfig(Protocol):
    """Protocol for database configuration providers."""

    def get_config(
        self, workdir: Path, build_type: str, request: pytest.FixtureRequest
    ) -> str:
        """Return TOML configuration string for this database backend."""
        ...

    def setup(
        self,
        runner: "CanailleRunner",
        config_path: Path,
        workdir: Path,
    ) -> None:
        """Run any database-specific setup after install (e.g., migrations)."""
        ...


def get_database_config(database_mode: str) -> DatabaseConfig:
    """Get the database configuration provider for the given mode."""
    from integration.databases import ldap as ldap_module
    from integration.databases import postgresql as postgresql_module
    from integration.databases import sqlite as sqlite_module

    configs: dict[str, DatabaseConfig] = {
        "sqlite": sqlite_module.SQLiteConfig(),
        "postgresql": postgresql_module.PostgreSQLConfig(),
        "ldap": ldap_module.LDAPConfig(),
    }
    return configs[database_mode]
