import json
import re
from pathlib import Path

import httpx
import portpicker
import pytest

from integration.runners import DevRunner
from integration.runners import DockerRunner
from integration.runners import PackageRunner
from integration.runners import PyInstallerRunner

ALL_BUILDS = ["dev", "docker", "package", "pyinstaller"]

# Cache for session-scoped resources per build mode
_build_cache: dict[str, dict] = {}


def parse_build_spec(spec: str) -> tuple[str, str | None]:
    """Parse a build spec like 'pyinstaller:/path/to/binary' into (build_type, source).

    For docker images with tags like 'docker:myimage:latest', handle multiple colons.
    """
    if ":" not in spec:
        return spec, None

    build_type, _, source = spec.partition(":")
    return build_type, source if source else None


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


def pytest_generate_tests(metafunc):
    if "build_mode" not in metafunc.fixturenames:
        return

    requested = metafunc.config.getoption("--build")
    if requested:
        # Parse specs and validate build types
        build_specs = []
        for spec in requested:
            build_type, source = parse_build_spec(spec)
            if build_type not in ALL_BUILDS:
                raise ValueError(
                    f"Invalid build type '{build_type}'. "
                    f"Must be one of: {', '.join(ALL_BUILDS)}"
                )
            build_specs.append(spec)
    else:
        build_specs = ALL_BUILDS
    metafunc.parametrize("build_mode", build_specs)


def pytest_sessionfinish(session, exitstatus):
    """Cleanup all cached resources at end of session."""
    for cache in _build_cache.values():
        if "runner" in cache:
            if "server_handle" in cache:
                cache["runner"].stop_server(cache["server_handle"])
            cache["runner"].cleanup()


def extract_csrf_token(html: str) -> str:
    """Extract CSRF token from HTML form."""
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if match:
        return match.group(1)
    match = re.search(r'value="([^"]+)"[^>]*name="csrf_token"', html)
    if match:
        return match.group(1)
    raise ValueError("CSRF token not found in HTML")


def _get_or_create_runner(build_spec, tmp_path_factory):
    """Get or create a runner for the given build spec."""
    build_type, build_source = parse_build_spec(build_spec)

    if build_spec not in _build_cache:
        _build_cache[build_spec] = {}

    cache = _build_cache[build_spec]

    if "runner" not in cache:
        project_root = Path(__file__).parent.parent

        if build_type == "pyinstaller":
            if build_source:
                # Use pre-built binary
                binary_path = Path(build_source)
                cache["runner"] = PyInstallerRunner(binary_path)
            else:
                # Build from source
                dist_dir = tmp_path_factory.mktemp(f"dist-{build_type}")
                cache["runner"] = PyInstallerRunner.build(project_root, dist_dir)

        elif build_type == "docker":
            if build_source:
                # Use pre-built image
                cache["runner"] = DockerRunner(image_name=build_source)
            else:
                # Build from source
                cache["runner"] = DockerRunner.build(project_root)

        elif build_type == "package":
            venv_path = tmp_path_factory.mktemp(f"venv-{build_type}")
            if build_source:
                source_path = Path(build_source)
                if source_path.suffix == ".whl":
                    # Use pre-built wheel
                    cache["runner"] = PackageRunner.from_wheel(source_path, venv_path)
                else:
                    # Assume it's a package spec like "canaille[sqlite,front]"
                    cache["runner"] = PackageRunner.from_package(
                        build_source, venv_path
                    )
            else:
                # Build from source
                dist_dir = tmp_path_factory.mktemp(f"dist-{build_type}")
                cache["runner"] = PackageRunner.build(project_root, dist_dir, venv_path)

        else:  # dev
            cache["runner"] = DevRunner()

    return cache["runner"]


@pytest.fixture
def canaille_runner(build_mode, tmp_path_factory):
    """Build and return the appropriate Canaille runner."""
    return _get_or_create_runner(build_mode, tmp_path_factory)


