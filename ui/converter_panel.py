"""数据转换器面板 - Hex/Decimal/Binary/ASCII 互转、大小端转换"""

import tkinter as tk
from tkinter import ttk, messagebox
from utils.hex_utils import hex_str_to_bytes, bytes_to_hex_str
from utils.context_menu import add_entry_context_menu


class ConverterPanel(ttk.LabelFrame):
    """数据转换器面板 - 格式转换 + 大小端转换"""

    def __init__(self, parent):
        super().__init__(parent, text=' 数据转换器 ', padding=8)
        self._build_ui()

    def _build_ui(self):
        # ===== 格式转换 =====
        convert_frame = ttk.Frame(self)
        convert_frame.pack(fill=tk.BOTH, expand=True)

        # 输入区
        ttk.Label(convert_frame, text='输入:', font=('', 12, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 4))

        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(convert_frame, textvariable=self.input_var,
                                     font=('Courier New', 12))
        self.input_entry.grid(row=1, column=0, sticky='ew', padx=(0, 4))
        add_entry_context_menu(self.input_entry)

        mode_frame = ttk.Frame(convert_frame)
        mode_frame.grid(row=2, column=0, sticky=tk.W, pady=(4, 8))

        self.input_mode = tk.StringVar(value='hex')
        ttk.Radiobutton(mode_frame, text='Hex', variable=self.input_mode,
                        value='hex', command=self._on_input_change).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(mode_frame, text='Decimal', variable=self.input_mode,
                        value='dec', command=self._on_input_change).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(mode_frame, text='Binary', variable=self.input_mode,
                        value='bin', command=self._on_input_change).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(mode_frame, text='ASCII', variable=self.input_mode,
                        value='ascii', command=self._on_input_change).pack(side=tk.LEFT, padx=2)

        ttk.Label(convert_frame, text='转换结果:', font=('', 12, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=(8, 4))

        results_frame = ttk.Frame(convert_frame)
        results_frame.grid(row=4, column=0, sticky='nsew')
        convert_frame.columnconfigure(0, weight=1)
        convert_frame.rowconfigure(4, weight=1)

        columns = ('format', 'value')
        self.result_tree = ttk.Treeview(results_frame, columns=columns, show='tree',
                                        height=6, selectmode='browse')
        self.result_tree.heading('#0', text='格式')
        self.result_tree.heading('value', text='值')

        self.result_tree.column('#0', width=80, minwidth=60, anchor=tk.W)
        self.result_tree.column('value', width=300, minwidth=100, anchor=tk.W)
        style = ttk.Style()
        style.configure('ConvResult.Treeview', font=('Courier New', 12), rowheight=28)
        style.configure('ConvResult.Treeview.Heading', font=('', 12, 'bold'))
        self.result_tree.configure(style='ConvResult.Treeview')

        result_scroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=result_scroll.set)

        self.result_tree.grid(row=0, column=0, sticky='nsew')
        result_scroll.grid(row=0, column=1, sticky='ns')
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        self.input_var.trace_add('write', lambda *args: self._update_conversion())

        endian_frame = ttk.LabelFrame(convert_frame, text=' 大小端转换 ', padding=6)
        endian_frame.grid(row=5, column=0, sticky='ew', pady=(8, 0))

        ttk.Label(endian_frame, text='原始Hex:', font=('', 12)).pack(side=tk.LEFT)
        self.endian_input_var = tk.StringVar()
        self.endian_input = ttk.Entry(endian_frame, textvariable=self.endian_input_var,
                                      font=('Courier New', 12), width=20)
        self.endian_input.pack(side=tk.LEFT, padx=(4, 8), fill=tk.X, expand=True)
        add_entry_context_menu(self.endian_input)

        ttk.Button(endian_frame, text='→ 大端', command=lambda: self._convert_endian('big'), width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(endian_frame, text='→ 小端', command=lambda: self._convert_endian('little'), width=8).pack(side=tk.LEFT, padx=2)

        self.endian_result_var = tk.StringVar()
        self.endian_result = ttk.Entry(endian_frame, textvariable=self.endian_result_var,
                                       font=('Courier New', 12), state='readonly', width=20)
        self.endian_result.pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)

    def _on_input_change(self):
        self._update_conversion()

    def _update_conversion(self):
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

        raw = self.input_var.get().strip()
        if not raw:
            return

        mode = self.input_mode.get()
        try:
            if mode == 'hex':
                hex_clean = ''.join(raw.split())
                data = bytes.fromhex(hex_clean)
                dec_val = int(hex_clean, 16)
                bin_str = bin(dec_val)[2:]
                ascii_str = self._bytes_to_ascii(data)
                self.result_tree.insert('', tk.END, text='Hex', values=(bytes_to_hex_str(data),))
                self.result_tree.insert('', tk.END, text='Decimal', values=(str(dec_val),))
                self.result_tree.insert('', tk.END, text='Binary', values=(bin_str,))
                self.result_tree.insert('', tk.END, text='ASCII', values=(ascii_str,))

            elif mode == 'dec':
                dec_val = int(raw)
                hex_str = format(dec_val, 'X')
                if len(hex_str) % 2:
                    hex_str = '0' + hex_str
                data = bytes.fromhex(hex_str)
                bin_str = bin(dec_val)[2:]
                ascii_str = self._bytes_to_ascii(data)
                self.result_tree.insert('', tk.END, text='Hex', values=(bytes_to_hex_str(data),))
                self.result_tree.insert('', tk.END, text='Decimal', values=(str(dec_val),))
                self.result_tree.insert('', tk.END, text='Binary', values=(bin_str,))
                self.result_tree.insert('', tk.END, text='ASCII', values=(ascii_str,))

            elif mode == 'bin':
                bin_str = raw.replace(' ', '')
                dec_val = int(bin_str, 2)
                hex_str = format(dec_val, 'X')
                if len(hex_str) % 2:
                    hex_str = '0' + hex_str
                data = bytes.fromhex(hex_str)
                ascii_str = self._bytes_to_ascii(data)
                self.result_tree.insert('', tk.END, text='Hex', values=(bytes_to_hex_str(data),))
                self.result_tree.insert('', tk.END, text='Decimal', values=(str(dec_val),))
                self.result_tree.insert('', tk.END, text='Binary', values=(bin_str,))
                self.result_tree.insert('', tk.END, text='ASCII', values=(ascii_str,))

            elif mode == 'ascii':
                data = raw.encode('utf-8')
                hex_str = bytes_to_hex_str(data)
                dec_val = int(data.hex(), 16)
                bin_str = bin(dec_val)[2:]
                self.result_tree.insert('', tk.END, text='Hex', values=(hex_str,))
                self.result_tree.insert('', tk.END, text='Decimal', values=(str(dec_val),))
                self.result_tree.insert('', tk.END, text='Binary', values=(bin_str,))
                self.result_tree.insert('', tk.END, text='ASCII', values=(raw,))

        except (ValueError, Exception) as e:
            self.result_tree.insert('', tk.END, text='错误', values=(str(e),))

    def _bytes_to_ascii(self, data: bytes) -> str:
        result = ''
        for b in data:
            if 32 <= b <= 126:
                result += chr(b)
            else:
                result += f'[{b:02X}]'
        return result

    def _convert_endian(self, target: str):
        raw = self.endian_input_var.get().strip()
        if not raw:
            return
        try:
            hex_clean = ''.join(raw.split())
            data = bytes.fromhex(hex_clean)
            result = data[::-1]
            self.endian_result_var.set(bytes_to_hex_str(result))
        except Exception as e:
            self.endian_result_var.set(f'错误: {e}')

    def get_settings(self) -> dict:
        return {
            'input': self.input_var.get(),
            'mode': self.input_mode.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        if 'input' in settings:
            self.input_var.set(settings['input'])
        if 'mode' in settings:
            self.input_mode.set(settings['mode'])
