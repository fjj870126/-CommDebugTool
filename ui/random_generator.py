"""随机数据生成器 - 生成指定长度/格式的随机测试数据"""

import tkinter as tk
from tkinter import ttk, messagebox
import random
import string
import struct
from utils.hex_utils import bytes_to_hex_str
from utils.context_menu import add_entry_context_menu


class RandomGenerator(ttk.LabelFrame):
    """随机数据生成器"""

    def __init__(self, parent, on_send=None):
        super().__init__(parent, text=' 随机数据生成器 ', padding=8)
        self._on_send = on_send
        self._build_ui()

    def _build_ui(self):
        # ===== 数据类型 =====
        type_frame = ttk.LabelFrame(self, text=' 数据类型 ', padding=6)
        type_frame.pack(fill=tk.X, pady=(0, 8))

        self.data_type = tk.StringVar(value='hex')
        types = [
            ('Hex 字节', 'hex'),
            ('ASCII 字符', 'ascii'),
            ('数字', 'number'),
            ('混合', 'mixed'),
            ('自定义格式', 'custom'),
        ]
        for text, value in types:
            ttk.Radiobutton(type_frame, text=text, variable=self.data_type,
                            value=value, command=self._on_type_change).pack(side=tk.LEFT, padx=4)

        # ===== 参数配置 =====
        param_frame = ttk.LabelFrame(self, text=' 参数配置 ', padding=6)
        param_frame.pack(fill=tk.X, pady=(0, 8))

        # 长度
        row1 = ttk.Frame(param_frame)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text='长度:', font=('', 12)).pack(side=tk.LEFT)
        self.length_var = tk.StringVar(value='16')
        self.length_spin = ttk.Spinbox(row1, from_=1, to=65536,
                                       textvariable=self.length_var, width=8)
        self.length_spin.pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(row1, text='数量:', font=('', 12)).pack(side=tk.LEFT)
        self.count_var = tk.StringVar(value='1')
        ttk.Spinbox(row1, from_=1, to=1000, textvariable=self.count_var, width=6).pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(row1, text='分隔符:').pack(side=tk.LEFT)
        self.separator_var = tk.StringVar(value=' ')
        self.separator_entry = ttk.Entry(row1, textvariable=self.separator_var, width=4)
        self.separator_entry.pack(side=tk.LEFT, padx=(4, 0))
        add_entry_context_menu(self.separator_entry)

        # 范围
        row2 = ttk.Frame(param_frame)
        row2.pack(fill=tk.X, pady=2)

        ttk.Label(row2, text='最小值:').pack(side=tk.LEFT)
        self.min_var = tk.StringVar(value='0')
        self.min_entry = ttk.Entry(row2, textvariable=self.min_var, width=8)
        self.min_entry.pack(side=tk.LEFT, padx=(4, 8))
        add_entry_context_menu(self.min_entry)

        ttk.Label(row2, text='最大值:').pack(side=tk.LEFT)
        self.max_var = tk.StringVar(value='255')
        self.max_entry = ttk.Entry(row2, textvariable=self.max_var, width=8)
        self.max_entry.pack(side=tk.LEFT, padx=(4, 8))
        add_entry_context_menu(self.max_entry)

        # 固定前缀/后缀
        ttk.Label(row2, text='前缀:').pack(side=tk.LEFT, padx=(12, 0))
        self.prefix_var = tk.StringVar(value='')
        self.prefix_entry = ttk.Entry(row2, textvariable=self.prefix_var, width=10)
        self.prefix_entry.pack(side=tk.LEFT, padx=(4, 8))
        add_entry_context_menu(self.prefix_entry)

        ttk.Label(row2, text='后缀:').pack(side=tk.LEFT)
        self.suffix_var = tk.StringVar(value='')
        self.suffix_entry = ttk.Entry(row2, textvariable=self.suffix_var, width=10)
        self.suffix_entry.pack(side=tk.LEFT, padx=(4, 0))
        add_entry_context_menu(self.suffix_entry)

        # 自定义格式
        row3 = ttk.Frame(param_frame)
        row3.pack(fill=tk.X, pady=2)

        ttk.Label(row3, text='格式模板:').pack(side=tk.LEFT)
        self.format_template_var = tk.StringVar(value='AA BB CC DD {random:4} EE FF')
        self.format_template = ttk.Entry(row3, textvariable=self.format_template_var,
                                         font=('Courier New', 11))
        self.format_template.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)
        add_entry_context_menu(self.format_template)

        ttk.Label(row3, text='  {random:N}=N字节随机, {seq}=序号', font=('', 9), foreground='gray').pack(side=tk.LEFT, padx=(4, 0))

        # ===== 操作按钮 =====
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(btn_frame, text='🎲 生成', command=self._generate, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='复制结果', command=self._copy_result, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='发送', command=self._send_data, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='清空', command=self._clear, width=8).pack(side=tk.LEFT, padx=(8, 0))

        # 输出格式
        ttk.Label(btn_frame, text='输出:').pack(side=tk.LEFT, padx=(12, 2))
        self.output_format = tk.StringVar(value='hex')
        ttk.Radiobutton(btn_frame, text='Hex', variable=self.output_format,
                        value='hex').pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(btn_frame, text='文本', variable=self.output_format,
                        value='text').pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(btn_frame, text='C数组', variable=self.output_format,
                        value='c_array').pack(side=tk.LEFT, padx=2)

        # ===== 结果区 =====
        result_frame = ttk.LabelFrame(self, text=' 生成结果 ', padding=4)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.result_text = tk.Text(result_frame, height=8, font=('Courier New', 12),
                                   wrap=tk.WORD)
        text_scroll_y = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        text_scroll_x = ttk.Scrollbar(result_frame, orient=tk.HORIZONTAL, command=self.result_text.xview)
        self.result_text.configure(yscrollcommand=text_scroll_y.set, xscrollcommand=text_scroll_x.set)

        self.result_text.grid(row=0, column=0, sticky='nsew')
        text_scroll_y.grid(row=0, column=1, sticky='ns')
        text_scroll_x.grid(row=1, column=0, sticky='ew')
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        # 状态栏
        self.status_var = tk.StringVar(value='就绪')
        ttk.Label(self, textvariable=self.status_var, foreground='gray').pack(anchor=tk.W, pady=(4, 0))

    def _on_type_change(self):
        """数据类型切换"""
        dtype = self.data_type.get()
        # 自定义格式时显示模板输入
        if dtype == 'custom':
            self.format_template.configure(state='normal')
        else:
            self.format_template.configure(state='readonly')

    def _generate(self):
        """生成随机数据"""
        dtype = self.data_type.get()
        try:
            length = int(self.length_var.get())
            count = int(self.count_var.get())
        except ValueError:
            messagebox.showwarning('提示', '长度和数量必须为整数')
            return

        if length < 1 or count < 1:
            messagebox.showwarning('提示', '长度和数量必须大于 0')
            return

        try:
            min_val = int(self.min_var.get())
            max_val = int(self.max_var.get())
        except ValueError:
            min_val, max_val = 0, 255

        prefix = self.prefix_var.get().strip()
        suffix = self.suffix_var.get().strip()
        separator = self.separator_var.get()

        self.result_text.delete('1.0', tk.END)

        results = []
        for i in range(count):
            if dtype == 'custom':
                data = self._generate_custom(i)
            else:
                data = self._generate_random(dtype, length, min_val, max_val)

            if data is None:
                return

            # 添加前缀/后缀
            if prefix:
                try:
                    prefix_bytes = bytes.fromhex(prefix.replace(' ', ''))
                    data = prefix_bytes + data
                except ValueError:
                    data = prefix.encode('utf-8') + data

            if suffix:
                try:
                    suffix_bytes = bytes.fromhex(suffix.replace(' ', ''))
                    data = data + suffix_bytes
                except ValueError:
                    data = data + suffix.encode('utf-8')

            results.append(data)

            # 格式化输出
            output_mode = self.output_format.get()
            if output_mode == 'hex':
                line = bytes_to_hex_str(data)
            elif output_mode == 'text':
                try:
                    line = data.decode('utf-8')
                except Exception:
                    line = repr(data)
            else:  # c_array
                hex_bytes = ', '.join(f'0x{b:02X}' for b in data)
                line = f'uint8_t data[{len(data)}] = {{{hex_bytes}}};'

            if count > 1:
                self.result_text.insert(tk.END, f'[{i + 1}] {line}\n')
            else:
                self.result_text.insert(tk.END, line)

        # 更新状态
        total_bytes = sum(len(d) for d in results)
        self.status_var.set(f'已生成 {count} 条, 共 {total_bytes} 字节')

    def _generate_random(self, dtype: str, length: int, min_val: int, max_val: int) -> bytes:
        """生成随机数据"""
        if dtype == 'hex':
            return bytes([random.randint(min_val, max_val) for _ in range(length)])

        elif dtype == 'ascii':
            chars = string.ascii_letters + string.digits + string.punctuation + ' '
            return ''.join(random.choice(chars) for _ in range(length)).encode('utf-8')

        elif dtype == 'number':
            # 生成数字字符串
            num_str = ''.join(random.choice(string.digits) for _ in range(length))
            return num_str.encode('utf-8')

        elif dtype == 'mixed':
            # 混合 Hex 和 ASCII
            result = bytearray()
            for _ in range(length):
                if random.random() < 0.5:
                    result.append(random.randint(min_val, max_val))
                else:
                    result.append(ord(random.choice(string.ascii_letters + string.digits + ' ')))
            return bytes(result)

        return bytes([random.randint(0, 255) for _ in range(length)])

    def _generate_custom(self, seq: int) -> bytes:
        """根据格式模板生成"""
        template = self.format_template_var.get().strip()
        if not template:
            messagebox.showwarning('提示', '请输入格式模板')
            return None

        result = bytearray()
        parts = template.split()

        for part in parts:
            if part.startswith('{random:') and part.endswith('}'):
                # {random:N} - N 字节随机数
                try:
                    n = int(part[8:-1])
                    result.extend(random.randint(0, 255) for _ in range(n))
                except ValueError:
                    pass
            elif part == '{seq}':
                # {seq} - 序号（4 字节大端）
                result.extend(struct.pack('>I', seq))
            elif part == '{seq:2}':
                # {seq:2} - 序号（2 字节大端）
                result.extend(struct.pack('>H', seq))
            elif part == '{seq:1}':
                # {seq:1} - 序号（1 字节）
                result.append(seq & 0xFF)
            elif part.startswith('{') and part.endswith('}'):
                # 其他占位符，跳过
                pass
            else:
                # Hex 字节
                try:
                    result.append(int(part, 16))
                except ValueError:
                    # 非 Hex，作为 ASCII 处理
                    result.extend(part.encode('utf-8'))

        return bytes(result)

    def _copy_result(self):
        """复制结果到剪贴板"""
        text = self.result_text.get('1.0', tk.END).strip()
        if text:
            try:
                self.winfo_toplevel().clipboard_clear()
                self.winfo_toplevel().clipboard_append(text)
                self.status_var.set(f'已复制 {len(text)} 字符')
            except Exception:
                pass

    def _send_data(self):
        """发送生成的数据"""
        text = self.result_text.get('1.0', tk.END).strip()
        if not text:
            return

        if self._on_send:
            # 解析 Hex 数据发送
            lines = text.split('\n')
            for line in lines:
                # 去掉序号前缀
                if line.startswith('['):
                    line = line.split(']', 1)[-1].strip()
                # 去掉 C 数组格式
                if line.startswith('uint8_t'):
                    continue

                try:
                    hex_clean = ''.join(line.split())
                    data = bytes.fromhex(hex_clean)
                    self._on_send(data)
                except ValueError:
                    # 非 Hex 格式，作为文本发送
                    self._on_send(line.encode('utf-8'))

            self.status_var.set(f'已发送 {len(lines)} 条数据')

    def _clear(self):
        """清空结果"""
        self.result_text.delete('1.0', tk.END)
        self.status_var.set('就绪')

    def get_settings(self) -> dict:
        return {
            'data_type': self.data_type.get(),
            'length': self.length_var.get(),
            'count': self.count_var.get(),
            'separator': self.separator_var.get(),
            'min_val': self.min_var.get(),
            'max_val': self.max_var.get(),
            'prefix': self.prefix_var.get(),
            'suffix': self.suffix_var.get(),
            'format_template': self.format_template_var.get(),
            'output_format': self.output_format.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        self.data_type.set(settings.get('data_type', 'hex'))
        self.length_var.set(settings.get('length', '16'))
        self.count_var.set(settings.get('count', '1'))
        self.separator_var.set(settings.get('separator', ' '))
        self.min_var.set(settings.get('min_val', '0'))
        self.max_var.set(settings.get('max_val', '255'))
        self.prefix_var.set(settings.get('prefix', ''))
        self.suffix_var.set(settings.get('suffix', ''))
        self.format_template_var.set(settings.get('format_template', 'AA BB CC DD {random:4} EE FF'))
        self.output_format.set(settings.get('output_format', 'hex'))
