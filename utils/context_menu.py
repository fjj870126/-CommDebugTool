"""右键菜单工具 - 为 Entry/Combobox 控件添加复制/粘贴/剪切功能"""

import tkinter as tk
from tkinter import ttk


def add_entry_context_menu(entry: tk.Entry):
    """为 Entry 控件添加右键菜单（剪切/复制/粘贴/全选）"""
    menu = tk.Menu(entry, tearoff=0)
    menu.add_command(label='剪切', command=lambda: entry.event_generate('<<Cut>>'))
    menu.add_command(label='复制', command=lambda: entry.event_generate('<<Copy>>'))
    menu.add_command(label='粘贴', command=lambda: entry.event_generate('<<Paste>>'))
    menu.add_separator()
    menu.add_command(label='全选', command=lambda: _select_all(entry))

    def _show(event):
        menu.tk_popup(event.x_root, event.y_root)

    entry.bind('<Button-3>', _show)  # Windows/Linux 右键
    entry.bind('<Button-2>', _show)  # macOS 中键
    entry.bind('<Control-Button-1>', _show)  # macOS 控制+左键模拟右键


def add_combobox_context_menu(cb: ttk.Combobox):
    """为 Combobox 控件添加右键菜单（剪切/复制/粘贴/全选）"""
    menu = tk.Menu(cb, tearoff=0)
    menu.add_command(label='剪切', command=lambda: cb.event_generate('<<Cut>>'))
    menu.add_command(label='复制', command=lambda: cb.event_generate('<<Copy>>'))
    menu.add_command(label='粘贴', command=lambda: cb.event_generate('<<Paste>>'))
    menu.add_separator()
    menu.add_command(label='全选', command=lambda: _select_all(cb))

    def _show(event):
        menu.tk_popup(event.x_root, event.y_root)

    cb.bind('<Button-3>', _show)  # Windows/Linux 右键
    cb.bind('<Button-2>', _show)  # macOS 中键
    cb.bind('<Control-Button-1>', _show)  # macOS 控制+左键模拟右键


def _select_all(widget):
    """全选 Entry/Combobox 内容"""
    widget.select_range(0, tk.END)
    widget.icursor(tk.END)
