import json
from pathlib import Path

import httpx
import portpicker
import pytest

from integration.databases import get_database_config
from integration.databases.ldap import create_slapd_server
from integration.runners import DevRunner
from integration.runners import DockerRunner
from integration.runners import PackageRunner
from integration.runners import PyInstallerRunner
from integration.utils import extract_csrf_token

RUNNERS = {
    "dev": DevRunner,
    "docker": DockerRunner,
    "package": PackageRunner,
    "pyinstaller": PyInstallerRunner,
}

ALL_BUILDS = ["dev", "docker", "package", "pyinstaller"]
ALL_DATABASES = ["sqlite", "postgresql", "ldap"]

_cache: dict[str, dict] = {}


def _cache_key(build_mode: str, database_mode: str) -> str:
    return f"{build_mode}|{database_mode}"


def parse_build_spec(spec: str) -> tuple[str, str | None]:
    """Parse a build spec like 'pyinstaller:/path/to/binary' into (build_type, source)."""
    if ":" not in spec:
        return spec, None

    build_type, _, source = spec.partition(":")
    return build_type, source if source else None


def pytest_configure(config):
    """Prepare shared resources before workers start."""
    config.addinivalue_line(
        "markers",
        "requires_extra(name): skip test if the specified extra is not in --extras",
    )

    if hasattr(config, "workerinput"):
        # This is a xdist worker, skip preparation
        return

    project_root = Path(__file__).parent.parent
    requested_builds = config.getoption("--build", default=[])
    if not requested_builds:
        requested_builds = ALL_BUILDS

    extras = config.getoption("--extras", default=None)

    for spec in requested_builds:
        build_type, build_source = parse_build_spec(spec)
        if build_source:
            # Pre-built source provided, no preparation needed
            continue
        runner_cls = RUNNERS.get(build_type)
        if runner_cls:
            runner_cls.prepare(project_root, extras)


def pytest_addoption(parser):
    parser.addoption(
        "--build",
        action="append",
        default=[],
        help="Build method(s) to test. Can be specified multiple times. "
        "Format: BUILD_TYPE[:SOURCE]. "
        "BUILD_TYPE: dev, docker, package, pyinstaller. "
        "SOURCE (optional): pre-built source to skip building. "
        "Examples: --build dev, --build pyinstaller:/path/to/binary, "
        "--build docker:myimage:tag, --build package:canaille[sqlite]. "
        "Default: all builds.",
    )
    parser.addoption(
        "--database",
        action="append",
        default=[],
        help="Database backend(s) to test. Can be specified multiple times. "
        "Options: sqlite, postgresql, ldap. "
        "Default: all databases.",
    )
    parser.addoption(
        "--extras",
        default=None,
        help="Extras to install for package builds (comma-separated). "
        "The database extra is always added automatically. "
        "Examples: --extras=server, --extras=front,oidc,server. "
        "Default: front,oidc,captcha,server.",
    )


def pytest_generate_tests(metafunc):
    if "build_mode" not in metafunc.fixturenames:
        return

    requested_builds = metafunc.config.getoption("--build")
    if requested_builds:
        build_specs = []
        for spec in requested_builds:
            build_type, source = parse_build_spec(spec)
            if build_type not in ALL_BUILDS:
                raise ValueError(
                    f"Invalid build type '{build_type}'. "
                    f"Must be one of: {', '.join(ALL_BUILDS)}"
                )
            build_specs.append(spec)
    else:
        build_specs = ALL_BUILDS

    requested_databases = metafunc.config.getoption("--database")
    if requested_databases:
        for db in requested_databases:
            if db not in ALL_DATABASES:
                raise ValueError(
                    f"Invalid database '{db}'. "
                    f"Must be one of: {', '.join(ALL_DATABASES)}"
                )
        database_specs = requested_databases
    else:
        database_specs = ALL_DATABASES

    if "database_mode" in metafunc.fixturenames:
        metafunc.parametrize(
            "build_mode,database_mode",
            [(b, d) for b in build_specs for d in database_specs],
            ids=[f"{b}-{d}" for b in build_specs for d in database_specs],
        )
    else:
        metafunc.parametrize("build_mode", build_specs)


