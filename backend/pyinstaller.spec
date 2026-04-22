# -*- mode: python ; coding: utf-8 -*-
# 在 backend/ 目录执行: pyinstaller pyinstaller.spec
# 或运行项目根目录 scripts/build_pyinstaller.ps1

import os

block_cipher = None
_spec_dir = os.path.dirname(os.path.abspath(SPEC))

_hidden = [
    "pymysql",
    "cryptography",
    "cryptography.hazmat.backends.openssl.backend",
    "bcrypt",
    "jwt",
    "waitress",
    "flask_cors",
    "sqlalchemy.dialects.mysql",
    "sqlalchemy.dialects.mysql.pymysql",
    "sqlalchemy.sql.default_comparator",
    "sqlalchemy.ext.baked",
    "werkzeug.middleware.proxy_fix",
]

a = Analysis(
    [os.path.join(_spec_dir, "run_server.py")],
    pathex=[_spec_dir],
    binaries=[],
    datas=[
        (
            os.path.join(_spec_dir, "app", "static", "admin"),
            os.path.join("app", "static", "admin"),
        ),
        (
            os.path.join(_spec_dir, "app", "static", "mobile"),
            os.path.join("app", "static", "mobile"),
        ),
    ],
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "IPython",
        "jupyter",
        "jupyter_client",
        "jupyter_core",
        "notebook",
        "nbformat",
        "nbconvert",
        "sphinx",
        "docutils",
        "jedi",
        "parso",
        "pygame",
        "PyQt5",
        "PySide6",
        "sklearn",
        "scipy",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="business-mgm-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="business-mgm-server",
)
