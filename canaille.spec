# -*- mode: python ; coding: utf-8 -*-

import os
import re
from pathlib import Path
import importlib.resources
from canaille.app.i18n import available_language_codes
from canaille import create_app

with create_app({"SECRET_KEY": "foo"}).app_context():
    codes = available_language_codes()

with importlib.resources.path('wtforms', 'locale') as locale_path:
    wtforms_locale = str(locale_path)

def filter_wtforms_catalogs(item):
    dest, _, _ = item
    if not dest.startswith("wtforms/locale"):
        return True

    if Path(dest).suffix != ".mo":
        return False

    code = dest.split("/")[2][:2]
    return code in codes


def filter_babel_catalogs(item):
    dest, _, _ = item
    if not re.match(r"babel/locale-data/\w+\.dat", dest):
        return True

    code = Path(dest).stem[:2]
    return code in codes


def filter_pycountry_catalogs(item):
    dest, _, _ = item
    if not re.match(r"pycountry/locales/\w+/LC_MESSAGES/.+\.mo", dest):
        return True

    code = dest.split("/")[2][:2]
    return code in codes


def filter_map_files(item):
    dest, _, _ = item
    return not dest.endswith(".map")


def filter_faker_providers(item):
    dest, _, _ = item
    if not re.match(r"faker/providers/\w+/\w+", dest):
        return True

    code = dest.split("/")[3][:2]
    return code in codes

a = Analysis(
    ['canaille/commands.py'],
    pathex=[],
    binaries=[],
    datas = [
        ('canaille/backends/sql/migrations', 'canaille/backends/sql/migrations'),
        ('canaille/templates', 'canaille/templates'),
        ('canaille/static', 'canaille/static'),
        (wtforms_locale, 'wtforms/locale'),
    ],
    hiddenimports=[
        "canaille.app.server",
        "canaille.backends.memory.backend",
        "canaille.backends.sql.backend",
        "canaille.backends.ldap.backend",
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
