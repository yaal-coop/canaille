import subprocess

import pytest

from canaille.app.configuration import settings_factory
from canaille.backends.sql.backend import SQLBackend


@pytest.fixture(scope="session")
def postgresql_template_dump(tmp_path_factory, postgresql_proc):
    """Create a pre-migrated PostgreSQL database dump once per test session.

    This creates a template database with all Alembic migrations applied,
    dumps it to a SQL file, and returns the dump path for restoration in
    each test.
    """
    pytest.importorskip("pytest_postgresql")
    import psycopg2

    proc_info = postgresql_proc
    template_dbname = "canaille_template"

    conn = psycopg2.connect(
        host=proc_info.host,
        port=proc_info.port,
        user=proc_info.user,
        dbname="postgres",
    )
    conn.autocommit = True
    cursor = conn.cursor()

    cursor.execute(f'DROP DATABASE IF EXISTS "{template_dbname}"')
    cursor.execute(f'CREATE DATABASE "{template_dbname}"')
    cursor.close()
    conn.close()

    uri = f"postgresql://{proc_info.user}@{proc_info.host}:{proc_info.port}/{template_dbname}"

    template_config = {
        "SECRET_KEY": "template-secret-key",
        "CANAILLE": {
            "DATABASE": "sql",
        },
        "CANAILLE_SQL": {
            "DATABASE_URI": uri,
            "PASSWORD_SCHEMES": "plaintext",
            "AUTO_MIGRATE": True,
        },
    }

    config_obj = settings_factory(template_config)
    config_dict = config_obj.model_dump()
    backend = SQLBackend(config_dict)

    from canaille import create_app

    app = create_app(config_dict)
    with app.app_context():
        backend.alembic.upgrade()

    backend.engine.dispose()

    dump_dir = tmp_path_factory.mktemp("postgresql_dumps")
    dump_path = dump_dir / "template.sql"

    subprocess.run(
        [
            "pg_dump",
            "--no-owner",
            "--no-acl",
            "-h",
            proc_info.host,
            "-p",
            str(proc_info.port),
            "-U",
            proc_info.user,
            "-d",
            template_dbname,
            "-f",
            str(dump_path),
        ],
        check=True,
    )

    yield dump_path

    conn = psycopg2.connect(
        host=proc_info.host,
        port=proc_info.port,
        user=proc_info.user,
        dbname="postgres",
    )
    conn.autocommit = True
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{template_dbname}'
        AND pid <> pg_backend_pid()
        """
    )
    cursor.execute(f'DROP DATABASE IF EXISTS "{template_dbname}"')
    cursor.close()
    conn.close()


@pytest.fixture
def postgresql_configuration(configuration, request):
    """Configure Canaille to use PostgreSQL test database."""
    pytest.importorskip("pytest_postgresql")

    postgresql = request.getfixturevalue("postgresql")
    info = postgresql.info
    uri = f"postgresql://{info.user}@{info.host}:{info.port}/{info.dbname}"

    configuration["CANAILLE"]["DATABASE"] = "sql"
    configuration["CANAILLE_SQL"] = {
        "DATABASE_URI": uri,
        "PASSWORD_SCHEMES": "plaintext",
    }
    yield configuration
    del configuration["CANAILLE_SQL"]


@pytest.fixture
def postgresql_backend(postgresql_configuration, postgresql_template_dump, request):
    postgresql = request.getfixturevalue("postgresql")
    info = postgresql.info

    subprocess.run(
        [
            "psql",
            "-h",
            info.host,
            "-p",
            str(info.port),
            "-U",
            info.user,
            "-d",
            info.dbname,
            "-f",
            str(postgresql_template_dump),
            "-q",
        ],
        check=True,
    )

    postgresql_configuration["CANAILLE_SQL"]["AUTO_MIGRATE"] = False

    config_obj = settings_factory(postgresql_configuration)
    config_dict = config_obj.model_dump()
    backend = SQLBackend(config_dict)
    with backend.session():
        yield backend
