"""数据对比面板 - 对比两段数据的差异"""

import tkinter as tk
from tkinter import ttk, messagebox
from utils.hex_utils import hex_str_to_bytes, bytes_to_hex_str
from utils.context_menu import add_entry_context_menu


class ComparePanel(ttk.LabelFrame):
    """数据对比面板"""

    def __init__(self, parent):
        super().__init__(parent, text=' 数据对比 ', padding=8)
        self._build_ui()

    def _build_ui(self):
        # 数据A
        ttk.Label(self, text='数据 A (Hex):').pack(anchor=tk.W)
        self.data_a_var = tk.StringVar()
        self.data_a_entry = ttk.Entry(self, textvariable=self.data_a_var,
                                      font=('Courier New', 10))
        self.data_a_entry.pack(fill=tk.X, pady=(0, 4))
        add_entry_context_menu(self.data_a_entry)

        # 数据B
        ttk.Label(self, text='数据 B (Hex):').pack(anchor=tk.W)
        self.data_b_var = tk.StringVar()
        self.data_b_entry = ttk.Entry(self, textvariable=self.data_b_var,
                                      font=('Courier New', 10))
        self.data_b_entry.pack(fill=tk.X, pady=(0, 4))
        add_entry_context_menu(self.data_b_entry)

        # 对比按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(4, 4))
        ttk.Button(btn_frame, text='🔍 对比', command=self._do_compare, width=10).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text='清空', command=self._clear, width=8).pack(side=tk.LEFT, padx=(4, 0))

        # 对比模式
        ttk.Label(btn_frame, text='模式:').pack(side=tk.LEFT, padx=(12, 0))
        self.mode_var = tk.StringVar(value='逐字节')
        mode_cb = ttk.Combobox(btn_frame, textvariable=self.mode_var,
                               values=['逐字节', '逐行(16字节)'], state='readonly', width=12)
        mode_cb.pack(side=tk.LEFT, padx=(4, 0))

        # 结果区域
        result_frame = ttk.LabelFrame(self, text=' 对比结果 ', padding=4)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.result_text = tk.Text(result_frame, height=10, font=('Courier New', 10),
                                   wrap=tk.NONE, state=tk.DISABLED)
        text_scroll_y = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        text_scroll_x = ttk.Scrollbar(result_frame, orient=tk.HORIZONTAL, command=self.result_text.xview)
        self.result_text.configure(yscrollcommand=text_scroll_y.set, xscrollcommand=text_scroll_x.set)

        self.result_text.grid(row=0, column=0, sticky='nsew')
        text_scroll_y.grid(row=0, column=1, sticky='ns')
        text_scroll_x.grid(row=1, column=0, sticky='ew')
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        # 标签
        info_frame = ttk.Frame(self)
        info_frame.pack(fill=tk.X, pady=(4, 0))
        self.status_var = tk.StringVar(value='等待对比...')
        ttk.Label(info_frame, textvariable=self.status_var, foreground='gray').pack(side=tk.LEFT)

    def _do_compare(self):
        """执行对比"""
        hex_a = self.data_a_var.get().strip()
        hex_b = self.data_b_var.get().strip()

        if not hex_a or not hex_b:
            messagebox.showwarning('提示', '请输入两段数据')
            return

        try:
            data_a = hex_str_to_bytes(hex_a)
            data_b = hex_str_to_bytes(hex_b)
        except ValueError as e:
            messagebox.showerror('错误', f'Hex 格式错误: {e}')
            return

        mode = self.mode_var.get()
        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete('1.0', tk.END)

        # 配置标签
        self.result_text.tag_configure('diff', foreground='red', background='#FFE0E0')
        self.result_text.tag_configure('same', foreground='green')
        self.result_text.tag_configure('missing', foreground='gray')
        self.result_text.tag_configure('header', font=('Courier New', 10, 'bold'))

        if mode == '逐字节':
            self._compare_byte_by_byte(data_a, data_b)
        else:
            self._compare_line_by_line(data_a, data_b)

        self.result_text.configure(state=tk.DISABLED)

        # 更新状态
        diff_count = sum(1 for a, b in zip(data_a, data_b) if a != b)
        len_diff = abs(len(data_a) - len(data_b))
        self.status_var.set(f'差异: {diff_count} 字节, 长度差: {len_diff} 字节')

    def _compare_byte_by_byte(self, data_a: bytes, data_b: bytes):
        """逐字节对比"""
        max_len = max(len(data_a), len(data_b))
        self.result_text.insert(tk.END, '偏移  │ 数据A  │ 数据B  │ 状态\n', 'header')
        self.result_text.insert(tk.END, '─' * 40 + '\n')

        for i in range(max_len):
            offset = f'{i:04X}'
            if i < len(data_a) and i < len(data_b):
                byte_a = f'{data_a[i]:02X}'
                byte_b = f'{data_b[i]:02X}'
                if data_a[i] == data_b[i]:
                    tag = 'same'
                    status = '✓'
                else:
                    tag = 'diff'
                    status = '✗'
                self.result_text.insert(tk.END, f'{offset}  │  {byte_a}    │  {byte_b}    │  {status}\n', tag)
            elif i < len(data_a):
                self.result_text.insert(tk.END, f'{offset}  │  {data_a[i]:02X}    │  --    │  仅A\n', 'missing')
            else:
                self.result_text.insert(tk.END, f'{offset}  │  --    │  {data_b[i]:02X}    │  仅B\n', 'missing')

    def _compare_line_by_line(self, data_a: bytes, data_b: bytes):
        """逐行(16字节)对比"""
        max_len = max(len(data_a), len(data_b))
        self.result_text.insert(tk.END, '偏移    │ 数据A (Hex)                          │ 数据B (Hex)\n', 'header')
        self.result_text.insert(tk.END, '─' * 80 + '\n')

        for offset in range(0, max_len, 16):
            line_a = data_a[offset:offset+16]
            line_b = data_b[offset:offset+16]

            hex_a = ' '.join(f'{b:02X}' for b in line_a) if line_a else '(无)'
            hex_b = ' '.join(f'{b:02X}' for b in line_b) if line_b else '(无)'

            # 检查这一行是否有差异
            has_diff = False
            for i in range(max(len(line_a), len(line_b))):
                if i < len(line_a) and i < len(line_b):
                    if line_a[i] != line_b[i]:
                        has_diff = True
                        break
                else:
                    has_diff = True
                    break

            tag = 'diff' if has_diff else 'same'
            self.result_text.insert(tk.END, f'{offset:04X}    │ {hex_a:<48} │ {hex_b}\n', tag)

    def _clear(self):
        """清空所有"""
        self.data_a_var.set('')
        self.data_b_var.set('')
        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete('1.0', tk.END)
        self.result_text.configure(state=tk.DISABLED)
        self.status_var.set('等待对比...')

    def get_settings(self) -> dict:
        return {
            'data_a': self.data_a_var.get(),
            'data_b': self.data_b_var.get(),
            'mode': self.mode_var.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        if 'data_a' in settings:
            self.data_a_var.set(settings['data_a'])
        if 'data_b' in settings:
            self.data_b_var.set(settings['data_b'])
        if 'mode' in settings:
            self.mode_var.set(settings['mode'])
