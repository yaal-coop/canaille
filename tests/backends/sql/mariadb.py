import getpass
import subprocess

import pytest
from pytest_mysql import factories

from canaille.app.configuration import settings_factory
from canaille.backends.sql.backend import SQLBackend

mariadb_proc = factories.mysql_proc(
    mysqld_exec="mariadbd",
    admin_executable="mariadb-admin",
    mysqld_safe="mariadbd-safe",
    install_db="mariadb-install-db",
    user=getpass.getuser(),
    # Each xdist worker runs its own server, so keep the redo log small.
    # The server is not in UTC, so that time zone mistakes show.
    params="--innodb-log-file-size=8M --default-time-zone=+02:00",
)

# The default collation of MariaDB 11.
mariadb_database = factories.mysql(
    "mariadb_proc",
    dbname="canaille",
    charset="utf8mb4",
    collation="utf8mb4_uca1400_ai_ci",
)


def mariadb_uri(process, dbname):
    return f"mariadb+pymysql://{process.user}@localhost/{dbname}?unix_socket={process.unixsocket}"


def mariadb_client(process, *args):
    return [
        "mariadb",
        f"--socket={process.unixsocket}",
        f"--user={process.user}",
        *args,
    ]


@pytest.fixture(scope="session")
def mariadb_template_dump(tmp_path_factory, mariadb_proc):
    """Create a pre-migrated MariaDB database dump once per test session."""
    template_dbname = "canaille_template"
    subprocess.run(
        mariadb_client(
            mariadb_proc,
            "--execute",
            f"DROP DATABASE IF EXISTS {template_dbname}; "
            f"CREATE DATABASE {template_dbname} "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_uca1400_ai_ci",
        ),
        check=True,
    )

    template_config = {
        "SECRET_KEY": "template-secret-key",
        "CANAILLE": {
            "DATABASE": "sql",
        },
        "CANAILLE_SQL": {
            "DATABASE_URI": mariadb_uri(mariadb_proc, template_dbname),
            "PASSWORD_SCHEMES": "plaintext",
            "AUTO_MIGRATE": True,
        },
    }

    config_dict = settings_factory(template_config).model_dump()
    backend = SQLBackend(config_dict)

    from canaille import create_app

    app = create_app(config_dict)
    with app.app_context():
        backend.alembic.upgrade()

    backend.engine.dispose()

    dump_path = tmp_path_factory.mktemp("mariadb_dumps") / "template.sql"
    with open(dump_path, "w") as dump:
        subprocess.run(
            [
                "mariadb-dump",
                f"--socket={mariadb_proc.unixsocket}",
                f"--user={mariadb_proc.user}",
                template_dbname,
            ],
            stdout=dump,
            check=True,
        )

    yield dump_path

    subprocess.run(
        mariadb_client(
            mariadb_proc, "--execute", f"DROP DATABASE IF EXISTS {template_dbname}"
        ),
        check=True,
    )


@pytest.fixture
def mariadb_configuration(configuration, mariadb_proc, mariadb_database):
    """Configure Canaille to use MariaDB test database."""
    configuration["CANAILLE"]["DATABASE"] = "sql"
    configuration["CANAILLE_SQL"] = {
        "DATABASE_URI": mariadb_uri(mariadb_proc, "canaille"),
        "PASSWORD_SCHEMES": "plaintext",
    }
    yield configuration
    del configuration["CANAILLE_SQL"]


@pytest.fixture
def mariadb_backend(mariadb_configuration, mariadb_template_dump, mariadb_proc):
    with open(mariadb_template_dump) as dump:
        subprocess.run(
            mariadb_client(mariadb_proc, "canaille"),
            stdin=dump,
            check=True,
        )

    mariadb_configuration["CANAILLE_SQL"]["AUTO_MIGRATE"] = False

    config_dict = settings_factory(mariadb_configuration).model_dump()
    backend = SQLBackend(config_dict)
    with backend.session():
        yield backend
