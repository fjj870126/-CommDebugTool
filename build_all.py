#!/usr/bin/env python3
"""
CommDebugTool - Unified Build Script
Run on any platform: python build_all.py

Since PyInstaller can only build for the current platform,
this script builds for the current OS and provides instructions
for building on other platforms.

For true one-click multi-platform builds, push to GitHub and
use the GitHub Actions workflow (.github/workflows/build.yml).
"""

import subprocess
import sys
import platform
import os
import shutil


def get_platform_info():
    """Detect current platform and architecture."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == 'darwin':
        plat = f'macos-{machine}'
    elif system == 'windows':
        arch_map = {'amd64': 'x64', 'x86_64': 'x64', 'x86': 'x86', 'arm64': 'arm64'}
        arch = arch_map.get(machine, machine)
        plat = f'windows-{arch}'
    elif system == 'linux':
        plat = f'linux-{machine}'
    else:
        plat = f'{system}-{machine}'

    return plat


def run_cmd(cmd, desc=None):
    """Run a command and print output."""
    if desc:
        print(f'\n>> {desc}')
    print(f'   $ {" ".join(cmd)}\n')
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f'\n[ERROR] Command failed with exit code {result.returncode}')
        sys.exit(1)


def main():
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    plat = get_platform_info()
    dist_dir = os.path.join('dist', plat)
    build_dir = os.path.join('build', plat)

    print('=' * 50)
    print('  CommDebugTool - Build Script')
    print('=' * 50)
    print(f'  Python:   {sys.version.split()[0]}')
    print(f'  Platform: {plat}')
    print(f'  Output:   {dist_dir}/')
    print('=' * 50)

    # Install dependencies
    # 使用国内镜像源加速下载
    run_cmd(
        [sys.executable, '-m', 'pip', 'install', 'pyinstaller', 'pyserial', '-q',
         '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple',
         '--trusted-host', 'pypi.tuna.tsinghua.edu.cn'],
        'Installing dependencies'
    )

    # Clean previous build for this platform
    for d in [build_dir, dist_dir]:
        if os.path.exists(d):
            print(f'\n>> Cleaning {d}/')
            shutil.rmtree(d)

    # Build
    run_cmd(
        [sys.executable, '-m', 'PyInstaller', 'CommDebugTool.spec',
         '--noconfirm', '--distpath', dist_dir, '--workpath', build_dir],
        'Building executable'
    )

    # Summary
    print()
    print('=' * 50)
    print('  Build complete!')
    print('=' * 50)
    print(f'  Output: {dist_dir}/')

    if platform.system() == 'Darwin':
        print(f'  Binary:  {dist_dir}/CommDebugTool')
        print(f'  App:     {dist_dir}/CommDebugTool.app')
    elif platform.system() == 'Windows':
        print(f'  Binary:  {dist_dir}\\CommDebugTool.exe')
    else:
        print(f'  Binary:  {dist_dir}/CommDebugTool')

    print()
    print('  To build for ALL platforms, push to GitHub and')
    print('  use Actions > Build Multi-Platform > Run workflow')
    print()


if __name__ == '__main__':
    main()
