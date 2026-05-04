# -*- mode: python ; coding: utf-8 -*-
import sys
import platform
from pathlib import Path

import PyInstaller.building.api

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

pyz = PyInstaller.building.api.PYZ(a.pure)

exe = PyInstaller.building.api.EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
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
