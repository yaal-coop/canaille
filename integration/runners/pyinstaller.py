import os
import signal
import subprocess
from pathlib import Path

import pytest

from .base import CanailleRunner


class PyInstallerRunner(CanailleRunner):
    """Run Canaille via PyInstaller binary."""

    def __init__(self, binary_path: Path):
        self.binary_path = binary_path

    @classmethod
    def build(cls, project_root: Path, dist_dir: Path) -> "PyInstallerRunner":
        """Build PyInstaller binary from source and return a runner."""
        import PyInstaller.__main__

        binary_path = dist_dir / "canaille" / "canaille"

        os.environ["PYINSTALLER_ONEDIR"] = "1"
        PyInstaller.__main__.run(
            [
                "--distpath",
                str(dist_dir),
                "--workpath",
                str(dist_dir / "build"),
                str(project_root / "canaille.spec"),
            ]
        )

        if not binary_path.exists():
            pytest.fail(f"Binary not found at {binary_path}")
        return cls(binary_path)

    def run_command(
        self, args: list[str], config_path: Path, workdir: Path
    ) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["CANAILLE_CONFIG"] = str(config_path)
        return subprocess.run(
            [str(self.binary_path), *args],
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
        return subprocess.Popen(
            [str(self.binary_path), "run", "--bind", f"{host}:{port}"],
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
