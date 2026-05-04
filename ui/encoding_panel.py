"""编码转换器 - UTF-8/GBK/GB2312/Big5 等编码互转"""

import tkinter as tk
from tkinter import ttk, messagebox
from utils.context_menu import add_entry_context_menu


class EncodingPanel(ttk.LabelFrame):
    """编码转换器"""

    ENCODINGS = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'shift_jis',
                 'euc-kr', 'latin-1', 'ascii', 'utf-16', 'utf-16le', 'utf-16be']

    def __init__(self, parent):
        super().__init__(parent, text=' 编码转换器 ', padding=8)
        self._build_ui()

    def _build_ui(self):
        # ===== 输入区 =====
        ttk.Label(self, text='输入文本:', font=('', 12, 'bold')).pack(anchor=tk.W)

        input_frame = ttk.Frame(self)
        input_frame.pack(fill=tk.X, pady=(0, 4))

        self.input_text = tk.Text(input_frame, height=4, font=('Courier New', 12),
                                  wrap=tk.WORD, undo=True)
        input_scroll = ttk.Scrollbar(input_frame, orient=tk.VERTICAL, command=self.input_text.yview)
        self.input_text.configure(yscrollcommand=input_scroll.set)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        input_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 输入编码选择
        enc_frame = ttk.Frame(self)
        enc_frame.pack(fill=tk.X, pady=(4, 8))

        ttk.Label(enc_frame, text='源编码:', font=('', 12)).pack(side=tk.LEFT)
        self.src_encoding = tk.StringVar(value='utf-8')
        src_cb = ttk.Combobox(enc_frame, textvariable=self.src_encoding,
                              values=self.ENCODINGS, state='readonly', width=12)
        src_cb.pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(enc_frame, text='目标编码:', font=('', 12)).pack(side=tk.LEFT)
        self.dst_encoding = tk.StringVar(value='gbk')
        dst_cb = ttk.Combobox(enc_frame, textvariable=self.dst_encoding,
                              values=self.ENCODINGS, state='readonly', width=12)
        dst_cb.pack(side=tk.LEFT, padx=(4, 8))

        ttk.Button(enc_frame, text='→ 转换', command=self._do_convert, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(enc_frame, text='↔ 互换', command=self._swap_encodings, width=8).pack(side=tk.LEFT, padx=2)

        # ===== 结果区 =====
        ttk.Label(self, text='转换结果:', font=('', 12, 'bold')).pack(anchor=tk.W, pady=(4, 0))

        result_frame = ttk.Frame(self)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        self.result_text = tk.Text(result_frame, height=4, font=('Courier New', 12),
                                   wrap=tk.WORD)
        result_scroll = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=result_scroll.set)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        result_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # ===== Hex 显示 =====
        hex_frame = ttk.LabelFrame(self, text=' Hex 表示 ', padding=4)
        hex_frame.pack(fill=tk.X, pady=(0, 8))

        self.src_hex_var = tk.StringVar(value='')
        ttk.Label(hex_frame, text='源 Hex:').pack(anchor=tk.W)
        self.src_hex_entry = ttk.Entry(hex_frame, textvariable=self.src_hex_var,
                                       font=('Courier New', 11), state='readonly')
        self.src_hex_entry.pack(fill=tk.X, pady=(0, 4))

        self.dst_hex_var = tk.StringVar(value='')
        ttk.Label(hex_frame, text='目标 Hex:').pack(anchor=tk.W)
        self.dst_hex_entry = ttk.Entry(hex_frame, textvariable=self.dst_hex_var,
                                       font=('Courier New', 11), state='readonly')
        self.dst_hex_entry.pack(fill=tk.X)

        # ===== 操作按钮 =====
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(0, 4))

        ttk.Button(btn_frame, text='复制结果', command=self._copy_result, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='复制源 Hex', command=lambda: self._copy_text(self.src_hex_var.get()), width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='复制目标 Hex', command=lambda: self._copy_text(self.dst_hex_var.get()), width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='清空', command=self._clear, width=8).pack(side=tk.LEFT, padx=(8, 0))

        # 状态栏
        self.status_var = tk.StringVar(value='就绪')
        ttk.Label(self, textvariable=self.status_var, foreground='gray').pack(anchor=tk.W, pady=(2, 0))

    def _do_convert(self):
        """执行编码转换"""
        text = self.input_text.get('1.0', tk.END).rstrip('\n')
        if not text:
            messagebox.showwarning('提示', '请输入要转换的文本')
            return

        src_enc = self.src_encoding.get()
        dst_enc = self.dst_encoding.get()

        try:
            # 先按源编码解码为 Unicode
            if src_enc == dst_enc:
                # 相同编码，直接显示 Hex
                data = text.encode(src_enc)
                self.result_text.delete('1.0', tk.END)
                self.result_text.insert('1.0', text)
                self.src_hex_var.set(self._bytes_to_hex(data))
                self.dst_hex_var.set(self._bytes_to_hex(data))
                self.status_var.set(f'编码相同 ({src_enc}), 长度: {len(data)} 字节')
                return

            # 解码为 Unicode
            try:
                unicode_text = text.encode(src_enc).decode(src_enc)
            except UnicodeDecodeError:
                # 如果已经是 Unicode 字符串，直接使用
                unicode_text = text

            # 源编码的 Hex
            src_data = unicode_text.encode(src_enc, errors='replace')
            self.src_hex_var.set(self._bytes_to_hex(src_data))

            # 转换为目标编码
            dst_data = unicode_text.encode(dst_enc, errors='replace')
            self.dst_hex_var.set(self._bytes_to_hex(dst_data))

            # 显示目标编码的文本
            try:
                dst_text = dst_data.decode(dst_enc)
            except Exception:
                dst_text = dst_data.decode(dst_enc, errors='replace')

            self.result_text.delete('1.0', tk.END)
            self.result_text.insert('1.0', dst_text)

            self.status_var.set(f'{src_enc} → {dst_enc}: {len(src_data)} → {len(dst_data)} 字节')

        except Exception as e:
            self.status_var.set(f'转换失败: {e}')
            messagebox.showerror('转换错误', str(e))

    def _swap_encodings(self):
        """互换源/目标编码"""
        src = self.src_encoding.get()
        dst = self.dst_encoding.get()
        self.src_encoding.set(dst)
        self.dst_encoding.set(src)
        # 如果有文本，自动转换
        if self.input_text.get('1.0', tk.END).strip():
            self._do_convert()

    def _bytes_to_hex(self, data: bytes) -> str:
        """字节转 Hex 字符串"""
        return ' '.join(f'{b:02X}' for b in data)

    def _copy_result(self):
        """复制结果"""
        text = self.result_text.get('1.0', tk.END).strip()
        self._copy_text(text)

    def _copy_text(self, text):
        """复制文本到剪贴板"""
        if text:
            try:
                self.winfo_toplevel().clipboard_clear()
                self.winfo_toplevel().clipboard_append(text)
                self.status_var.set(f'已复制: {text[:50]}{"..." if len(text) > 50 else ""}')
            except Exception:
                pass

    def _clear(self):
        """清空所有"""
        self.input_text.delete('1.0', tk.END)
        self.result_text.delete('1.0', tk.END)
        self.src_hex_var.set('')
        self.dst_hex_var.set('')
        self.status_var.set('就绪')

    def get_settings(self) -> dict:
        return {
            'src_encoding': self.src_encoding.get(),
            'dst_encoding': self.dst_encoding.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        self.src_encoding.set(settings.get('src_encoding', 'utf-8'))
        self.dst_encoding.set(settings.get('dst_encoding', 'gbk'))
