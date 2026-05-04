# -*- mode: python ; coding: utf-8 -*-
import sys
import platform
from pathlib import Path

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
    ],
    hiddenimports=[
        'comm.tcp_client',
        'comm.tcp_server',
        'comm.udp_comm',
        'comm.serial_comm',
        'comm.websocket_comm',
        'comm.mqtt_comm',
        'packet.checksum',
        'packet.packet_builder',
        'protocols',
        'ui',
        'utils',
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

# macOS needs .app bundle for GUI app
if platform.system() == 'Darwin':
    exe = EXE(
        a,
        PyInstaller.building.api.PYZ(a.pure),
        name='CommDebugTool',
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
    app = BUNDLE(
        exe,
        name='CommDebugTool.app',
        icon='resources/app_icon.icns' if Path('resources/app_icon.icns').exists() else None,
        bundle_identifier='com.commdebugtool.app',
        info_plist={
            'NSHighResolutionCapable': True,
            'CFBundleDisplayName': 'CommDebugTool',
        },
    )
else:
    exe = EXE(
        a,
        PyInstaller.building.api.PYZ(a.pure),
        name='CommDebugTool',
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
