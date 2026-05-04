"""软件自动更新模块 - 支持 GitHub / Gitee 多源检测"""

import json
import os
import platform
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.request import urlopen, Request
from urllib.error import URLError

from utils.version import APP_VERSION


# ===== 配置 =====
UPDATE_SOURCES = [
    {
        'name': 'GitHub',
        'api_url': 'https://api.github.com/repos/{owner}/{repo}/releases/latest',
        'download_url': 'https://github.com/{owner}/{repo}/releases/download/{tag}/{filename}',
    },
    {
        'name': 'Gitee',
        'api_url': 'https://gitee.com/api/v5/repos/{owner}/{repo}/releases/latest',
        'download_url': 'https://gitee.com/{owner}/{repo}/releases/download/{tag}/{filename}',
    },
]

OWNER = 'fjj20800959'
REPO = 'comm-debug-tool'


def _parse_version(tag: str) -> tuple:
    nums = re.findall(r'\d+', tag)
    return tuple(int(n) for n in nums[:3]) if nums else (0, 0, 0)


def check_update(timeout: int = 5) -> dict:
    for source in UPDATE_SOURCES:
        try:
            url = source['api_url'].format(owner=OWNER, repo=REPO)
            req = Request(url, headers={'User-Agent': 'CommDebugTool', 'Accept': 'application/json'})
            with urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            tag = data.get('tag_name', '')
            remote_ver = _parse_version(tag)
            local_ver = _parse_version(APP_VERSION)
            assets = []
            for asset in data.get('assets', []):
                assets.append({
                    'name': asset.get('name', ''),
                    'url': asset.get('browser_download_url', ''),
                    'size': asset.get('size', 0),
                })
            return {
                'has_update': remote_ver > local_ver,
                'version': tag.lstrip('v'),
                'body': data.get('body', ''),
                'source': source['name'],
                'assets': assets,
            }
        except URLError as e:
            if hasattr(e, 'code') and e.code == 403:
                continue
        except Exception:
            continue
    # API 失败时，尝试从 Release 页面抓取版本信息
    try:
        html_url = f'https://gitee.com/{OWNER}/{REPO}/releases'
        req = Request(html_url, headers={'User-Agent': 'CommDebugTool'})
        with urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode('utf-8')
        tags = re.findall(r'v\d+\.\d+\.\d+', html)
        if tags:
            latest_tag = tags[0]
            remote_ver = _parse_version(latest_tag)
            local_ver = _parse_version(APP_VERSION)
            # 尝试从 API 获取更新内容和附件
            try:
                api_url = f'https://gitee.com/api/v5/repos/{OWNER}/{REPO}/releases/tags/{latest_tag}'
                api_req = Request(api_url, headers={'User-Agent': 'CommDebugTool', 'Accept': 'application/json'})
                with urlopen(api_req, timeout=5) as api_resp:
                    api_data = json.loads(api_resp.read().decode('utf-8'))
                body = api_data.get('body', '')
                assets = []
                for asset in api_data.get('assets', []):
                    assets.append({
                        'name': asset.get('name', ''),
                        'url': asset.get('browser_download_url', ''),
                        'size': asset.get('size', 0),
                    })
            except Exception:
                body = ''
                assets = []
                dl_items = re.findall(r'/releases/download/v[\d.]+/[^"<>]+', html)
                seen = set()
                for path in dl_items:
                    name = path.rsplit('/', 1)[-1] if '/' in path else path
                    if name not in seen and not name.endswith('.zip') is False:
                        seen.add(name)
                        assets.append({'name': name, 'url': f'https://gitee.com/{OWNER}/{REPO}{path}', 'size': 0})
                assets = [a for a in assets if not (a['name'].startswith('v') and (a['name'].endswith('.zip') or a['name'].endswith('.tar.gz')))]
            return {
                'has_update': remote_ver > local_ver,
                'version': latest_tag.lstrip('v'),
                'body': body,
                'source': 'Gitee',
                'assets': assets,
            }
    except Exception:
        pass
    return None


