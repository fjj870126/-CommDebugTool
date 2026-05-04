#!/usr/bin/env python3
"""
CommDebugTool - 全平台打包脚本

在当前平台运行即可打包当前平台的可执行文件。
如需打包其他平台，请在对应平台上运行此脚本。
"""

import subprocess
import sys
import platform
import os
import shutil
import zipfile
import tarfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.version import APP_VERSION


def get_platform_info():
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch_map = {
        'x86_64': 'x86_64', 'amd64': 'x86_64',
        'x86': 'x86', 'i386': 'x86', 'i686': 'x86',
        'arm64': 'arm64', 'aarch64': 'arm64',
    }
    arch = arch_map.get(machine, machine)
    if system == 'darwin':
        return f'macos-{arch}', arch
    elif system == 'windows':
        return f'windows-{arch}', arch
    elif system == 'linux':
        return f'linux-{arch}', arch
    return f'{system}-{arch}', arch


def run_cmd(cmd, desc=None):
    if desc:
        print(f'\n>> {desc}')
    print(f'   $ {" ".join(cmd)}\n')
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f'\n[ERROR] 命令执行失败，退出码 {result.returncode}')
        sys.exit(1)


def create_zip(output_path, source_dir):
    base_name = os.path.basename(os.path.normpath(source_dir))
    parent = os.path.dirname(os.path.normpath(source_dir))
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            for f in files:
                file_path = os.path.join(root, f)
                arcname = os.path.relpath(file_path, parent)
                zf.write(file_path, arcname)


def build_macos(dist_dir, build_dir, plat):
    icon_path = 'resources/app_icon.icns'
    icon_arg = ['--icon', icon_path] if os.path.exists(icon_path) else []

    run_cmd(
        [sys.executable, '-m', 'PyInstaller',
         '--onefile', '--windowed',
         '--name', 'CommDebugTool',
         '--distpath', dist_dir,
         '--workpath', build_dir,
         '--add-data', f'resources{os.pathsep}resources',
         '--hidden-import', 'comm.tcp_client',
         '--hidden-import', 'comm.tcp_server',
         '--hidden-import', 'comm.udp_comm',
         '--hidden-import', 'comm.serial_comm',
         '--hidden-import', 'comm.websocket_comm',
         '--hidden-import', 'comm.mqtt_comm',
         '--hidden-import', 'packet.checksum',
         '--hidden-import', 'packet.packet_builder',
         '--hidden-import', 'protocols',
         '--hidden-import', 'ui',
         '--hidden-import', 'utils',
         ] + icon_arg + ['main.py'],
        '打包可执行文件'
    )

    print(f'\n>> 压缩打包...')
    binary_path = os.path.join(dist_dir, 'CommDebugTool')
    if not os.path.exists(binary_path):
        return

    app_tmp = os.path.join('dist', '_app_tmp')
    if os.path.exists(app_tmp):
        shutil.rmtree(app_tmp)

    # 创建 .app 结构
    app_dir = os.path.join(app_tmp, 'CommDebugTool.app', 'Contents', 'MacOS')
    os.makedirs(app_dir)
    shutil.copy2(binary_path, os.path.join(app_dir, 'CommDebugTool'))
    os.chmod(os.path.join(app_dir, 'CommDebugTool'), 0o755)

    resources_dir = os.path.join(app_tmp, 'CommDebugTool.app', 'Contents', 'Resources')
    os.makedirs(resources_dir)
    if os.path.exists(icon_path):
        shutil.copy2(icon_path, os.path.join(resources_dir, 'app_icon.icns'))

    plist = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>CommDebugTool</string>
