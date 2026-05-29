# -*- mode: python ; coding: utf-8 -*-
# Budowanie: pyinstaller AIQuizGenerator.spec
# Wynik:   dist/AIQuizGenerator.exe  (jeden plik)

from PyInstaller.utils.hooks import collect_all

block_cipher = None

hiddenimports = [
    "backend.main",
    "backend.db",
    "backend.ai_service",
    "backend.models",
    "paths",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "sqlalchemy.dialects.sqlite",
    "multipart",
    "email.mime.multipart",
]

datas = []
binaries = []

for pkg in ("PyQt6", "pdfplumber", "groq", "fastapi", "uvicorn", "pydantic", "httpx"):
    tmp = collect_all(pkg)
    datas += tmp[0]
    binaries += tmp[1]
    hiddenimports += tmp[2]

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AIQuizGenerator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