def _select_asset(assets: list) -> dict:
    sys_plat = platform.system()
    sys_machine = platform.machine().lower()

    arch_map = {
        'x86_64': ['x86_64', 'amd64'],
        'amd64': ['x86_64', 'amd64'],
        'arm64': ['arm64', 'aarch64'],
        'aarch64': ['arm64', 'aarch64'],
        'x86': ['x86', 'i386', 'i686'],
        'i386': ['x86', 'i386', 'i686'],
        'i686': ['x86', 'i386', 'i686'],
    }
    arch_names = arch_map.get(sys_machine, [sys_machine])

    plat_map = {'Darwin': 'macos', 'Windows': 'windows', 'Linux': 'linux'}
    plat_name = plat_map.get(sys_plat, '')

    def name_matches(name: str) -> bool:
        name_lower = name.lower()
        if not plat_name or plat_name not in name_lower:
            return False
        return any(a in name_lower for a in arch_names)

    # 优先匹配本平台+本架构的 zip
    for asset in assets:
        name = asset['name'].lower()
        if name.endswith('.zip') and name_matches(name):
            return asset

    # 其次匹配本平台+本架构的安装包
    for asset in assets:
        name = asset['name'].lower()
        if not name_matches(name):
            continue
        if sys_plat == 'Darwin' and name.endswith('.dmg'):
            return asset
        if sys_plat == 'Windows' and name.endswith('.exe'):
            return asset
        if sys_plat == 'Linux' and (name.endswith('.tar.gz') or name.endswith('.AppImage')):
            return asset

    # 任意本平台的 zip
    for asset in assets:
        name = asset['name'].lower()
        if name.endswith('.zip') and plat_name and plat_name in name:
            return asset

    # 任意 zip
    for asset in assets:
        name = asset['name'].lower()
        if name.endswith('.zip'):
            return asset

    return assets[0] if assets else None


def download_update(asset: dict, progress_callback=None) -> str:
    import tempfile
    url = asset['url']
    name = asset['name']
    local_path = os.path.join(tempfile.gettempdir(), name)
    req = Request(url, headers={'User-Agent': 'CommDebugTool'})
    with urlopen(req, timeout=30) as resp:
        total = int(resp.headers.get('Content-Length', 0))
        downloaded = 0
        chunk_size = 8192
        with open(local_path, 'wb') as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total > 0:
                    progress_callback(downloaded / total)
    return local_path


