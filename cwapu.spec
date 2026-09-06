# -*- mode: python ; coding: utf-8 -*-
# CWapu, ricetta di compilazione.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' UltraCode).
# Il percorso di GBUtils si ricava dalla posizione di questo file, cosi' la
# compilazione riesce anche su una macchina dove i repository stanno altrove.
import os

GBUTILS_DIR = os.path.abspath(os.path.join(SPECPATH, '..', 'GBUtils'))

a = Analysis(
    ['cwapu.py'],
    pathex=[GBUTILS_DIR],
    binaries=[],
    datas=[('words.txt', '.'), ('MASTER.SCP', '.'), ('Manuale_CWapu.html', '.'), ('locales', 'locales')],
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