# PyInstaller spec file for OSINT Framework Desktop
# Usage: pyinstaller osint_desktop.spec

import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

a = Analysis(
    ['osint_desktop.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/ui', 'src/ui'),
        ('src/core', 'src/core'),
    ],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtChart',
        'matplotlib',
        'networkx',
        'numpy',
        'pandas',
    ] + collect_submodules('src'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OSINTFramework',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Set to icon.ico path if available
)

# For macOS app bundle
# coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas,
#                strip=False, upx=True, upx_exclude=[], name='OSINTFramework')
