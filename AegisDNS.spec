# PyInstaller spec for the native AegisDNS GUI (Linux build).
#
# Only the GUI is packaged here — backend services (DB, scanner, VirusTotal,
# LLM) run separately via `docker compose up -d` per README.md. This bundle
# just needs PySide6 + the Scapy sniffer + the HTTP client talking to the
# Dockerized backend on 127.0.0.1:5005.
#
# Build with:  pyinstaller AegisDNS.spec
# Output:      dist/AegisDNS/AegisDNS

# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ["src/main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("src/gui/Style_Sheet", "src/gui/Style_Sheet"),
        ("src/images", "src/images"),
        # Needed by src/logic/backend_launcher.py to auto-start the backend
        # via `docker compose up -d` on a machine that only has the GUI
        # installed (not a git checkout of the repo).
        ("docker-compose.yml", "."),
        ("backend", "backend"),
        ("scanner", "scanner"),
        (".env.example", "."),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AegisDNS",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="AegisDNS",
)
