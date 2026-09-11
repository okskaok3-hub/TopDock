# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

PYTHON_HOME = Path(sys.executable).resolve().parent
TCL_ROOT = PYTHON_HOME / "tcl"
DLL_ROOT = PYTHON_HOME / "DLLs"

binaries = [
    (str(DLL_ROOT / "_tkinter.pyd"), "."),
    (str(DLL_ROOT / "tcl86t.dll"), "."),
    (str(DLL_ROOT / "tk86t.dll"), "."),
]


def collect_dir_data(source_dir, dest_prefix):
    entries = []
    source_dir = Path(source_dir)
    for file_path in source_dir.rglob("*"):
        if file_path.is_file():
            relative_dir = file_path.parent.relative_to(source_dir)
            dest_dir = Path(dest_prefix) / relative_dir
            entries.append((str(file_path), str(dest_dir)))
    return entries


datas = []
datas += collect_dir_data(PYTHON_HOME / "Lib" / "tkinter", "tkinter")
datas += collect_dir_data(TCL_ROOT / "tcl8.6", "tcl/tcl8.6")
datas += collect_dir_data(TCL_ROOT / "tk8.6", "tcl/tk8.6")

hiddenimports = [
    "pystray._win32",
    "win32api",
    "win32con",
    "win32gui",
    "PIL._tkinter_finder",
    "pynput.keyboard._win32",
    "pynput.mouse._win32",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["pyi_rth_tkinter.py"],
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
    name="VDIToolkit",
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