<key>CFBundleIdentifier</key><string>com.commdebugtool.app</string>
<key>CFBundleName</key><string>CommDebugTool</string>
<key>CFBundleIconFile</key><string>app_icon.icns</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>LSUIElement</key><true/>
</dict></plist>'''
    info_dir = os.path.join(app_tmp, 'CommDebugTool.app', 'Contents')
    with open(os.path.join(info_dir, 'Info.plist'), 'w') as f:
        f.write(plist)

    # 创建 /Applications 快捷方式
    subprocess.run(['ln', '-s', '/Applications', os.path.join(app_tmp, 'Applications')],
                   capture_output=True)

    ver_dir = os.path.join('dist', f'v{APP_VERSION}')
    plat_dir_name = f'{plat}'
    plat_dir_full = os.path.join(ver_dir, plat_dir_name)
    os.makedirs(plat_dir_full, exist_ok=True)

    # 生成 DMG
    dmg_name = f'CommDebugTool-{APP_VERSION}-{plat}.dmg'
    dmg_path = os.path.join(plat_dir_full, dmg_name)
    subprocess.run([
        'hdiutil', 'create', '-volname', 'CommDebugTool',
        '-srcfolder', app_tmp,
        '-ov', '-format', 'UDZO', dmg_path
    ], check=True)
    print(f'   生成: {dmg_path}')

    # 生成 ZIP（OTA 更新用，只打包 .app）
    zip_name = f'CommDebugTool-{APP_VERSION}-{plat}.zip'
    zip_path = os.path.join(plat_dir_full, zip_name)
    app_contents = os.path.join(app_tmp, 'CommDebugTool.app')
    create_zip(zip_path, app_contents)
    print(f'   生成: {zip_path}')

    shutil.rmtree(app_tmp)
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)

    # 删除旧的平铺文件（兼容旧版输出）
    for old in ['CommDebugTool-1.0.0-macos-arm64.zip', 'CommDebugTool-1.0.0-macos-arm64.dmg',
                'CommDebugTool-1.0.1-macos-arm64.zip', 'CommDebugTool-1.0.1-macos-arm64.dmg']:
        old_path = os.path.join(ver_dir, old)
        if os.path.exists(old_path):
            os.remove(old_path)


def build_windows(dist_dir, build_dir, plat):
    run_cmd(
        [sys.executable, '-m', 'PyInstaller',
         '--onefile', '--windowed',
         '--name', 'CommDebugTool',
         '--distpath', dist_dir,
         '--workpath', build_dir,
         '--add-data', f'resources{os.pathsep}resources',
         '--hidden-import', 'comm.tcp_client',
         '--hidden-import', 'comm.tcp_server',
         '--hidden-import', 'comm.udp_comm',
         '--hidden-import', 'comm.serial_comm',
         '--hidden-import', 'comm.websocket_comm',
         '--hidden-import', 'comm.mqtt_comm',
         '--hidden-import', 'packet.checksum',
         '--hidden-import', 'packet.packet_builder',
         '--hidden-import', 'protocols',
         '--hidden-import', 'ui',
         '--hidden-import', 'utils',
         ] + ['main.py'],
        '打包可执行文件'
    )

    print(f'\n>> 压缩打包...')
    exe_path = os.path.join(dist_dir, 'CommDebugTool.exe')
    if not os.path.exists(exe_path):
        return

    ver_dir = os.path.join('dist', f'v{APP_VERSION}')
    plat_dir_name = f'{plat}'
    plat_dir_full = os.path.join(ver_dir, plat_dir_name)
    os.makedirs(plat_dir_full, exist_ok=True)

    zip_name = f'CommDebugTool-{APP_VERSION}-{plat}.zip'
    zip_path = os.path.join(plat_dir_full, zip_name)
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe_path, 'CommDebugTool.exe')
    print(f'   生成: {zip_path}')

    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)


def build_linux(dist_dir, build_dir, plat):
    run_cmd(
        [sys.executable, '-m', 'PyInstaller',
         '--onefile', '--windowed',
         '--name', 'CommDebugTool',
         '--distpath', dist_dir,
         '--workpath', build_dir,
         '--add-data', f'resources{os.pathsep}resources',
         '--hidden-import', 'comm.tcp_client',
         '--hidden-import', 'comm.tcp_server',
         '--hidden-import', 'comm.udp_comm',
         '--hidden-import', 'comm.serial_comm',
         '--hidden-import', 'comm.websocket_comm',
         '--hidden-import', 'comm.mqtt_comm',
         '--hidden-import', 'packet.checksum',
         '--hidden-import', 'packet.packet_builder',
         '--hidden-import', 'protocols',
         '--hidden-import', 'ui',
         '--hidden-import', 'utils',
         ] + ['main.py'],
        '打包可执行文件'
    )

    print(f'\n>> 压缩打包...')
    binary_path = os.path.join(dist_dir, 'CommDebugTool')
    if not os.path.exists(binary_path):
        return

    ver_dir = os.path.join('dist', f'v{APP_VERSION}')
    plat_dir_name = f'{plat}'
    plat_dir_full = os.path.join(ver_dir, plat_dir_name)
    os.makedirs(plat_dir_full, exist_ok=True)

    tar_name = f'CommDebugTool-{APP_VERSION}-{plat}.tar.gz'
    tar_path = os.path.join(plat_dir_full, tar_name)
    if os.path.exists(tar_path):
        os.remove(tar_path)
    with tarfile.open(tar_path, 'w:gz') as tf:
        tf.add(dist_dir, arcname='CommDebugTool')
    print(f'   生成: {tar_path}')

    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    plat, arch = get_platform_info()
    dist_dir = os.path.join('dist', plat)
    build_dir = os.path.join('build', plat)

    print('=' * 55)
    print(f'  CommDebugTool v{APP_VERSION} - 打包脚本')
    print('=' * 55)
    print(f'  系统:     {platform.system()} {arch}')
    print(f'  Python:   {sys.version.split()[0]}')
    print(f'  输出:     dist/v{APP_VERSION}/')
    print('=' * 55)

    # 安装依赖
    run_cmd(
        [sys.executable, '-m', 'pip', 'install', 'pyinstaller', 'pyserial', '-q',
         '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple',
         '--trusted-host', 'pypi.tuna.tsinghua.edu.cn'],
        '安装依赖'
    )

    # 清理旧构建
    for d in [build_dir, dist_dir]:
        if os.path.exists(d):
            print(f'\n>> 清理 {d}/')
            shutil.rmtree(d)

    # 根据平台选择打包方式
    system = platform.system()
    if system == 'Darwin':
        build_macos(dist_dir, build_dir, plat)
    elif system == 'Windows':
        build_windows(dist_dir, build_dir, plat)
    elif system == 'Linux':
        build_linux(dist_dir, build_dir, plat)
    else:
        print(f'不支持的平台: {system}')
        sys.exit(1)

    print()
    print('=' * 55)
    print('  打包完成!')
    print('=' * 55)
    print(f'  输出目录: dist/v{APP_VERSION}/')
    print()
    print('  如需打包其他平台:')
    print('  1. 在对应平台运行 python build_all.py')
    print('  2. 或推送到 GitHub 用 Actions 自动打包')
    print()


if __name__ == '__main__':
    main()