def pytest_runtest_setup(item):
    """Skip tests marked with requires_extra if the extra is not installed."""
    for marker in item.iter_markers(name="requires_extra"):
        extra = marker.args[0]
        extras = item.config.getoption("--extras") or ""
        if extras and extra not in extras.split(","):
            pytest.skip(f"requires '{extra}' extra (not in --extras={extras})")


def pytest_sessionfinish(session, exitstatus):
    """Cleanup all cached resources at end of session."""
    for cache in _cache.values():
        if "runner" in cache:
            if "server_handle" in cache:
                cache["runner"].stop_server(cache["server_handle"])
            cache["runner"].cleanup()


@pytest.fixture(scope="session")
def slapd_server():
    """Start a LDAP server for the test session."""
    server = create_slapd_server()
    try:
        yield server
    finally:
        server.stop()


@pytest.fixture
def canaille_runner(build_mode, database_mode, tmp_path_factory, request):
    """Build and return the appropriate Canaille runner."""
    build_type, build_source = parse_build_spec(build_mode)
    extras = request.config.getoption("--extras")
    key = _cache_key(build_mode, database_mode)
    if extras is not None:
        key = f"{key}|{extras}"

    if key not in _cache:
        _cache[key] = {}

    cache = _cache[key]
    if "runner" not in cache:
        project_root = Path(__file__).parent.parent
        runner_cls = RUNNERS[build_type]
        cache["runner"] = runner_cls.get_or_build(
            build_source, project_root, tmp_path_factory, database_mode, extras
        )

    return cache["runner"]


@pytest.fixture
def workdir(tmp_path_factory, build_mode, database_mode):
    """Create a temporary working directory for all subprocess calls."""
    key = _cache_key(build_mode, database_mode)
    if key not in _cache:
        _cache[key] = {}

    cache = _cache[key]
    if "workdir" not in cache:
        build_type, _ = parse_build_spec(build_mode)
        cache["workdir"] = tmp_path_factory.mktemp(
            f"workdir-{build_type}-{database_mode}"
        )

    return cache["workdir"]


@pytest.fixture
def config_path(workdir, build_mode, database_mode, request):
    """Create configuration file for the appropriate database backend."""
    key = _cache_key(build_mode, database_mode)
    cache = _cache[key]
    build_type, _ = parse_build_spec(build_mode)

    if "config_path" not in cache:
        config_file = workdir / "config.toml"

        base_config = """\
SECRET_KEY = "integration-test-secret-key"
TRUSTED_HOSTS = ["localhost", "127.0.0.1"]

[CANAILLE]
JAVASCRIPT = false
HTMX = false
"""
        db_config = get_database_config(database_mode)
        config_file.write_text(
            base_config + db_config.get_config(workdir, build_type, request)
        )
        cache["config_path"] = config_file

    return cache["config_path"]


@pytest.fixture
def installed_database(
    canaille_runner, config_path, workdir, build_mode, database_mode
):
    """Initialize the database with install and migrations."""
    key = _cache_key(build_mode, database_mode)
    cache = _cache[key]

    if "installed_database" not in cache:
        result = canaille_runner.run_command(["install"], config_path, workdir)
        if result.returncode != 0:
            pytest.fail(f"Install failed:\n{result.stdout}\n{result.stderr}")

        db_config = get_database_config(database_mode)
        db_config.setup(canaille_runner, config_path, workdir)

        cache["installed_database"] = True

    return cache["installed_database"]


