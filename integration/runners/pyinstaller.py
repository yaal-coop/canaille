import os
import shutil
import signal
import subprocess
from pathlib import Path

import PyInstaller.__main__

from .base import CanailleRunner


class PyInstallerRunner(CanailleRunner):
    """Run Canaille via PyInstaller binary."""

    SHARED_BUILD_DIR = ".integration-build/pyinstaller"

    def __init__(self, binary_path: Path):
        self.binary_path = binary_path

    @classmethod
    def prepare(cls, project_root: Path, extras: str | None = None) -> None:
        """Build PyInstaller binary once before tests run."""
        dist_dir = project_root / cls.SHARED_BUILD_DIR

        # Clean and recreate
        if dist_dir.exists():
            shutil.rmtree(dist_dir)
        dist_dir.mkdir(parents=True)

        binary_path = dist_dir / "canaille" / "canaille"

        env_backup = os.environ.get("CANAILLE_CONFIG")
        temp_config = dist_dir / "pyinstaller_build.toml"
        temp_config.write_text(f"""\
SECRET_KEY = "build-only"
[CANAILLE_SQL]
DATABASE_URI = "sqlite:///{dist_dir}/build.sqlite"
""")
        os.environ["CANAILLE_CONFIG"] = str(temp_config)
        os.environ["PYINSTALLER_ONEDIR"] = "1"
        try:
            PyInstaller.__main__.run(
                [
                    "--distpath",
                    str(dist_dir),
                    "--workpath",
                    str(dist_dir / "build"),
                    str(project_root / "canaille.spec"),
                ]
            )
        finally:
            if env_backup is not None:
                os.environ["CANAILLE_CONFIG"] = env_backup
            else:
                os.environ.pop("CANAILLE_CONFIG", None)

        if not binary_path.exists():
            raise RuntimeError(f"Binary not found at {binary_path}")

    @classmethod
    def _get_shared_binary(cls, project_root: Path) -> Path:
        """Get the shared binary path built by prepare()."""
        binary_path = project_root / cls.SHARED_BUILD_DIR / "canaille" / "canaille"
        if not binary_path.exists():
            raise RuntimeError(
                f"Binary not found at {binary_path}. Was prepare() called?"
            )
        return binary_path

    @classmethod
    def get_or_build(
        cls,
        build_source: str | None,
        project_root: Path,
        tmp_path_factory,
        database_mode: str = "unknown",
        extras: str | None = None,
    ) -> "PyInstallerRunner":
        if build_source:
            binary_path = Path(build_source).resolve()
            if binary_path.is_dir():
                binary_path = binary_path / "canaille"
            return cls(binary_path)

        # Use shared binary built by prepare()
        binary_path = cls._get_shared_binary(project_root)
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
