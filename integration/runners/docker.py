import shutil
import subprocess
import uuid
from pathlib import Path

from .base import CanailleRunner


def get_container_runtime() -> str:
    """Return 'docker' or 'podman', whichever is available."""
    for cmd in ("docker", "podman"):
        if shutil.which(cmd):
            return cmd
    raise RuntimeError("Neither docker nor podman found")


def normalize_image_name(image_name: str, runtime: str) -> str:
    """Normalize image name for the container runtime.

    Podman requires 'localhost/' prefix to find local images,
    otherwise it searches remote registries.
    """
    if runtime == "podman" and "/" not in image_name:
        return f"localhost/{image_name}"
    return image_name


class DockerRunner(CanailleRunner):
    """Run Canaille via Docker/Podman container."""

    DEFAULT_IMAGE = "canaille:integration-test"
    CONTAINER_MOUNT = "/data"

    def __init__(
        self,
        image_name: str | None = None,
        network_host: bool = False,
        database_mode: str = "unknown",
    ):
        self.runtime = get_container_runtime()
        raw_image = image_name or self.DEFAULT_IMAGE
        self.image_name = normalize_image_name(raw_image, self.runtime)
        self.containers: list[str] = []
        self.network_host = network_host
        self.database_mode = database_mode

    @classmethod
    def get_or_build(
        cls,
        build_source: str | None,
        project_root: Path,
        tmp_path_factory,
        database_mode: str = "unknown",
        extras: str | None = None,
    ) -> "DockerRunner":
        if build_source:
            return cls(
                image_name=build_source, network_host=True, database_mode=database_mode
            )
        # Image is already built by prepare(), just return a runner
        return cls(network_host=True, database_mode=database_mode)

    def run_command(
        self, args: list[str], config_path: Path, workdir: Path
    ) -> subprocess.CompletedProcess:
        container_config_path = f"{self.CONTAINER_MOUNT}/{config_path.name}"
        cmd = [
            self.runtime,
            "run",
            "--rm",
            "-v",
            f"{workdir}:{self.CONTAINER_MOUNT}",
            "-e",
            f"CANAILLE_CONFIG={container_config_path}",
        ]
        if self.network_host:
            cmd.append("--network=host")
        cmd.extend([self.image_name, *args])
        return subprocess.run(cmd, capture_output=True, text=True)

    def start_server(
        self, host: str, port: int, config_path: Path, workdir: Path
    ) -> str:
        container_name = f"canaille-{self.database_mode}-{uuid.uuid4().hex[:8]}"
        container_config_path = f"{self.CONTAINER_MOUNT}/{config_path.name}"
        cmd = [
            self.runtime,
            "run",
            "-d",
            "--name",
            container_name,
            "--pids-limit=-1",
            "-v",
            f"{workdir}:{self.CONTAINER_MOUNT}",
            "-e",
            f"CANAILLE_CONFIG={container_config_path}",
        ]
        if self.network_host:
            cmd.extend(
                ["--network=host", self.image_name, "run", "--bind", f"{host}:{port}"]
            )
        else:
            cmd.extend(
                [
                    "-p",
                    f"{host}:{port}:8000",
                    self.image_name,
                    "run",
                    "--bind",
                    "0.0.0.0:8000",
                ]
            )
        subprocess.run(cmd, check=True, capture_output=True)
        self.containers.append(container_name)
        return container_name

    def stop_server(self, handle: str) -> None:
        subprocess.run(
            [self.runtime, "stop", handle],
            capture_output=True,
        )
        subprocess.run(
            [self.runtime, "rm", "-f", handle],
            capture_output=True,
        )
        if handle in self.containers:
            self.containers.remove(handle)

    def get_server_logs(self, handle: str) -> tuple[str, str]:
        result = subprocess.run(
            [self.runtime, "logs", handle], capture_output=True, text=True
        )
        return result.stdout, result.stderr

    def cleanup(self) -> None:
        """Remove any remaining containers."""
        for container in self.containers:
            subprocess.run([self.runtime, "rm", "-f", container], capture_output=True)
        self.containers.clear()

    @classmethod
    def prepare(cls, project_root: Path, extras: str | None = None) -> None:
        """Build container image once before tests run."""
        runtime = get_container_runtime()
        image_name = normalize_image_name(cls.DEFAULT_IMAGE, runtime)
        result = subprocess.run(
            [runtime, "build", "-t", image_name, str(project_root)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"{runtime} build failed:\n{result.stdout}\n{result.stderr}"
            )
