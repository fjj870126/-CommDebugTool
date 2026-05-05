# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('resources', 'resources')],
    hiddenimports=['comm.tcp_client', 'comm.tcp_server', 'comm.udp_comm', 'comm.serial_comm', 'comm.websocket_comm', 'comm.mqtt_comm', 'packet.checksum', 'packet.packet_builder', 'protocols', 'ui', 'utils'],
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
    icon=['resources/app_icon.icns'],
)
app = BUNDLE(
    exe,
    name='CommDebugTool.app',
    icon='resources/app_icon.icns',
    bundle_identifier=None,
)
