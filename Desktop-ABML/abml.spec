# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ENV = os.path.join(SPECPATH, "env", "Lib", "site-packages")
MTCNN_WEIGHTS = os.path.join(ENV, "mtcnn", "assets", "weights")

datas = [
    # Assets propios (logos e íconos)
    (os.path.join(SPECPATH, "assets"), "assets"),

    # Pesos de MTCNN (.lz4)
    (os.path.join(MTCNN_WEIGHTS, "onet.lz4"), os.path.join("mtcnn", "assets", "weights")),
    (os.path.join(MTCNN_WEIGHTS, "pnet.lz4"), os.path.join("mtcnn", "assets", "weights")),
    (os.path.join(MTCNN_WEIGHTS, "rnet.lz4"), os.path.join("mtcnn", "assets", "weights")),

    # Datos de otras dependencias
    *collect_data_files("mtcnn"),
    *collect_data_files("deepface"),
    *collect_data_files("retinaface"),
    *collect_data_files("customtkinter"),
]

hiddenimports = [
    # mtcnn completo como paquete Python
    "mtcnn",
    "mtcnn.assets",
    "mtcnn.assets.weights",
    *collect_submodules("mtcnn"),

    # deepface y backends
    *collect_submodules("deepface"),
    *collect_submodules("retinaface"),

    # Win32 / captura de pantalla
    "win32gui", "win32ui", "win32con", "win32api", "pywintypes",
    "mss",
    "pygetwindow",

    # UI
    "customtkinter",
    "darkdetect",
    "PIL._tkinter_finder",
]

a = Analysis(
    ["main.py"],
    pathex=[SPECPATH],
    binaries=[],
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
    name="ABML",
    icon=os.path.join(SPECPATH, "assets", "icons", "Logo_1.ico"),
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
