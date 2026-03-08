# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for VOK (Windows). Run from project root: pyinstaller vok.spec --clean --noconfirm

from pathlib import Path

block_cipher = None

# When frozen, app uses sys._MEIPASS; resources must be at _MEIPASS/resources
project_root = Path('.')
resources = (str(project_root / 'resources'), 'resources')
icon_path = project_root / 'resources' / 'icon.ico'

a = Analysis(
    ['run.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[resources],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'qfluentwidgets',
        'yt_dlp',
        'requests',
        'bs4',
        'lxml',
        'playwright',
        'aiohttp',
        'dotenv',
        'PIL',
        'PIL.Image',
        'apscheduler',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='VOK Get',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path) if icon_path.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VOK Get',
)
