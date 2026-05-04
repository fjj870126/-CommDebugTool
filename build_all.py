#!/usr/bin/env python3
"""
CommDebugTool - 全平台打包脚本
"""

import subprocess
import sys
import platform
import os
import shutil
import zipfile
import tarfile


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
    root_len = len(os.path.dirname(source_dir)) + 1
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            for f in files:
                file_path = os.path.join(root, f)
                arcname = file_path[root_len:]
                zf.write(file_path, arcname)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    plat, arch = get_platform_info()
    dist_dir = os.path.join('dist', plat)
    build_dir = os.path.join('build', plat)

    print('=' * 55)
    print('  CommDebugTool - 打包脚本')
    print('=' * 55)
    print(f'  系统:     {platform.system()} {arch}')
    print(f'  Python:   {sys.version.split()[0]}')
    print(f'  输出:     {dist_dir}/')
    print('=' * 55)

    run_cmd(
        [sys.executable, '-m', 'pip', 'install', 'pyinstaller', 'pyserial', '-q',
         '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple',
         '--trusted-host', 'pypi.tuna.tsinghua.edu.cn'],
        '安装依赖'
    )

    for d in [build_dir, dist_dir]:
        if os.path.exists(d):
            print(f'\n>> 清理 {d}/')
            shutil.rmtree(d)

    if platform.system() == 'Darwin':
        # macOS: 打包成 .app
        icon_path = 'resources/app_icon.icns'
        icon_arg = []
        if os.path.exists(icon_path):
            icon_arg = ['--icon', icon_path]
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
    else:
        run_cmd(
            [sys.executable, '-m', 'PyInstaller',
             'CommDebugTool.spec',
             '--noconfirm',
             '--distpath', dist_dir,
             '--workpath', build_dir],
            '打包可执行文件'
        )

    print()
    print(f'>> 压缩打包...')

    if platform.system() == 'Darwin':
        binary_path = os.path.join(dist_dir, 'CommDebugTool')
        if os.path.exists(binary_path):
            app_tmp = os.path.join('dist', '_app_tmp')
            if os.path.exists(app_tmp):
                shutil.rmtree(app_tmp)
            app_dir = os.path.join(app_tmp, 'CommDebugTool.app', 'Contents', 'MacOS')
            os.makedirs(app_dir)
            shutil.copy2(binary_path, os.path.join(app_dir, 'CommDebugTool'))
            os.chmod(os.path.join(app_dir, 'CommDebugTool'), 0o755)

            resources_dir = os.path.join(app_tmp, 'CommDebugTool.app', 'Contents', 'Resources')
            os.makedirs(resources_dir)
            icon_src = 'resources/app_icon.icns'
            if os.path.exists(icon_src):
                shutil.copy2(icon_src, os.path.join(resources_dir, 'app_icon.icns'))

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

            dmg_name = f'CommDebugTool-{plat}.dmg'
            dmg_path = os.path.join('dist', dmg_name)
            subprocess.run([
                'hdiutil', 'create', '-volname', 'CommDebugTool',
                '-srcfolder', app_tmp,
                '-ov', '-format', 'UDZO', dmg_path
            ], check=True)
            print(f'   生成: {dmg_path}')

            zip_name = f'CommDebugTool-{plat}.zip'
            zip_path = os.path.join('dist', zip_name)
            create_zip(zip_path, app_tmp)
            print(f'   生成: {zip_path}')

            shutil.rmtree(app_tmp)
            if os.path.exists(dist_dir):
                shutil.rmtree(dist_dir)
            print(f'   生成: {zip_path}')
            shutil.rmtree(dist_dir)
    elif platform.system() == 'Windows':
        exe_glob = os.path.join(dist_dir, 'CommDebugTool.exe')
        if os.path.exists(exe_glob):
            zip_name = f'CommDebugTool-{plat}.zip'
            zip_path = os.path.join('dist', zip_name)
            create_zip(zip_path, dist_dir)
            print(f'   生成: {zip_path}')
            shutil.rmtree(dist_dir)
    elif platform.system() == 'Linux':
        binary_path = os.path.join(dist_dir, 'CommDebugTool')
        if os.path.exists(binary_path):
            tar_name = f'CommDebugTool-{plat}.tar.gz'
            tar_path = os.path.join('dist', tar_name)
            with tarfile.open(tar_path, 'w:gz') as tf:
                tf.add(dist_dir, arcname='')
            print(f'   生成: {tar_path}')
            shutil.rmtree(dist_dir)

    print()
    print('=' * 55)
    print('  打包完成!')
    print('=' * 55)
    print(f'  压缩包在 dist/ 目录下')
    print()


if __name__ == '__main__':
    main()