@pytest.fixture
def workdir(tmp_path_factory, build_mode):
    """Create a temporary working directory for all subprocess calls."""
    if build_mode not in _build_cache:
        _build_cache[build_mode] = {}

    cache = _build_cache[build_mode]
    if "workdir" not in cache:
        build_type, _ = parse_build_spec(build_mode)
        cache["workdir"] = tmp_path_factory.mktemp(f"workdir-{build_type}")

    return cache["workdir"]


@pytest.fixture
def config_path(workdir, build_mode):
    """Create a minimal configuration file with a temporary SQLite database."""
    cache = _build_cache[build_mode]
    build_type, _ = parse_build_spec(build_mode)

    if "config_path" not in cache:
        config_file = workdir / "config.toml"

        if build_type == "docker":
            db_path = f"{DockerRunner.CONTAINER_MOUNT}/canaille.sqlite"
        else:
            db_path = workdir / "canaille.sqlite"

        config_file.write_text(
            f"""\
SECRET_KEY = "integration-test-secret-key"
TRUSTED_HOSTS = ["localhost", "127.0.0.1"]

[CANAILLE]
DATABASE = "sql"
JAVASCRIPT = false
HTMX = false

[CANAILLE_SQL]
DATABASE_URI = "sqlite:///{db_path}"
"""
        )
        cache["config_path"] = config_file

    return cache["config_path"]


@pytest.fixture
def installed_database(canaille_runner, config_path, workdir, build_mode):
    """Initialize the database with install and migrations."""
    cache = _build_cache[build_mode]

    if "installed_database" not in cache:
        result = canaille_runner.run_command(["install"], config_path, workdir)
        if result.returncode != 0:
            pytest.fail(f"Install failed:\n{result.stdout}\n{result.stderr}")

        result = canaille_runner.run_command(["db", "upgrade"], config_path, workdir)
        if result.returncode != 0:
            pytest.fail(f"DB upgrade failed:\n{result.stdout}\n{result.stderr}")

        cache["installed_database"] = True

    return cache["installed_database"]


@pytest.fixture
def user_data(canaille_runner, config_path, workdir, installed_database, build_mode):
    """Create a regular user via CLI and return the JSON output."""
    cache = _build_cache[build_mode]

    if "user_data" not in cache:
        result = canaille_runner.run_command(
            [
                "create",
                "user",
                "--user-name",
                "testuser",
                "--password",
                "testpassword123",
                "--emails",
                "test@example.com",
                "--given-name",
                "Test",
                "--family-name",
                "User",
            ],
            config_path,
            workdir,
        )
        if result.returncode != 0:
            pytest.fail(f"User creation failed:\n{result.stdout}\n{result.stderr}")

        cache["user_data"] = json.loads(result.stdout)

    return cache["user_data"]


@pytest.fixture
def admin_data(canaille_runner, config_path, workdir, installed_database, build_mode):
    """Create an admin user via CLI and return the JSON output."""
    cache = _build_cache[build_mode]

    if "admin_data" not in cache:
        result = canaille_runner.run_command(
            [
                "create",
                "user",
                "--user-name",
                "admin",
                "--password",
                "adminpassword123",
                "--emails",
                "admin@example.com",
                "--given-name",
                "Admin",
                "--family-name",
                "User",
            ],
            config_path,
            workdir,
        )
        if result.returncode != 0:
            pytest.fail(f"Admin creation failed:\n{result.stdout}\n{result.stderr}")

        cache["admin_data"] = json.loads(result.stdout)

    return cache["admin_data"]


@pytest.fixture
def canaille_server(
    canaille_runner, config_path, workdir, user_data, admin_data, build_mode
):
    """Start the canaille server and yield the base URL."""
    cache = _build_cache[build_mode]

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
            data={"login": "admin", "csrf_token": csrf_token},
        )
        csrf_token = extract_csrf_token(response.text)

        client.post(
            "/auth/password",
            data={"password": "adminpassword123", "csrf_token": csrf_token},
        )

        yield client
