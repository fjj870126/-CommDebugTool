"""Base64 编解码面板 - Base64 ↔ Hex/文本/二进制 互转"""

import tkinter as tk
from tkinter import ttk
import base64
from utils.hex_utils import hex_str_to_bytes, bytes_to_hex_str
from utils.context_menu import add_entry_context_menu


class Base64Panel(ttk.LabelFrame):
    """Base64 编解码面板"""

    def __init__(self, parent):
        super().__init__(parent, text=' Base64 编解码 ', padding=8)
        self._build_ui()

    def _build_ui(self):
        # ===== 输入区 =====
        ttk.Label(self, text='输入:', font=('', 12, 'bold')).pack(anchor=tk.W)

        input_frame = ttk.Frame(self)
        input_frame.pack(fill=tk.X, pady=(0, 4))

        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(input_frame, textvariable=self.input_var,
                                     font=('Courier New', 12))
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        add_entry_context_menu(self.input_entry)

        # 输入模式
        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill=tk.X, pady=(0, 8))

        self.input_mode = tk.StringVar(value='text')
        ttk.Radiobutton(mode_frame, text='文本', variable=self.input_mode,
                        value='text', command=self._on_mode_change).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(mode_frame, text='Hex', variable=self.input_mode,
                        value='hex', command=self._on_mode_change).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(mode_frame, text='Base64', variable=self.input_mode,
                        value='base64', command=self._on_mode_change).pack(side=tk.LEFT, padx=2)

        # ===== 操作按钮 =====
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(btn_frame, text='→ 编码为 Base64', command=self._do_encode, width=16).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='→ 解码 Base64', command=self._do_decode, width=16).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='清空', command=self._clear, width=8).pack(side=tk.LEFT, padx=(8, 0))

        # ===== 结果区 =====
        ttk.Label(self, text='结果:', font=('', 12, 'bold')).pack(anchor=tk.W, pady=(4, 0))

        # 结果使用 Notebook 分多个标签页显示
        result_notebook = ttk.Notebook(self)
        result_notebook.pack(fill=tk.BOTH, expand=True)

        # Base64 结果
        b64_frame = ttk.Frame(result_notebook, padding=4)
        result_notebook.add(b64_frame, text=' Base64 ')

        self.b64_result_var = tk.StringVar()
        self.b64_result = ttk.Entry(b64_frame, textvariable=self.b64_result_var,
                                    font=('Courier New', 12))
        self.b64_result.pack(fill=tk.X, expand=True, pady=2)
        add_entry_context_menu(self.b64_result)

        b64_btn_frame = ttk.Frame(b64_frame)
        b64_btn_frame.pack(fill=tk.X)
        ttk.Button(b64_btn_frame, text='复制', command=lambda: self._copy_result(self.b64_result_var.get()), width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(b64_btn_frame, text='URL安全', command=self._to_urlsafe, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(b64_btn_frame, text='标准', command=self._to_standard, width=8).pack(side=tk.LEFT, padx=2)

        # Hex 结果
        hex_frame = ttk.Frame(result_notebook, padding=4)
        result_notebook.add(hex_frame, text=' Hex ')

        self.hex_result_var = tk.StringVar()
        self.hex_result = ttk.Entry(hex_frame, textvariable=self.hex_result_var,
                                    font=('Courier New', 12))
        self.hex_result.pack(fill=tk.X, expand=True, pady=2)
        add_entry_context_menu(self.hex_result)

        ttk.Button(hex_frame, text='复制', command=lambda: self._copy_result(self.hex_result_var.get()), width=8).pack(anchor=tk.W, padx=2)

        # 文本结果
        text_frame = ttk.Frame(result_notebook, padding=4)
        result_notebook.add(text_frame, text=' 文本 ')

        self.text_result = tk.Text(text_frame, height=6, font=('Courier New', 12),
                                   wrap=tk.WORD)
        text_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_result.yview)
        self.text_result.configure(yscrollcommand=text_scroll.set)
        self.text_result.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 二进制结果
        bin_frame = ttk.Frame(result_notebook, padding=4)
        result_notebook.add(bin_frame, text=' 二进制 ')

        self.bin_result = tk.Text(bin_frame, height=6, font=('Courier New', 12),
                                  wrap=tk.WORD)
        bin_scroll = ttk.Scrollbar(bin_frame, orient=tk.VERTICAL, command=self.bin_result.yview)
        self.bin_result.configure(yscrollcommand=bin_scroll.set)
        self.bin_result.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bin_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 状态栏
        self.status_var = tk.StringVar(value='就绪')
        ttk.Label(self, textvariable=self.status_var, foreground='gray').pack(anchor=tk.W, pady=(4, 0))

        # 绑定输入变化自动转换
        self.input_var.trace_add('write', lambda *args: self._auto_convert())

    def _on_mode_change(self):
        """输入模式切换"""
        self._auto_convert()

    def _auto_convert(self):
        """自动转换（根据输入模式智能判断）"""
        raw = self.input_var.get().strip()
        if not raw:
            return

        mode = self.input_mode.get()
        try:
            if mode == 'text':
                # 文本 → 编码为 Base64
                data = raw.encode('utf-8')
                b64 = base64.b64encode(data).decode('ascii')
                self.b64_result_var.set(b64)
                self.hex_result_var.set(bytes_to_hex_str(data))
                self.text_result.delete('1.0', tk.END)
                self.text_result.insert('1.0', raw)
                self._update_bin_result(data)
                self.status_var.set(f'文本 {len(raw)} 字符 → Base64 {len(b64)} 字符')

            elif mode == 'hex':
                # Hex → 解码为字节 → 编码为 Base64
                hex_clean = ''.join(raw.split())
                data = bytes.fromhex(hex_clean)
                b64 = base64.b64encode(data).decode('ascii')
                self.b64_result_var.set(b64)
                self.hex_result_var.set(bytes_to_hex_str(data))
                try:
                    text = data.decode('utf-8')
                    self.text_result.delete('1.0', tk.END)
                    self.text_result.insert('1.0', text)
                except Exception:
                    self.text_result.delete('1.0', tk.END)
                    self.text_result.insert('1.0', f'(非 UTF-8 文本, {len(data)} 字节)')
                self._update_bin_result(data)
                self.status_var.set(f'Hex {len(hex_clean)//2} 字节 → Base64 {len(b64)} 字符')

            elif mode == 'base64':
                # Base64 → 解码
                try:
                    data = base64.b64decode(raw)
                except Exception:
                    try:
                        data = base64.urlsafe_b64decode(raw)
                    except Exception:
                        self.status_var.set('Base64 格式错误')
                        return
                b64 = base64.b64encode(data).decode('ascii')
                self.b64_result_var.set(b64)
                self.hex_result_var.set(bytes_to_hex_str(data))
                try:
                    text = data.decode('utf-8')
                    self.text_result.delete('1.0', tk.END)
                    self.text_result.insert('1.0', text)
                except Exception:
                    self.text_result.delete('1.0', tk.END)
                    self.text_result.insert('1.0', f'(非 UTF-8 文本, {len(data)} 字节)')
                self._update_bin_result(data)
                self.status_var.set(f'Base64 {len(raw)} 字符 → {len(data)} 字节')

        except Exception as e:
            self.status_var.set(f'错误: {e}')

    def _update_bin_result(self, data: bytes):
        """更新二进制显示"""
        self.bin_result.delete('1.0', tk.END)
        lines = []
        for i, b in enumerate(data):
            lines.append(f'{b:08b}')
            if (i + 1) % 8 == 0:
                lines.append('\n')
            elif (i + 1) % 4 == 0:
                lines.append(' ')
            else:
                lines.append(' ')
        self.bin_result.insert('1.0', ''.join(lines))

    def _do_encode(self):
        """编码为 Base64"""
        self.input_mode.set('text')
        self._auto_convert()

    def _do_decode(self):
        """解码 Base64"""
        self.input_mode.set('base64')
        self._auto_convert()

    def _to_urlsafe(self):
        """转换为 URL 安全的 Base64"""
        b64 = self.b64_result_var.get().strip()
        if b64:
            try:
                data = base64.b64decode(b64)
                urlsafe = base64.urlsafe_b64encode(data).decode('ascii')
                self.b64_result_var.set(urlsafe)
                self.status_var.set('已转换为 URL 安全格式')
            except Exception as e:
                self.status_var.set(f'转换失败: {e}')

    def _to_standard(self):
        """转换为标准 Base64"""
        b64 = self.b64_result_var.get().strip()
        if b64:
            try:
                data = base64.urlsafe_b64decode(b64)
                standard = base64.b64encode(data).decode('ascii')
                self.b64_result_var.set(standard)
                self.status_var.set('已转换为标准格式')
            except Exception:
                try:
                    data = base64.b64decode(b64)
                    standard = base64.b64encode(data).decode('ascii')
                    self.b64_result_var.set(standard)
                    self.status_var.set('已是标准格式')
                except Exception as e:
                    self.status_var.set(f'转换失败: {e}')

    def _copy_result(self, text):
        """复制结果到剪贴板"""
        if text:
            try:
                self.winfo_toplevel().clipboard_clear()
                self.winfo_toplevel().clipboard_append(text)
                self.status_var.set(f'已复制: {text[:50]}{"..." if len(text) > 50 else ""}')
            except Exception:
                pass

    def _clear(self):
        """清空所有"""
        self.input_var.set('')
        self.b64_result_var.set('')
        self.hex_result_var.set('')
        self.text_result.delete('1.0', tk.END)
        self.bin_result.delete('1.0', tk.END)
        self.status_var.set('就绪')

    def get_settings(self) -> dict:
        return {
            'input_mode': self.input_mode.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        self.input_mode.set(settings.get('input_mode', 'text'))
