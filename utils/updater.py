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
    """将 v1.0.0 转换为 (1,0,0)"""
    nums = re.findall(r'\d+', tag)
    return tuple(int(n) for n in nums[:3]) if nums else (0, 0, 0)


def check_update(timeout: int = 5) -> dict:
    """检查更新，返回 { 'has_update': bool, 'version': str, 'body': str, 'source': str, 'assets': [] }
    或 None（检查失败）"""
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
        except Exception:
            continue
    return None


def _select_asset(assets: list) -> dict:
    """根据当前平台选择合适的下载包"""
    sys_plat = platform.system()
    for asset in assets:
        name = asset['name'].lower()
        if sys_plat == 'Darwin' and (name.endswith('.dmg') or name.endswith('.zip')):
            return asset
        if sys_plat == 'Windows' and (name.endswith('.exe') or name.endswith('.zip')):
            return asset
        if sys_plat == 'Linux' and (name.endswith('.tar.gz') or name.endswith('.zip') or name.endswith('.AppImage')):
            return asset
    return assets[0] if assets else None


def download_update(asset: dict, progress_callback=None) -> str:
    """下载更新包到临时目录，返回本地路径"""
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
    """安装更新包并重启"""
    import zipfile
    import tempfile
    import shutil

    sys_plat = platform.system()
    try:
        if local_path.endswith('.zip'):
            extract_dir = os.path.join(tempfile.gettempdir(), 'commdebugtool_update')
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            with zipfile.ZipFile(local_path, 'r') as zf:
                zf.extractall(extract_dir)

            if sys_plat == 'Darwin':
                new_binary = os.path.join(extract_dir, 'CommDebugTool')
                subprocess.run(['xattr', '-d', 'com.apple.quarantine', new_binary],
                               capture_output=True)
                subprocess.run(['codesign', '--force', '--deep', '--sign', '-', new_binary],
                               capture_output=True)
            elif sys_plat == 'Windows':
                new_binary = os.path.join(extract_dir, 'CommDebugTool.exe')
            else:
                new_binary = os.path.join(extract_dir, 'CommDebugTool')

            if not os.path.exists(new_binary):
                subprocess.Popen(['open', extract_dir])
                sys.exit(0)

            os.chmod(new_binary, 0o755)
            current = sys.argv[0]

            if getattr(sys, 'frozen', False):
                current = sys.executable

            if os.path.exists(current):
                import stat
                backup = current + '.bak'
                try:
                    os.remove(backup)
                except:
                    pass
                os.rename(current, backup)
                shutil.copy2(new_binary, current)
                os.chmod(current, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
                if sys_plat == 'Darwin':
                    subprocess.run(['xattr', '-d', 'com.apple.quarantine', current],
                                   capture_output=True)
                    subprocess.run(['codesign', '--force', '--deep', '--sign', '-', current],
                                   capture_output=True)
                subprocess.Popen([current])
                try:
                    os.remove(backup)
                except:
                    pass
                sys.exit(0)
            else:
                subprocess.Popen([new_binary])
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
    """显示发现新版本对话框"""
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
    """显示已是最新版对话框"""
    messagebox.showinfo('检查更新', f'当前已是最新版本 v{APP_VERSION}', parent=parent)


# ===== 入口函数 =====

def check_and_show(parent, config_update: dict):
    """检查更新并显示结果（后台线程）"""
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
    """静默检查更新，有新版本返回 True（供启动时调用，由调用方处理弹窗）"""
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
