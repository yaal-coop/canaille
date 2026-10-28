import base64
import hashlib
import io
import json
import os
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

ROOT = Path(__file__).parent
PACKAGE_LOCK = ROOT / "package-lock.json"
VENDOR_DIR = ROOT / "canaille" / "static" / "vendor"
VENDOR_STAMP = VENDOR_DIR / ".package-lock.sha256"
FOMANTIC_FONTS = [
    f"themes/default/assets/fonts/{name}.{extension}"
    for name in ("brand-icons", "icons", "outline-icons")
    for extension in ("woff", "woff2")
]
VENDOR_FILES = {
    "fomantic-ui-css": {
        path: f"fomantic-ui/{path}"
        for path in ["semantic.min.css", "semantic.min.js", *FOMANTIC_FONTS]
    },
    "jquery": {"dist/jquery.min.js": "jquery/jquery.min.js"},
    "htmx.org": {"dist/htmx.min.js": "htmx/htmx.min.js"},
    "idiomorph": {"dist/idiomorph-ext.min.js": "idiomorph/idiomorph-ext.min.js"},
    "wtforms-htmx-components": {
        "combobox.js": "wtforms-htmx-components/combobox.js",
    },
}


def create_mo_files():
    from babel.messages.frontend import compile_catalog

    cmd = compile_catalog()
    cmd.directory = os.path.join(os.path.dirname(__file__), "canaille", "translations")
    cmd.quiet = True
    cmd.statistics = True
    cmd.finalize_options()
    return cmd.run()


def download_npm_package(url, integrity):
    """Download a npm package tarball and check its integrity hash."""
    algorithm, expected = integrity.split()[0].split("-", 1)
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()

    digest = base64.b64encode(hashlib.new(algorithm, data).digest()).decode()
    if digest != expected:
        raise RuntimeError(f"{url} does not match the package-lock.json integrity.")

    return data


def vendor_static_files():
    """Extract the front-end files from the packages locked in package-lock.json."""
    lock = PACKAGE_LOCK.read_bytes()
    lock_hash = hashlib.sha256(lock).hexdigest()
    if VENDOR_STAMP.exists() and VENDOR_STAMP.read_text() == lock_hash:
        return

    packages = json.loads(lock)["packages"]
    shutil.rmtree(VENDOR_DIR, ignore_errors=True)
    for name, files in VENDOR_FILES.items():
        package = packages[f"node_modules/{name}"]
        tarball = download_npm_package(package["resolved"], package["integrity"])
        with tarfile.open(fileobj=io.BytesIO(tarball)) as archive:
            for source, target in files.items():
                destination = VENDOR_DIR / target
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.extractfile(f"package/{source}").read())

    VENDOR_STAMP.write_text(lock_hash)


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        create_mo_files()
        vendor_static_files()


if __name__ == "__main__":
    vendor_static_files()
    exit_code = create_mo_files()
    sys.exit(exit_code)
