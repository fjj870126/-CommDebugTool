"""位操作计算器 - 位与/或/异或/移位/取反等操作"""

import tkinter as tk
from tkinter import ttk, messagebox
from utils.context_menu import add_entry_context_menu


class BitwisePanel(ttk.LabelFrame):
    """位操作计算器"""

    def __init__(self, parent):
        super().__init__(parent, text=' 位操作计算器 ', padding=8)
        self._build_ui()

    def _build_ui(self):
        # ===== 操作数输入 =====
        op_frame = ttk.LabelFrame(self, text=' 操作数 ', padding=6)
        op_frame.pack(fill=tk.X, pady=(0, 8))

        # 操作数 A
        row1 = ttk.Frame(op_frame)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text='操作数 A:', font=('', 12)).pack(side=tk.LEFT)
        self.op_a_var = tk.StringVar(value='0xAA')
        self.op_a_entry = ttk.Entry(row1, textvariable=self.op_a_var,
                                    font=('Courier New', 12), width=20)
        self.op_a_entry.pack(side=tk.LEFT, padx=(4, 8), fill=tk.X, expand=True)
        add_entry_context_menu(self.op_a_entry)

        # 操作数 B
        row2 = ttk.Frame(op_frame)
        row2.pack(fill=tk.X, pady=2)

        ttk.Label(row2, text='操作数 B:', font=('', 12)).pack(side=tk.LEFT)
        self.op_b_var = tk.StringVar(value='0x0F')
        self.op_b_entry = ttk.Entry(row2, textvariable=self.op_b_var,
                                    font=('Courier New', 12), width=20)
        self.op_b_entry.pack(side=tk.LEFT, padx=(4, 8), fill=tk.X, expand=True)
        add_entry_context_menu(self.op_b_entry)

        # 输入格式提示
        ttk.Label(row2, text='支持: 0xHex, 0bBinary, Decimal', font=('', 9), foreground='gray').pack(side=tk.LEFT)

        # 位数选择
        row3 = ttk.Frame(op_frame)
        row3.pack(fill=tk.X, pady=2)

        ttk.Label(row3, text='位数:', font=('', 12)).pack(side=tk.LEFT)
        self.bit_width = tk.StringVar(value='8')
        for w in ['8', '16', '32', '64']:
            ttk.Radiobutton(row3, text=f'{w}位', variable=self.bit_width,
                            value=w).pack(side=tk.LEFT, padx=4)

        # ===== 操作按钮 =====
        btn_frame = ttk.LabelFrame(self, text=' 操作 ', padding=6)
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        ops = [
            ('& 与', self._op_and), ('| 或', self._op_or),
            ('^ 异或', self._op_xor), ('~ 取反(A)', self._op_not),
            ('<< 左移(A)', self._op_shl), ('>> 右移(A)', self._op_shr),
        ]
        for i, (text, cmd) in enumerate(ops):
            btn = ttk.Button(btn_frame, text=text, command=cmd, width=14)
            btn.grid(row=i // 3, column=i % 3, padx=3, pady=2, sticky='ew')
            btn_frame.columnconfigure(i % 3, weight=1)

        # ===== 结果区 =====
        result_frame = ttk.LabelFrame(self, text=' 结果 ', padding=6)
        result_frame.pack(fill=tk.BOTH, expand=True)

        # 结果显示
        self.result_var = tk.StringVar(value='')
        self.result_entry = ttk.Entry(result_frame, textvariable=self.result_var,
                                      font=('Courier New', 14, 'bold'), state='readonly')
        self.result_entry.pack(fill=tk.X, pady=(0, 8))

        # 详细结果表格
        tree_container = ttk.Frame(result_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        columns = ('format', 'value_a', 'value_b', 'result')
        self.result_tree = ttk.Treeview(tree_container, columns=columns, show='headings',
                                        height=4)
        self.result_tree.heading('format', text='格式')
        self.result_tree.heading('value_a', text='操作数 A')
        self.result_tree.heading('value_b', text='操作数 B')
        self.result_tree.heading('result', text='结果')

        self.result_tree.column('format', width=80, minwidth=60, anchor=tk.CENTER)
        self.result_tree.column('value_a', width=120, minwidth=80, anchor=tk.CENTER)
        self.result_tree.column('value_b', width=120, minwidth=80, anchor=tk.CENTER)
        self.result_tree.column('result', width=120, minwidth=80, anchor=tk.CENTER)

        style = ttk.Style()
        style.configure('Bitwise.Treeview', font=('Courier New', 11), rowheight=26)
        style.configure('Bitwise.Treeview.Heading', font=('', 11, 'bold'))
        self.result_tree.configure(style='Bitwise.Treeview')

        result_scroll = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=result_scroll.set)

        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        result_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 状态栏
        self.status_var = tk.StringVar(value='就绪')
        ttk.Label(self, textvariable=self.status_var, foreground='gray').pack(anchor=tk.W, pady=(4, 0))

    def _parse_value(self, text: str) -> int:
        """解析数值，支持 0x/0b/十进制"""
        text = text.strip()
        if not text:
            raise ValueError('输入为空')
        if text.startswith('0x') or text.startswith('0X'):
            return int(text, 16)
        elif text.startswith('0b') or text.startswith('0B'):
            return int(text, 2)
        else:
            return int(text)

    def _mask(self, value: int) -> int:
        """按位数掩码"""
        width = int(self.bit_width.get())
        if width >= 64:
            return value
        return value & ((1 << width) - 1)

    def _format_result(self, value: int) -> str:
        """格式化结果"""
        width = int(self.bit_width.get())
        if width <= 8:
            return f'0x{value:02X}  (Dec: {value}, Bin: {value:08b})'
        elif width <= 16:
            return f'0x{value:04X}  (Dec: {value}, Bin: {value:016b})'
        elif width <= 32:
            return f'0x{value:08X}  (Dec: {value})'
        else:
            return f'0x{value:016X}  (Dec: {value})'

    def _update_result(self, result: int, op_name: str):
        """更新结果显示"""
        width = int(self.bit_width.get())
        result = self._mask(result)

        # 主结果
        self.result_var.set(self._format_result(result))

        # 解析操作数
        try:
            a = self._parse_value(self.op_a_var.get())
            b = self._parse_value(self.op_b_var.get())
        except ValueError:
            a = b = 0

        a = self._mask(a)
        b = self._mask(b)

        # 清空旧结果
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

        # 插入各种格式
        if width <= 8:
            bin_fmt = f'{{:0{width}b}}'
            self.result_tree.insert('', tk.END, values=('Hex', f'0x{a:02X}', f'0x{b:02X}', f'0x{result:02X}'))
            self.result_tree.insert('', tk.END, values=('Dec', str(a), str(b), str(result)))
            self.result_tree.insert('', tk.END, values=('Bin', bin_fmt.format(a), bin_fmt.format(b), bin_fmt.format(result)))
        elif width <= 16:
            self.result_tree.insert('', tk.END, values=('Hex', f'0x{a:04X}', f'0x{b:04X}', f'0x{result:04X}'))
            self.result_tree.insert('', tk.END, values=('Dec', str(a), str(b), str(result)))
            self.result_tree.insert('', tk.END, values=('Bin', f'{a:016b}', f'{b:016b}', f'{result:016b}'))
        elif width <= 32:
            self.result_tree.insert('', tk.END, values=('Hex', f'0x{a:08X}', f'0x{b:08X}', f'0x{result:08X}'))
            self.result_tree.insert('', tk.END, values=('Dec', str(a), str(b), str(result)))
        else:
            self.result_tree.insert('', tk.END, values=('Hex', f'0x{a:016X}', f'0x{b:016X}', f'0x{result:016X}'))
            self.result_tree.insert('', tk.END, values=('Dec', str(a), str(b), str(result)))

        self.status_var.set(f'{op_name}: {self._format_result(result)}')

    def _get_operands(self):
        """获取操作数"""
        try:
            a = self._parse_value(self.op_a_var.get())
            b = self._parse_value(self.op_b_var.get())
            return a, b
        except ValueError as e:
            messagebox.showwarning('输入错误', f'操作数格式错误: {e}')
            return None, None

    def _op_and(self):
        a, b = self._get_operands()
        if a is not None:
            self._update_result(a & b, 'AND')

    def _op_or(self):
        a, b = self._get_operands()
        if a is not None:
            self._update_result(a | b, 'OR')

    def _op_xor(self):
        a, b = self._get_operands()
        if a is not None:
            self._update_result(a ^ b, 'XOR')

    def _op_not(self):
        a, _ = self._get_operands()
        if a is not None:
            width = int(self.bit_width.get())
            if width >= 64:
                result = ~a
            else:
                result = (~a) & ((1 << width) - 1)
            self._update_result(result, 'NOT')

    def _op_shl(self):
        a, b = self._get_operands()
        if a is not None:
            self._update_result(a << b, 'SHL')

    def _op_shr(self):
        a, b = self._get_operands()
        if a is not None:
            self._update_result(a >> b, 'SHR')

    def get_settings(self) -> dict:
        return {
            'op_a': self.op_a_var.get(),
            'op_b': self.op_b_var.get(),
            'bit_width': self.bit_width.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        self.op_a_var.set(settings.get('op_a', '0xAA'))
        self.op_b_var.set(settings.get('op_b', '0x0F'))
        self.bit_width.set(settings.get('bit_width', '8'))
