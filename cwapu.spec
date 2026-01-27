# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['cwapu.py'],
    pathex=['E:\\git\\Mine\\GBUtils'],
    binaries=[],
    datas=[('words.txt', '.'), ('MASTER.SCP', '.'), ('locales', 'locales')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['wx', 'PyQt5', 'PySide2', 'PySide6', 'IPython', 'notebook', 'nbconvert', 'qtpy'],
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
    name='cwapu',
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