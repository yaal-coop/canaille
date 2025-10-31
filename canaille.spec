# -*- mode: python ; coding: utf-8 -*-

import os
import re
from pathlib import Path
import importlib.resources
from canaille.app.i18n import available_language_codes
from canaille import create_app

with create_app().app_context():
    codes = {code.split("_")[0] for code in available_language_codes()}

with importlib.resources.path('wtforms', 'locale') as locale_path:
    wtforms_locale = str(locale_path)

def filter_wtforms_catalogs(item):
    dest, _, _ = item
    if not dest.startswith("wtforms/locale"):
        return True

    if Path(dest).suffix != ".mo":
        return False

    code = dest.split("/")[2].split("_")[0]
    return code in codes


def filter_babel_catalogs(item):
    dest, _, _ = item
    if not re.match(r"babel/locale-data/\w+\.dat", dest):
        return True

    code = Path(dest).stem.split("_")[0]
    return code in codes


def filter_pycountry_catalogs(item):
    dest, _, _ = item
    if not re.match(r"pycountry/locales/\w+/LC_MESSAGES/.+\.mo", dest):
        return True

    code = dest.split("/")[2].split("_")[0]
    return code in codes


def filter_map_files(item):
    dest, _, _ = item
    return not dest.endswith(".map")


def filter_faker_providers(item):
    dest, _, _ = item
    if not re.match(r"faker/providers/\w+/\w+", dest):
        return True

    code = dest.split("/")[3].split("_")[0]
    return code in codes

a = Analysis(
    ['canaille/commands.py'],
    pathex=[],
    binaries=[],
    datas = [
        ('canaille/backends/sql/migrations', 'canaille/backends/sql/migrations'),
        ('canaille/templates', 'canaille/templates'),
        ('canaille/static', 'canaille/static'),
        ('canaille/translations', 'canaille/translations'),
        (wtforms_locale, 'wtforms/locale'),
    ],
    hiddenimports=[
        "dramatiq_eager_broker",
        "canaille.hypercorn.app",
        "canaille.backends.memory.backend",
        "canaille.backends.memory.models",
        "canaille.backends.memory.models.core",
        "canaille.backends.memory.models.oidc",
        "canaille.backends.sql.backend",
        "canaille.backends.sql.models",
        "canaille.backends.sql.models.core",
        "canaille.backends.sql.models.oidc",
        "canaille.backends.ldap.backend",
        "canaille.backends.ldap.models",
        "canaille.backends.ldap.models.core",
        "canaille.backends.ldap.models.oidc",
        # TODO: import all passlib handlers?
        "passlib.hash",
        "passlib.handlers.pbkdf2",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

a.datas = list(filter(filter_wtforms_catalogs, a.datas))
a.datas = list(filter(filter_babel_catalogs, a.datas))
a.datas = list(filter(filter_pycountry_catalogs, a.datas))
a.datas = list(filter(filter_faker_providers, a.datas))
a.datas = list(filter(filter_map_files, a.datas))

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='canaille',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
