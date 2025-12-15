import subprocess
import time
from abc import ABC
from abc import abstractmethod
from pathlib import Path

import httpx


class CanailleRunner(ABC):
    """Abstract base class for running Canaille commands."""

    @abstractmethod
    def run_command(
        self, args: list[str], config_path: Path, workdir: Path
    ) -> subprocess.CompletedProcess:
        """Run a Canaille command and return the result."""

    @abstractmethod
    def start_server(
        self, host: str, port: int, config_path: Path, workdir: Path
    ) -> object:
        """Start the Canaille server and return a handle to stop it."""

    @abstractmethod
    def stop_server(self, handle: object) -> None:
        """Stop the Canaille server."""

    def cleanup(self) -> None:  # noqa: B027
        """Cleanup any resources created by this runner."""

    @classmethod  # noqa: B027
    def prepare(cls, project_root: Path) -> None:
        """Prepare shared resources before tests run (called once by master)."""

    @abstractmethod
    def get_server_logs(self, handle: object) -> tuple[str, str]:
        """Get stdout and stderr from a server handle."""

    def wait_for_server(self, host: str, port: int, timeout: float = 30.0) -> bool:
        """Wait until the server is ready to handle HTTP requests."""
        start = time.time()
        url = f"http://{host}:{port}/about"
        while time.time() - start < timeout:
            try:
                with httpx.Client(timeout=2.0) as client:
                    response = client.get(url)
                    if response.status_code == 200:
                        return True
            except (httpx.ConnectError, httpx.ReadError, httpx.TimeoutException):
                pass
            time.sleep(0.5)
        return False
