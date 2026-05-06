"""全局设置对话框 - 主题、字体、日志限制等"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from ui.theme import set_theme, get_theme, get_theme_names, DARK, LIGHT


DEFAULT_SETTINGS = {
    'ui_theme': 'dark',
    'ttk_theme': 'clam',
    'font_family': 'Courier New',
    'font_size': 10,
    'log_max_lines': 10000,
    'auto_scroll': True,
    'timestamp_format': '%H:%M:%S.%f',
    'show_send_time': True,
    'show_recv_time': True,
    'hex_uppercase': True,
    'hex_separator': ' ',
    'confirm_exit': True,
    'save_log_on_exit': False,
    'status_bar': True,
}


class SettingsDialog:
    """全局设置对话框"""

    def __init__(self, parent, main_window=None, settings=None, on_save=None):
        self._parent = parent
        self._main_window = main_window
        self._on_save = on_save
        self._dialog = None
        self._result = None
        self._settings = dict(DEFAULT_SETTINGS)
        if settings:
            self._settings.update(settings)

    def get_setting(self, key: str, default=None):
        return self._settings.get(key, default)

    def get_all_settings(self) -> dict:
        return dict(self._settings)

    def show(self):
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title('全局设置')
        self._dialog.resizable(False, False)
        self._dialog.transient(self._parent)
        self._dialog.grab_set()
        self._dialog.withdraw()
        self._dialog.update_idletasks()
        pw = self._parent.winfo_width()
        ph = self._parent.winfo_height()
        px = self._parent.winfo_rootx()
        py = self._parent.winfo_rooty()
        w, h = 620, 580
        self._dialog.geometry(f'{w}x{h}+{px + (pw - w) // 2}+{py + (ph - h) // 2}')
        self._dialog.deiconify()
        self._dialog.after_idle(self._build_all)
        self._dialog.protocol('WM_DELETE_WINDOW', self._on_close)

    def _build_all(self):
        notebook = ttk.Notebook(self._dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        self._build_ui(notebook)

        btn_frame = ttk.Frame(self._dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text='恢复默认', command=self._reset_defaults).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text='保存', command=self._save_and_close).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_frame, text='应用', command=self._apply_settings).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_frame, text='取消', command=self._dialog.destroy).pack(side=tk.RIGHT, padx=(4, 0))

    def _build_ui(self, notebook):
        # ---- 外观设置 ----
        appearance_frame = ttk.Frame(notebook, padding=10)
        notebook.add(appearance_frame, text='  外观  ')

        row = 0

        ttk.Label(appearance_frame, text='界面风格:', font=('', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 2))
        row += 1

        style = ttk.Style()
        available_themes = list(style.theme_names())
        self.ttk_theme_var = tk.StringVar(
            value=self._settings.get('ttk_theme', 'clam'))

        theme_frame = ttk.Frame(appearance_frame)
        theme_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 8))
        self.ttk_theme_cb = ttk.Combobox(theme_frame, textvariable=self.ttk_theme_var,
                                         values=available_themes, state='readonly', width=18)
        self.ttk_theme_cb.pack(side=tk.LEFT)
        ttk.Button(theme_frame, text='应用', command=self._apply_ttk_theme,
                   width=6).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(theme_frame, text=f'共 {len(available_themes)} 个',
                  foreground='gray', font=('', 9)).pack(side=tk.LEFT, padx=(8, 0))
        row += 1

        ttk.Separator(appearance_frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=3, sticky='ew', pady=6)
        row += 1

        ttk.Label(appearance_frame, text='编辑器主题:', font=('', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 2))
        row += 1

        theme_names = get_theme_names()
        self.ui_theme_var = tk.StringVar(
            value=self._settings.get('ui_theme', DARK))
        self.ui_theme_var.trace('w', lambda *a: self._apply_ui_theme())
        ui_theme_frame = ttk.Frame(appearance_frame)
        ui_theme_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 8))
        for t_name in theme_names:
            label = '暗色' if t_name == DARK else '亮色'
            ttk.Radiobutton(ui_theme_frame, text=label,
                            variable=self.ui_theme_var, value=t_name).pack(side=tk.LEFT, padx=2)
        row += 1

        ttk.Separator(appearance_frame, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=3, sticky='ew', pady=6)
        row += 1

        ttk.Label(appearance_frame, text='字体:', font=('', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 2))
        row += 1

        font_frame = ttk.Frame(appearance_frame)
        font_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 8))
        self.font_family_var = tk.StringVar(value=self._settings.get('font_family', 'Courier New'))
        font_family_cb = ttk.Combobox(font_frame, textvariable=self.font_family_var,
                                      values=['Courier New', 'Consolas', 'Monaco',
                                              'Menlo', 'Source Code Pro', 'Fira Code'],
                                      state='readonly', width=15)
        font_family_cb.pack(side=tk.LEFT)
        self.font_size_var = tk.StringVar(value=str(self._settings.get('font_size', 10)))
        ttk.Spinbox(font_frame, from_=8, to=24, textvariable=self.font_size_var,
                    width=4).pack(side=tk.LEFT, padx=(4, 0))
        row += 1

        ttk.Label(appearance_frame, text='Hex 显示:', font=('', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 2))
        row += 1

        hex_frame = ttk.Frame(appearance_frame)
        hex_frame.grid(row=row, column=0, columnspan=3, sticky=tk.W, pady=(0, 4))
        self.hex_upper_var = tk.BooleanVar(value=self._settings.get('hex_uppercase', True))
        ttk.Checkbutton(hex_frame, text='大写', variable=self.hex_upper_var).pack(side=tk.LEFT)
        ttk.Label(hex_frame, text='分隔符:').pack(side=tk.LEFT, padx=(10, 2))
        self.hex_sep_var = tk.StringVar(value=self._settings.get('hex_separator', ' '))
        ttk.Combobox(hex_frame, textvariable=self.hex_sep_var,
                     values=[' ', '', ':', '-'], state='readonly', width=4).pack(side=tk.LEFT)

        # ---- 日志设置 ----
        log_frame = ttk.Frame(notebook, padding=10)
        notebook.add(log_frame, text='  日志  ')

        row = 0
        ttk.Label(log_frame, text='最大行数:').grid(row=row, column=0, sticky=tk.W, pady=4)
        self.log_max_var = tk.StringVar(value=str(self._settings.get('log_max_lines', 10000)))
        ttk.Spinbox(log_frame, from_=100, to=100000, increment=100,
                    textvariable=self.log_max_var, width=8).grid(row=row, column=1, sticky=tk.W, padx=10, pady=4)
        row += 1

        self.auto_scroll_var = tk.BooleanVar(value=self._settings.get('auto_scroll', True))
        ttk.Checkbutton(log_frame, text='自动滚动到最新', variable=self.auto_scroll_var).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=4)
        row += 1

        self.show_send_time_var = tk.BooleanVar(value=self._settings.get('show_send_time', True))
        ttk.Checkbutton(log_frame, text='显示发送时间', variable=self.show_send_time_var).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=4)
        row += 1

        self.show_recv_time_var = tk.BooleanVar(value=self._settings.get('show_recv_time', True))
        ttk.Checkbutton(log_frame, text='显示接收时间', variable=self.show_recv_time_var).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=4)
        row += 1

        self.save_log_exit_var = tk.BooleanVar(value=self._settings.get('save_log_on_exit', False))
        ttk.Checkbutton(log_frame, text='退出时自动保存日志', variable=self.save_log_exit_var).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=4)
        row += 1

        # ---- 快捷键 ----
        shortcut_frame = ttk.Frame(notebook, padding=10)
        notebook.add(shortcut_frame, text='  快捷键  ')

        shortcuts = [
            ('Ctrl+T / Cmd+T', '新增连接'),
            ('Ctrl+Enter / Cmd+Enter', '发送数据'),
            ('Ctrl+L / Cmd+L', '清空日志'),
            ('Ctrl+F / Cmd+F', '聚焦日志搜索'),
            ('Ctrl+W / Cmd+W', '断开连接'),
            ('Ctrl+M / Cmd+M', '打开MQTT窗口'),
            ('Ctrl+1~9 / Cmd+1~9', '切换工具面板'),
        ]

        ttk.Label(shortcut_frame, text='快捷键', font=('', 9, 'bold')).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 4))
        ttk.Label(shortcut_frame, text='功能', font=('', 9, 'bold')).grid(
            row=0, column=1, sticky=tk.W, padx=(20, 0), pady=(0, 4))

        for i, (key, desc) in enumerate(shortcuts, 1):
            ttk.Label(shortcut_frame, text=key).grid(
                row=i, column=0, sticky=tk.W, pady=2)
            ttk.Label(shortcut_frame, text=desc).grid(
                row=i, column=1, sticky=tk.W, padx=(20, 0), pady=2)

    def _apply_ui_theme(self):
        theme_name = self.ui_theme_var.get()
        set_theme(theme_name)

    def _apply_settings(self):
        """应用设置（不关闭对话框）"""
        self._apply_ui_theme()
        self._apply_ttk_theme()
        self._settings['font_family'] = self.font_family_var.get()
        self._settings['font_size'] = int(self.font_size_var.get())
        self._settings['hex_uppercase'] = self.hex_upper_var.get()
        self._settings['hex_separator'] = self.hex_sep_var.get()
        self._settings['log_max_lines'] = int(self.log_max_var.get())
        self._settings['auto_scroll'] = self.auto_scroll_var.get()
        self._settings['show_send_time'] = self.show_send_time_var.get()
        self._settings['show_recv_time'] = self.show_recv_time_var.get()
        self._settings['save_log_on_exit'] = self.save_log_exit_var.get()
        self._result = dict(self._settings)
        if self._main_window:
            self._main_window.apply_settings(self._settings)
        if self._on_save:
            self._on_save(dict(self._settings))

    def _on_close(self):
        self._dialog.destroy()

    def _apply_ttk_theme(self):
        theme_name = self.ttk_theme_var.get()
        try:
            style = ttk.Style()
            style.theme_use(theme_name)
        except Exception as e:
            messagebox.showerror('错误', f'应用主题失败: {e}', parent=self._dialog)

    def _reset_defaults(self):
        if messagebox.askyesno('确认', '恢复所有设置为默认值？', parent=self._dialog):
            self.ui_theme_var.set('dark')
            self.ttk_theme_var.set('clam')
            self.font_family_var.set('Courier New')
            self.font_size_var.set('10')
            self.hex_upper_var.set(True)
            self.hex_sep_var.set(' ')
            self.log_max_var.set('10000')
            self.auto_scroll_var.set(True)
            self.show_send_time_var.set(True)
            self.show_recv_time_var.set(True)
            self.save_log_exit_var.set(False)

    def _save_and_close(self):
        self._settings['ui_theme'] = self.ui_theme_var.get()
        selected = self.ttk_theme_cb.get()
        self._settings['ttk_theme'] = selected if selected else self.ttk_theme_var.get()
        try:
            ttk.Style().theme_use(self._settings['ttk_theme'])
        except Exception:
            pass
        self._settings['font_family'] = self.font_family_var.get()
        self._settings['font_size'] = int(self.font_size_var.get())
        self._settings['hex_uppercase'] = self.hex_upper_var.get()
        self._settings['hex_separator'] = self.hex_sep_var.get()
        self._settings['log_max_lines'] = int(self.log_max_var.get())
        self._settings['auto_scroll'] = self.auto_scroll_var.get()
        self._settings['show_send_time'] = self.show_send_time_var.get()
        self._settings['show_recv_time'] = self.show_recv_time_var.get()
        self._settings['save_log_on_exit'] = self.save_log_exit_var.get()

        self._result = dict(self._settings)

        if self._main_window:
            self._main_window.apply_settings(self._settings)

        if self._on_save:
            self._on_save(dict(self._settings))

        self._dialog.destroy()
