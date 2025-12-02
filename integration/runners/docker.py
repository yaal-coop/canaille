import subprocess
import uuid
from pathlib import Path

import pytest

from .base import CanailleRunner


class DockerRunner(CanailleRunner):
    """Run Canaille via Docker container."""

    DEFAULT_IMAGE = "canaille:integration-test"
    CONTAINER_MOUNT = "/data"

    def __init__(self, image_name: str | None = None):
        self.image_name = image_name or self.DEFAULT_IMAGE
        self.containers: list[str] = []

    @classmethod
    def build(cls, project_root: Path) -> "DockerRunner":
        """Build Docker image from source and return a runner."""
        result = subprocess.run(
            ["docker", "build", "-t", cls.DEFAULT_IMAGE, str(project_root)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(f"Docker build failed:\n{result.stdout}\n{result.stderr}")
        return cls()

    def run_command(
        self, args: list[str], config_path: Path, workdir: Path
    ) -> subprocess.CompletedProcess:
        container_config_path = f"{self.CONTAINER_MOUNT}/{config_path.name}"
        return subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{workdir}:{self.CONTAINER_MOUNT}",
                "-e",
                f"CANAILLE_CONFIG={container_config_path}",
                self.image_name,
                *args,
            ],
            capture_output=True,
            text=True,
        )

    def start_server(
        self, host: str, port: int, config_path: Path, workdir: Path
    ) -> str:
        container_name = f"canaille-integration-{uuid.uuid4().hex[:8]}"
        container_config_path = f"{self.CONTAINER_MOUNT}/{config_path.name}"
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "-v",
                f"{workdir}:{self.CONTAINER_MOUNT}",
                "-e",
                f"CANAILLE_CONFIG={container_config_path}",
                "-p",
                f"{host}:{port}:8000",
                self.image_name,
                "run",
                "--bind",
                "0.0.0.0:8000",
            ],
            check=True,
            capture_output=True,
        )
        self.containers.append(container_name)
        return container_name

    def stop_server(self, handle: str) -> None:
        subprocess.run(
            ["docker", "stop", handle],
            capture_output=True,
        )
        subprocess.run(
            ["docker", "rm", "-f", handle],
            capture_output=True,
        )
        if handle in self.containers:
            self.containers.remove(handle)

    def get_server_logs(self, handle: str) -> tuple[str, str]:
        result = subprocess.run(
            ["docker", "logs", handle], capture_output=True, text=True
        )
        return result.stdout, result.stderr

    def cleanup(self) -> None:
        """Remove any remaining containers."""
        for container in self.containers:
            subprocess.run(["docker", "rm", "-f", container], capture_output=True)
        self.containers.clear()
