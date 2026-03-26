import os
import shutil
import signal
import subprocess
from pathlib import Path

from .base import CanailleRunner


class DevRunner(CanailleRunner):
    """Run Canaille directly from the development environment."""

    def __init__(self):
        self.canaille_cmd = shutil.which("canaille")
        if not self.canaille_cmd:
            raise RuntimeError("canaille command not found in PATH")

    @classmethod
    def get_or_build(
        cls,
        build_source: str | None,
        project_root: Path,
        tmp_path_factory,
        database_mode: str = "unknown",
        extras: str | None = None,
    ) -> "DevRunner":
        return cls()

    def run_command(
        self, args: list[str], config_path: Path, workdir: Path
    ) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["CANAILLE_CONFIG"] = str(config_path)
        return subprocess.run(
            [self.canaille_cmd, *args],
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
            [self.canaille_cmd, "run", "--bind", f"{host}:{port}"],
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
