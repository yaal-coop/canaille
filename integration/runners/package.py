import os
import shutil
import signal
import subprocess
from pathlib import Path

import pytest

from .base import CanailleRunner

DEFAULT_EXTRAS = "front,oidc,sqlite,captcha,server"


class PackageRunner(CanailleRunner):
    """Run Canaille from a wheel installed in a dedicated venv."""

    def __init__(self, venv_path: Path):
        self.venv_path = venv_path
        self.canaille_cmd = venv_path / "bin" / "canaille"

    @classmethod
    def build(
        cls,
        project_root: Path,
        dist_dir: Path,
        venv_path: Path,
        extras: str = DEFAULT_EXTRAS,
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
        extras: str = DEFAULT_EXTRAS,
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
        result = subprocess.run(
            [
                uv_path,
                "pip",
                "install",
                "--python",
                str(venv_path / "bin" / "python"),
                f"{wheel_path}[{extras}]",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(f"uv pip install failed:\n{result.stdout}\n{result.stderr}")

        return cls(venv_path)

    @classmethod
    def from_package(
        cls,
        package_spec: str,
        venv_path: Path,
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

        return cls(venv_path)

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