def install_update(local_path: str):
    import zipfile
    import shutil

    sys_plat = platform.system()
    try:
        if local_path.endswith('.zip'):
            extract_parent = os.path.expanduser('~/.commdebugtool_update')
            extract_dir = os.path.join(extract_parent, 'app')
            if os.path.exists(extract_dir):
                if os.path.isfile(extract_dir):
                    os.remove(extract_dir)
                else:
                    shutil.rmtree(extract_dir)
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(local_path, 'r') as zf:
                zf.extractall(extract_dir)

            if sys_plat == 'Darwin':
                app_path = os.path.join(extract_dir, 'CommDebugTool.app')
                if os.path.exists(app_path):
                    target_app = '/Applications/CommDebugTool.app'
                    # 先复制到临时位置，成功后再替换
                    temp_target = target_app + '.new'
                    if os.path.exists(temp_target):
                        if os.path.isfile(temp_target):
                            os.remove(temp_target)
                        else:
                            shutil.rmtree(temp_target)
                    shutil.copytree(app_path, temp_target)
                    # 修复执行权限
                    binary = os.path.join(temp_target, 'Contents', 'MacOS', 'CommDebugTool')
                    if os.path.exists(binary):
                        os.chmod(binary, 0o755)
                    # 签名
                    subprocess.run(['xattr', '-dr', 'com.apple.quarantine', temp_target],
                                   capture_output=True)
                    subprocess.run(['codesign', '--force', '--deep', '--sign', '-', temp_target],
                                   capture_output=True)
                    # 替换旧文件
                    if os.path.exists(target_app):
                        shutil.rmtree(target_app)
                    shutil.move(temp_target, target_app)
                    binary = os.path.join(target_app, 'Contents', 'MacOS', 'CommDebugTool')
                    subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     start_new_session=True, close_fds=True)
                    import time
                    time.sleep(2)
                    os.system(f'(sleep 3 && rm -rf "{extract_parent}") &')
                    os._exit(0)
                else:
                    new_binary = os.path.join(extract_dir, 'CommDebugTool')
                    if os.path.exists(new_binary):
                        os.chmod(new_binary, 0o755)
                        subprocess.run(['xattr', '-d', 'com.apple.quarantine', new_binary],
                                       capture_output=True)
                        subprocess.run(['codesign', '--force', '--deep', '--sign', '-', new_binary],
                                       capture_output=True)
                        subprocess.Popen([new_binary])
                    else:
                        subprocess.Popen(['open', extract_dir])
                subprocess.Popen(['bash', '-c',
                    f'sleep 5 && rm -rf {extract_parent}'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                sys.exit(0)
            elif sys_plat == 'Windows':
                new_binary = os.path.join(extract_dir, 'CommDebugTool.exe')
                if os.path.exists(new_binary):
                    os.chmod(new_binary, 0o755)
                    subprocess.Popen([new_binary])
                    sys.exit(0)
                # Windows 上如果找不到 .exe，说明下载的是其他平台的包
                messagebox.showwarning('系统不匹配',
                    '下载的安装包不适用于 Windows 系统，\n'
                    '请前往 Gitee 发布页面下载 Windows 版本:\n'
                    f'https://gitee.com/{OWNER}/{REPO}/releases')
                sys.exit(0)
            else:
                new_binary = os.path.join(extract_dir, 'CommDebugTool')
                if os.path.exists(new_binary):
                    os.chmod(new_binary, 0o755)
                    subprocess.Popen([new_binary])
                else:
                    subprocess.Popen(['open', extract_dir])
                sys.exit(0)
        elif sys_plat == 'Darwin' and local_path.endswith('.dmg'):
            subprocess.Popen(['open', local_path])
        elif sys_plat == 'Windows':
            subprocess.Popen([local_path], shell=True)
        elif sys_plat == 'Linux' and local_path.endswith('.AppImage'):
            os.chmod(local_path, 0o755)
            subprocess.Popen([local_path])
    except Exception as e:
        messagebox.showerror('安装失败', f'请手动解压安装:\n{local_path}\n\n错误: {e}')
    sys.exit(0)


# ===== UI 对话框 =====

def show_update_dialog(parent, info: dict, config_update: dict = None):
    dialog = tk.Toplevel(parent)
    dialog.title('发现新版本')
    dialog.transient(parent)
    dialog.grab_set()
    dialog.withdraw()
    dialog.update_idletasks()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    w, h = 500, 480
    dialog.geometry(f'{w}x{h}+{px + (pw - w) // 2}+{py + (ph - h) // 2}')
    dialog.deiconify()

    main_frame = ttk.Frame(dialog, padding=12)
    main_frame.pack(fill=tk.BOTH, expand=True)

    title_text = f'发现新版本 v{info["version"]}（来源: {info["source"]}）'
    ttk.Label(main_frame, text=title_text, font=('', 12, 'bold')).pack(anchor=tk.W, pady=(0, 8))

    ttk.Label(main_frame, text=f'当前版本: v{APP_VERSION}  →  新版本: v{info["version"]}',
              font=('', 9)).pack(anchor=tk.W, pady=(0, 6))

    body_frame = ttk.LabelFrame(main_frame, text=' 更新内容 ', padding=6)
    body_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

    body_text = tk.Text(body_frame, wrap=tk.WORD, height=10, font=('', 9))
    body_scroll = ttk.Scrollbar(body_frame, orient=tk.VERTICAL, command=body_text.yview)
    body_text.configure(yscrollcommand=body_scroll.set)
    body_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    body_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    body_text.insert('1.0', info.get('body', '暂无更新说明'))
    body_text.configure(state=tk.DISABLED)

    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(fill=tk.X, padx=12, pady=(0, 12))

    download_path = [None]

    def on_download():
        nonlocal download_path
        assets = info.get('assets', [])
        if not assets:
            messagebox.showinfo('提示', '请前往 Gitee 发布页面手动下载安装包:\n'
                                f'https://gitee.com/{OWNER}/{REPO}/releases',
                                parent=dialog)
            return
        asset = _select_asset(assets)
        if not asset:
            messagebox.showwarning('提示', '没有找到适合当前平台的安装包', parent=dialog)
            return

        download_btn.configure(state=tk.DISABLED)
        cancel_btn.configure(state=tk.DISABLED)

        progress_win = tk.Toplevel(dialog)
        progress_win.title('下载更新')
        progress_win.transient(dialog)
        progress_win.grab_set()
        progress_win.geometry('+{}+{}'.format(dialog.winfo_rootx() + 50, dialog.winfo_rooty() + 100))
        progress_win.resizable(False, False)

        pf = ttk.Frame(progress_win, padding=16)
        pf.pack(fill=tk.BOTH, expand=True)

        ttk.Label(pf, text='正在下载更新...', font=('', 10)).pack(anchor=tk.W, pady=(0, 8))

        progress_bar = ttk.Progressbar(pf, mode='indeterminate', length=350)
        progress_bar.pack(fill=tk.X, pady=(0, 4))
        progress_bar.start(10)

        progress_label = ttk.Label(pf, text='', font=('', 9))
        progress_label.pack(anchor=tk.E)

        def update_progress(ratio):
            progress_bar.configure(mode='determinate')
            progress_bar.stop()
            progress_bar['value'] = ratio * 100
            progress_label.configure(text=f'{ratio * 100:.0f}%')
            progress_win.update_idletasks()

        def do_download():
            try:
                path = download_update(asset, progress_callback=update_progress)
                download_path[0] = path
                progress_win.destroy()
                dialog.after(0, lambda: on_download_done(path))
            except Exception as e:
                progress_win.destroy()
                dialog.after(0, lambda: on_download_error(str(e)))

        def on_download_done(path):
            if messagebox.askyesno('确认', '下载完成，是否立即安装并重启？', parent=dialog):
                install_update(path)
            else:
                messagebox.showinfo('提示', f'安装包已保存到:\n{path}', parent=dialog)
                dialog.destroy()

        def on_download_error(err):
            messagebox.showerror('下载失败', str(err), parent=dialog)
            download_btn.configure(state=tk.NORMAL)
            cancel_btn.configure(state=tk.NORMAL)

        threading.Thread(target=do_download, daemon=True).start()

    def on_ignore():
        if config_update is not None:
            ignored = config_update.get('ignored_versions', [])
            if info['version'] not in ignored:
                ignored.append(info['version'])
                config_update['ignored_versions'] = ignored
        dialog.destroy()

    def on_later():
        dialog.destroy()

    download_btn = ttk.Button(btn_frame, text='⬇ 下载', command=on_download)
    download_btn.pack(side=tk.LEFT, padx=(0, 4))
    cancel_btn = ttk.Button(btn_frame, text='稍后提醒', command=on_later)
    cancel_btn.pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(btn_frame, text='忽略此版本', command=on_ignore).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(btn_frame, text='取消', command=dialog.destroy).pack(side=tk.RIGHT)


def show_no_update(parent):
    messagebox.showinfo('检查更新', f'当前已是最新版本 v{APP_VERSION}', parent=parent)


def check_and_show(parent, config_update: dict):
    def _do_check():
        try:
            info = check_update(timeout=5)
            if info is None:
                parent.after(0, lambda: messagebox.showwarning(
                    '检查更新失败', '无法连接到更新服务器，请检查网络', parent=parent))
                return
            if not info['has_update']:
                parent.after(0, lambda: show_no_update(parent))
                return
            ignored = config_update.get('ignored_versions', [])
            if info['version'] in ignored:
                parent.after(0, lambda: show_no_update(parent))
                return
            parent.after(0, lambda: show_update_dialog(parent, info, config_update))
        except Exception:
            parent.after(0, lambda: messagebox.showwarning(
                '检查更新失败', '检查更新时发生异常', parent=parent))
    threading.Thread(target=_do_check, daemon=True).start()


def check_silent(parent, config_update: dict) -> bool:
    def _do_check():
        try:
            info = check_update(timeout=3)
            if info and info['has_update']:
                ignored = config_update.get('ignored_versions', [])
                if info['version'] not in ignored:
                    parent.after(0, lambda: show_update_dialog(parent, info, config_update))
        except Exception:
            pass
    threading.Thread(target=_do_check, daemon=True).start()
    return True