@pytest.fixture
def user_data(
    canaille_runner, config_path, workdir, installed_database, build_mode, database_mode
):
    """Create a regular user via CLI and return the JSON output."""
    key = _cache_key(build_mode, database_mode)
    cache = _cache[key]

    if "user_data" not in cache:
        build_type, _ = parse_build_spec(build_mode)
        username = f"testuser-{build_type}"
        result = canaille_runner.run_command(
            [
                "create",
                "user",
                "--user-name",
                username,
                "--password",
                "testpassword123",
                "--emails",
                f"test-{build_type}@example.com",
                "--given-name",
                "Test",
                "--family-name",
                "User",
                "--formatted-name",
                "Test User",
            ],
            config_path,
            workdir,
        )
        if result.returncode != 0:
            pytest.fail(f"User creation failed:\n{result.stdout}\n{result.stderr}")

        cache["user_data"] = json.loads(result.stdout)
        cache["user_data"]["login"] = username

    return cache["user_data"]


@pytest.fixture
def admin_data(
    canaille_runner, config_path, workdir, installed_database, build_mode, database_mode
):
    """Create an admin user via CLI and return the JSON output."""
    key = _cache_key(build_mode, database_mode)
    cache = _cache[key]

    if "admin_data" not in cache:
        build_type, _ = parse_build_spec(build_mode)
        username = f"admin-{build_type}"
        result = canaille_runner.run_command(
            [
                "create",
                "user",
                "--user-name",
                username,
                "--password",
                "adminpassword123",
                "--emails",
                f"admin-{build_type}@example.com",
                "--given-name",
                "Admin",
                "--family-name",
                "User",
                "--formatted-name",
                "Admin User",
            ],
            config_path,
            workdir,
        )
        if result.returncode != 0:
            pytest.fail(f"Admin creation failed:\n{result.stdout}\n{result.stderr}")

        cache["admin_data"] = json.loads(result.stdout)
        cache["admin_data"]["login"] = username

    return cache["admin_data"]


@pytest.fixture
def canaille_server(
    canaille_runner,
    config_path,
    workdir,
    user_data,
    admin_data,
    build_mode,
    database_mode,
):
    """Start the canaille server and yield the base URL."""
    key = _cache_key(build_mode, database_mode)
    cache = _cache[key]

    if "server_url" not in cache:
        host = "127.0.0.1"
        port = portpicker.pick_unused_port()

        handle = canaille_runner.start_server(host, port, config_path, workdir)
        cache["server_handle"] = handle

        if not canaille_runner.wait_for_server(host, port):
            stdout, stderr = canaille_runner.get_server_logs(handle)
            canaille_runner.stop_server(handle)
            pytest.fail(f"Server failed to start:\nstdout: {stdout}\nstderr: {stderr}")

        cache["server_url"] = f"http://{host}:{port}"

    return cache["server_url"]


@pytest.fixture
def client(canaille_server):
    """Create an httpx client with cookie persistence."""
    with httpx.Client(base_url=canaille_server, follow_redirects=True) as client:
        yield client


@pytest.fixture
def logged_admin_client(canaille_server, admin_data):
    """Create an httpx client logged in as admin."""
    with httpx.Client(base_url=canaille_server, follow_redirects=True) as client:
        response = client.get("/login")
        csrf_token = extract_csrf_token(response.text)

        response = client.post(
            "/login",
            data={"login": admin_data["login"], "csrf_token": csrf_token},
        )
        csrf_token = extract_csrf_token(response.text)

        client.post(
            "/auth/password",
            data={"password": "adminpassword123", "csrf_token": csrf_token},
        )

        yield client


@pytest.fixture
def logged_user_client(canaille_server, user_data):
    """Create an httpx client logged in as regular user."""
    with httpx.Client(base_url=canaille_server, follow_redirects=True) as client:
        response = client.get("/login")
        csrf_token = extract_csrf_token(response.text)

        response = client.post(
            "/login",
            data={"login": user_data["login"], "csrf_token": csrf_token},
        )
        csrf_token = extract_csrf_token(response.text)

        client.post(
            "/auth/password",
            data={"password": "testpassword123", "csrf_token": csrf_token},
        )

        yield client
