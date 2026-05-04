#!/usr/bin/env python3
"""
CommDebugTool - 全平台打包脚本

在 macOS 上打包: python build_all.py
打包后会在 dist/ 目录生成可执行文件。

跨平台打包方法:
  方法1（推荐）: 推送到 GitHub，用 Actions 自动打包
  方法2: 在对应平台分别运行 python build_all.py

各平台架构:
  macOS:   arm64 (Apple Silicon), x86_64 (Intel)
  Windows: x64, x86 (32位), arm64
  Linux:   x86_64, aarch64, i686
"""

import subprocess
import sys
import platform
import os
import shutil
import zipfile
import tarfile


def get_platform_info():
    """检测当前平台和架构"""
    system = platform.system().lower()
    machine = platform.machine().lower()

    arch_map = {
        'x86_64': 'x86_64', 'amd64': 'x86_64',
        'x86': 'x86', 'i386': 'x86', 'i686': 'x86',
        'arm64': 'arm64', 'aarch64': 'arm64',
    }
    arch = arch_map.get(machine, machine)

    if system == 'darwin':
        plat = f'macos-{arch}'
    elif system == 'windows':
        plat = f'windows-{arch}'
    elif system == 'linux':
        plat = f'linux-{arch}'
    else:
        plat = f'{system}-{arch}'

    return plat, arch


def run_cmd(cmd, desc=None):
    if desc:
        print(f'\n>> {desc}')
    print(f'   $ {" ".join(cmd)}\n')
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f'\n[ERROR] 命令执行失败，退出码 {result.returncode}')
        sys.exit(1)


def create_zip(output_path, source_dir):
    """打包成 zip"""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            for f in files:
                file_path = os.path.join(root, f)
                arcname = os.path.relpath(file_path, source_dir)
                zf.write(file_path, arcname)


def create_tar_gz(output_path, source_dir):
    """打包成 tar.gz"""
    with tarfile.open(output_path, 'w:gz') as tf:
        tf.add(source_dir, arcname='')


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
    print(f'  打包格式: ', end='')
    if platform.system() == 'Windows':
        print(f'CommDebugTool-{plat}.zip')
    elif platform.system() == 'Darwin':
        print(f'CommDebugTool-{plat}.zip')
    else:
        print(f'CommDebugTool-{plat}.tar.gz')
    print('=' * 55)

    # 安装依赖
    run_cmd(
        [sys.executable, '-m', 'pip', 'install', 'pyinstaller', 'pyserial', '-q',
         '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple',
         '--trusted-host', 'pypi.tuna.tsinghua.edu.cn'],
        '安装依赖'
    )

    # 清理上一次的构建
    for d in [build_dir, dist_dir]:
        if os.path.exists(d):
            print(f'\n>> 清理 {d}/')
            shutil.rmtree(d)

    # 打包
    run_cmd(
        [sys.executable, '-m', 'PyInstaller', 'CommDebugTool.spec',
         '--noconfirm', '--distpath', dist_dir, '--workpath', build_dir],
        '打包可执行文件'
    )

    # 打包成压缩包
    print()
    print(f'>> 压缩打包...')
    plat_dist = os.path.join('dist', plat)

    if platform.system() == 'Darwin':
        # macOS: 打包 .app
        app_path = os.path.join(plat_dist, 'CommDebugTool.app')
        if os.path.exists(app_path):
            zip_name = f'CommDebugTool-{plat}.zip'
            zip_path = os.path.join('dist', zip_name)
            create_zip(zip_path, app_path)
            print(f'   生成: {zip_path}')
            # 清理未压缩的文件夹
            shutil.rmtree(plat_dist)
    elif platform.system() == 'Windows':
        exe_path = os.path.join(plat_dist, 'CommDebugTool.exe')
        if os.path.exists(exe_path):
            zip_name = f'CommDebugTool-{plat}.zip'
            zip_path = os.path.join('dist', zip_name)
            create_zip(zip_path, plat_dist)
            print(f'   生成: {zip_path}')
            shutil.rmtree(plat_dist)
    elif platform.system() == 'Linux':
        binary_path = os.path.join(plat_dist, 'CommDebugTool')
        if os.path.exists(binary_path):
            tar_name = f'CommDebugTool-{plat}.tar.gz'
            tar_path = os.path.join('dist', tar_name)
            create_tar_gz(tar_path, plat_dist)
            print(f'   生成: {tar_path}')
            shutil.rmtree(plat_dist)

    # 完成
    print()
    print('=' * 55)
    print('  打包完成!')
    print('=' * 55)
    print(f'  压缩包在 dist/ 目录下')
    print()
    print('  跨平台打包方法:')
    print('  1. 推送到 GitHub，在 Actions 页面手动触发 Build Multi-Platform')
    print('  2. 在对应平台分别运行 python build_all.py')
    print()
    print(f'  当前平台 {plat} 打包完成 ✅')
    print()


if __name__ == '__main__':
    main()
