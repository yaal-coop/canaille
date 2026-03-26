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
    if database_mode == "sqlite":
        from integration.databases import sqlite as sqlite_module

        return sqlite_module.SQLiteConfig()
    elif database_mode == "postgresql":
        from integration.databases import postgresql as postgresql_module

        return postgresql_module.PostgreSQLConfig()
    elif database_mode == "ldap":
        from integration.databases import ldap as ldap_module

        return ldap_module.LDAPConfig()
    else:
        raise ValueError(f"Unknown database mode: {database_mode}")
