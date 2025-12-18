import os
import shutil
import signal
import subprocess
from pathlib import Path

import pytest

from .base import CanailleRunner

DEFAULT_EXTRAS = "front,oidc,captcha,server"

DATABASE_EXTRAS = {
    "sqlite": "sqlite",
    "postgresql": "postgresql",
    "ldap": "ldap",
}


class PackageRunner(CanailleRunner):
    """Run Canaille from a wheel installed in a dedicated venv."""

    SHARED_BUILD_DIR = ".integration-build/package"

    def __init__(self, venv_path: Path, extras: str):
        self.venv_path = venv_path
        self.extras = extras
        self.canaille_cmd = venv_path / "bin" / "canaille"

    @classmethod
    def prepare(cls, project_root: Path, extras: str | None = None) -> None:
        """Build wheel once before tests run."""
        dist_dir = project_root / cls.SHARED_BUILD_DIR
        dist_dir.mkdir(parents=True, exist_ok=True)

        # Clean old wheels
        for old_wheel in dist_dir.glob("*.whl"):
            old_wheel.unlink()

        result = subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(dist_dir)],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"uv build failed:\n{result.stdout}\n{result.stderr}")

        wheels = list(dist_dir.glob("*.whl"))
        if not wheels:
            raise RuntimeError(f"No wheel found in {dist_dir}")

    @classmethod
    def _get_shared_wheel(cls, project_root: Path) -> Path:
        """Get the shared wheel path built by prepare()."""
        dist_dir = project_root / cls.SHARED_BUILD_DIR
        wheels = list(dist_dir.glob("*.whl"))
        if not wheels:
            raise RuntimeError(f"No wheel found in {dist_dir}. Was prepare() called?")
        return wheels[0]

    @classmethod
    def get_or_build(
        cls,
        build_source: str | None,
        project_root: Path,
        tmp_path_factory,
        database_mode: str = "unknown",
        extras: str | None = None,
    ) -> "PackageRunner":
        db_extra = DATABASE_EXTRAS.get(database_mode, "sqlite")
        base_extras = extras if extras is not None else DEFAULT_EXTRAS
        full_extras = f"{base_extras},{db_extra}" if base_extras else db_extra

        venv_path = tmp_path_factory.mktemp("venv-package")
        if build_source:
            source_path = Path(build_source)
            if source_path.suffix == ".whl":
                return cls.from_wheel(source_path, venv_path, full_extras)
            return cls.from_package(build_source, venv_path, full_extras)

        # Use shared wheel built by prepare()
        wheel_path = cls._get_shared_wheel(project_root)
        return cls.from_wheel(wheel_path, venv_path, full_extras)

    @classmethod
    def build(
        cls,
        project_root: Path,
        dist_dir: Path,
        venv_path: Path,
        extras: str,
    ) -> "PackageRunner":
        """Build wheel, create venv, install and return a runner."""
        # Build the wheel with uv
        result = subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(dist_dir)],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(f"uv build failed:\n{result.stdout}\n{result.stderr}")

        # Find the built wheel
        wheels = list(dist_dir.glob("*.whl"))
        if not wheels:
            pytest.fail(f"No wheel found in {dist_dir}")
        wheel_path = wheels[0]

        return cls.from_wheel(wheel_path, venv_path, extras)

    @classmethod
    def from_wheel(
        cls,
        wheel_path: Path,
        venv_path: Path,
        extras: str,
    ) -> "PackageRunner":
        """Create venv, install wheel and return a runner."""
        uv_path = shutil.which("uv")

        # Create venv
        result = subprocess.run(
            [uv_path, "venv", str(venv_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(f"uv venv failed:\n{result.stdout}\n{result.stderr}")

        # Install the wheel with necessary extras using uv pip
        package_spec = f"{wheel_path}[{extras}]" if extras else str(wheel_path)
        result = subprocess.run(
            [
                uv_path,
                "pip",
                "install",
                "--python",
                str(venv_path / "bin" / "python"),
                package_spec,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(f"uv pip install failed:\n{result.stdout}\n{result.stderr}")

        return cls(venv_path, extras)

    @classmethod
    def from_package(
        cls,
        package_spec: str,
        venv_path: Path,
        extras: str = "",
    ) -> "PackageRunner":
        """Create venv, install package from PyPI and return a runner."""
        uv_path = shutil.which("uv")

        # Create venv
        result = subprocess.run(
            [uv_path, "venv", str(venv_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(f"uv venv failed:\n{result.stdout}\n{result.stderr}")

        # Install the package using uv pip
        install_spec = f"{package_spec}[{extras}]" if extras else package_spec
        result = subprocess.run(
            [
                uv_path,
                "pip",
                "install",
                "--python",
                str(venv_path / "bin" / "python"),
                install_spec,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(f"uv pip install failed:\n{result.stdout}\n{result.stderr}")

        return cls(venv_path, extras)

    def run_command(
        self, args: list[str], config_path: Path, workdir: Path
    ) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["CANAILLE_CONFIG"] = str(config_path)
        env["PATH"] = f"{self.venv_path / 'bin'}:{env.get('PATH', '')}"
        return subprocess.run(
            [str(self.canaille_cmd), *args],
            env=env,
            cwd=workdir,
            capture_output=True,
            text=True,
        )

    def start_server(
        self, host: str, port: int, config_path: Path, workdir: Path
    ) -> subprocess.Popen:
        env = os.environ.copy()
        env["CANAILLE_CONFIG"] = str(config_path)
        env["PATH"] = f"{self.venv_path / 'bin'}:{env.get('PATH', '')}"
        return subprocess.Popen(
            [str(self.canaille_cmd), "run", "--bind", f"{host}:{port}"],
            env=env,
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def stop_server(self, handle: subprocess.Popen) -> None:
        handle.send_signal(signal.SIGTERM)
        try:
            handle.wait(timeout=10)
        except subprocess.TimeoutExpired:
            handle.kill()
            handle.wait()

    def get_server_logs(self, handle: subprocess.Popen) -> tuple[str, str]:
        stdout, stderr = handle.communicate(timeout=5)
        return stdout.decode(), stderr.decode()
