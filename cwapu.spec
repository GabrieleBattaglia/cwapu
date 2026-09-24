# -*- mode: python ; coding: utf-8 -*-
# CWapu, ricetta di compilazione.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' UltraCode).
# Il percorso di GBUtils si ricava dalla posizione di questo file, cosi' la
# compilazione riesce anche su una macchina dove i repository stanno altrove.
# Dalla 8.0.0, issue 21, il pacchetto e' una cartella e non piu' un file
# unico: in dist\cwapu c'e' cwapu.exe con accanto _internal, dove stanno le
# librerie e le risorse, ciascuna sotto resources come nel sorgente, e il
# manuale sotto docs. Cosi' l'eseguibile non si scompatta piu' in una
# cartella temporanea a ogni avvio, e percorso_risorsa trova
# resources\words.txt dentro _internal come lo trova accanto a cwapu.py.
import os
from pathlib import Path

GBUTILS_DIR = os.path.abspath(os.path.join(SPECPATH, '..', 'GBUtils'))

# Delle traduzioni al programma servono soltanto i cataloghi compilati: i .po
# e il modello .pot sono il testo su cui si lavora e nel pacchetto pubblico
# non c'entrano, come dice il punto 4.6 del prontuario di rilascio. L'elenco
# si ricava da SPECPATH, cosi' non dipende dalla cartella da cui si lancia
# PyInstaller, e ogni catalogo resta nella sua cartella, per esempio
# resources\locales\en\LC_MESSAGES.
CATALOGHI = [
    (str(percorso), str(percorso.parent.relative_to(Path(SPECPATH))))
    for percorso in Path(SPECPATH, 'resources', 'locales').rglob('*.mo')
]
RISORSE = [
    (os.path.join('resources', nome), 'resources')
    for nome in ('words.txt', 'MASTER.SCP')
]
# Il manuale sta in docs dalla 8.0.1, e in _internal\docs nel pacchetto.
RISORSE.append((os.path.join('docs', 'Manuale_CWapu.html'), 'docs'))

a = Analysis(
    ['cwapu.py'],
    pathex=[GBUTILS_DIR],
    binaries=[],
    datas=RISORSE + CATALOGHI,
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
    [],
    exclude_binaries=True,
    name='cwapu',
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='cwapu',
)
