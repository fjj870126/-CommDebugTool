"""协议编辑器 - 合并模板库 + 组包 + 解析，一站式协议编辑工具"""

import os
import json
import copy
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from utils.context_menu import add_entry_context_menu, add_combobox_context_menu
from utils.hex_utils import hex_str_to_bytes, bytes_to_hex_str
from packet.checksum import calc_checksum, get_algorithm_names
from ui.theme import get_theme
from protocols import PRESET_TEMPLATES


class ToolTip:
    """鼠标悬停提示工具类"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind('<Enter>', self._show_tip)
        self.widget.bind('<Leave>', self._hide_tip)

    def _show_tip(self, event=None):
        if self.tip_window:
            return
        display_text = getattr(self.widget, '_tooltip_text', None) or self.text
        if not display_text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f'+{x}+{y}')
        label = tk.Label(tw, text=display_text, justify=tk.LEFT,
                         background=get_theme().color('tooltip_bg'),
                         foreground=get_theme().color('tooltip_fg'),
                         relief=tk.SOLID, borderwidth=1,
                         font=('Courier New', 9), padx=8, pady=4,
                         wraplength=600)
        label.pack()

    def _hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class FieldEditDialog(tk.Toplevel):
    """字段编辑对话框 - 支持类型、枚举映射、位解析"""

    def __init__(self, parent, title='编辑字段', field=None, field_names: list = None):
        super().__init__(parent)
        self.title(title)
        self.withdraw()
        self.resizable(False, False)
        self.result = None
        self._field_names = field_names or []
        self.transient(parent)
        self.grab_set()
        self.attributes('-topmost', True)
        self.after(100, self._keep_on_top)

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)

        ttk.Label(frame, text='字段名:').grid(row=0, column=0, sticky=tk.W, pady=4)
        self.name_var = tk.StringVar(value=field.get('name', '新字段') if field else '新字段')
        name_entry = ttk.Entry(frame, textvariable=self.name_var, width=20)
        name_entry.grid(row=0, column=1, padx=(8, 0), pady=4)
        add_entry_context_menu(name_entry)

        self.value_label = ttk.Label(frame, text='Hex值:')
        self.value_label.grid(row=1, column=0, sticky=tk.W, pady=4)
        value_frame = ttk.Frame(frame)
        value_frame.grid(row=1, column=1, padx=(8, 0), pady=4, sticky=tk.EW)
        self.hex_var = tk.StringVar(value=field.get('hex_value', '00') if field else '00')
        self.value_entry = ttk.Entry(value_frame, textvariable=self.hex_var, width=14, font=('Courier New', 10))
        self.value_entry.pack(side=tk.LEFT)
        add_entry_context_menu(self.value_entry)
        self._input_mode = tk.StringVar(value='hex')
        ttk.Radiobutton(value_frame, text='Hex', variable=self._input_mode,
                         value='hex', command=self._on_mode_switch).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Radiobutton(value_frame, text='Dec', variable=self._input_mode,
                         value='dec', command=self._on_mode_switch).pack(side=tk.LEFT, padx=(2, 0))

        ttk.Label(frame, text='字节数:').grid(row=2, column=0, sticky=tk.W, pady=4)
        self.count_var = tk.StringVar(value=str(field.get('byte_count', 1)) if field else '1')
        count_spin = ttk.Spinbox(frame, textvariable=self.count_var, from_=1, to=256, width=8)
        count_spin.grid(row=2, column=1, padx=(8, 0), pady=4, sticky=tk.W)

        ttk.Label(frame, text='类型:').grid(row=3, column=0, sticky=tk.W, pady=4)
        self.type_var = tk.StringVar(value=field.get('field_type', '数据') if field else '数据')
        type_cb = ttk.Combobox(frame, textvariable=self.type_var,
                              values=['数据', '固定值', '长度', '校验'],
                              state='readonly', width=10)
        type_cb.grid(row=3, column=1, padx=(8, 0), pady=4, sticky=tk.W)
        type_cb.bind('<<ComboboxSelected>>', self._on_type_change)
        add_combobox_context_menu(type_cb)

        ttk.Label(frame, text='数据类型:').grid(row=3, column=2, sticky=tk.W, pady=4, padx=(16, 0))
        self.parse_mode_var = tk.StringVar(value=field.get('parse_mode', '') if field else '')
        parse_mode_cb = ttk.Combobox(frame, textvariable=self.parse_mode_var,
                                     values=['固定值', '枚举映射', '位解析', '位标志'],
                                     state='readonly', width=10)
        parse_mode_cb.grid(row=3, column=3, padx=(4, 0), pady=4, sticky=tk.W)
        parse_mode_cb.bind('<<ComboboxSelected>>', self._on_parse_mode_change)
        add_combobox_context_menu(parse_mode_cb)

        ttk.Label(frame, text='含义:').grid(row=8, column=0, sticky=tk.W, pady=4)
        self.desc_var = tk.StringVar(value=field.get('description', '') if field else '')
        desc_entry = ttk.Entry(frame, textvariable=self.desc_var, width=20)
        desc_entry.grid(row=8, column=1, padx=(8, 0), pady=4, sticky=tk.EW)
        add_entry_context_menu(desc_entry)

        self.len_config_frame = ttk.LabelFrame(frame, text=' 长度计算配置 ', padding=6)
        self.len_config_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=(8, 0))

        if self._field_names:
            range_options = [f'{i}: {n}' for i, n in enumerate(self._field_names)]
        else:
            range_options = ['0: (无可用字段)']

        r1 = ttk.Frame(self.len_config_frame)
        r1.pack(fill=tk.X, pady=2)
        ttk.Label(r1, text='计算起始:').pack(side=tk.LEFT)
        self.len_start_var = tk.StringVar()
        self.len_start_cb = ttk.Combobox(r1, textvariable=self.len_start_var,
                                          values=range_options, state='readonly', width=14)
        self.len_start_cb.pack(side=tk.LEFT, padx=(4, 0))
        add_combobox_context_menu(self.len_start_cb)

        r2 = ttk.Frame(self.len_config_frame)
        r2.pack(fill=tk.X, pady=2)
        ttk.Label(r2, text='计算结束:').pack(side=tk.LEFT)
        self.len_end_var = tk.StringVar()
        self.len_end_cb = ttk.Combobox(r2, textvariable=self.len_end_var,
                                        values=range_options, state='readonly', width=14)
        self.len_end_cb.pack(side=tk.LEFT, padx=(4, 0))
        add_combobox_context_menu(self.len_end_cb)

        r3 = ttk.Frame(self.len_config_frame)
        r3.pack(fill=tk.X, pady=2)
        ttk.Label(r3, text='字节序:').pack(side=tk.LEFT)
        self.len_endian_var = tk.StringVar(value='big')
        ttk.Radiobutton(r3, text='大端', variable=self.len_endian_var,
                         value='big').pack(side=tk.LEFT, padx=(4, 2))
        ttk.Radiobutton(r3, text='小端', variable=self.len_endian_var,
                         value='little').pack(side=tk.LEFT, padx=2)

        if field and field.get('field_type') == '长度':
            if range_options and field.get('length_start', 0) < len(range_options):
                self.len_start_var.set(range_options[field.get('length_start', 0)])
            if range_options and field.get('length_end', 0) < len(range_options):
                self.len_end_var.set(range_options[field.get('length_end', 0)])
            self.len_endian_var.set(field.get('length_byte_order', 'big'))
        elif range_options:
            self.len_start_var.set(range_options[0])
            self.len_end_var.set(range_options[-1])

        self.chk_config_frame = ttk.LabelFrame(frame, text=' 校验配置 ', padding=6)
        self.chk_config_frame.grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=(8, 0))

        c1 = ttk.Frame(self.chk_config_frame)
        c1.pack(fill=tk.X, pady=2)
        ttk.Label(c1, text='校验算法:').pack(side=tk.LEFT)
        self.chk_algo_var = tk.StringVar(value='CRC16/MODBUS')
        self.chk_algo_cb = ttk.Combobox(c1, textvariable=self.chk_algo_var,
                                         values=get_algorithm_names(), state='readonly', width=16)
        self.chk_algo_cb.pack(side=tk.LEFT, padx=(4, 0))
        add_combobox_context_menu(self.chk_algo_cb)

        c2 = ttk.Frame(self.chk_config_frame)
        c2.pack(fill=tk.X, pady=2)
        ttk.Label(c2, text='校验起始:').pack(side=tk.LEFT)
        self.chk_start_var = tk.StringVar()
        self.chk_start_cb = ttk.Combobox(c2, textvariable=self.chk_start_var,
                                          values=range_options, state='readonly', width=14)
        self.chk_start_cb.pack(side=tk.LEFT, padx=(4, 0))
        add_combobox_context_menu(self.chk_start_cb)

        c3 = ttk.Frame(self.chk_config_frame)
        c3.pack(fill=tk.X, pady=2)
        ttk.Label(c3, text='校验结束:').pack(side=tk.LEFT)
        self.chk_end_var = tk.StringVar()
        self.chk_end_cb = ttk.Combobox(c3, textvariable=self.chk_end_var,
                                        values=range_options, state='readonly', width=14)
        self.chk_end_cb.pack(side=tk.LEFT, padx=(4, 0))
        add_combobox_context_menu(self.chk_end_cb)

        c4 = ttk.Frame(self.chk_config_frame)
        c4.pack(fill=tk.X, pady=2)
        ttk.Label(c4, text='字节序:').pack(side=tk.LEFT)
        self.chk_endian_var = tk.StringVar(value='big')
        ttk.Radiobutton(c4, text='大端', variable=self.chk_endian_var,
                         value='big').pack(side=tk.LEFT, padx=(4, 2))
        ttk.Radiobutton(c4, text='小端', variable=self.chk_endian_var,
                         value='little').pack(side=tk.LEFT, padx=2)

        if field and field.get('field_type') == '校验':
            self.chk_algo_var.set(field.get('checksum_algorithm', 'CRC16/MODBUS'))
            if range_options and field.get('checksum_start', 0) < len(range_options):
                self.chk_start_var.set(range_options[field.get('checksum_start', 0)])
            if range_options and field.get('checksum_end', 0) < len(range_options):
                self.chk_end_var.set(range_options[field.get('checksum_end', 0)])
            self.chk_endian_var.set(field.get('checksum_byte_order', 'big'))
        elif range_options:
            self.chk_start_var.set(range_options[0])
            if len(range_options) > 1:
                self.chk_end_var.set(range_options[-2])
            else:
                self.chk_end_var.set(range_options[0])

        self._enum_frame = ttk.LabelFrame(frame, text=' 枚举值映射配置 ', padding=6)
        self._enum_frame.grid(row=6, column=0, columnspan=4, sticky=tk.EW, pady=(4, 0))
        self._enum_frame.grid_remove()

        enum_mode_frame = ttk.Frame(self._enum_frame)
        enum_mode_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(enum_mode_frame, text='输入模式:').pack(side=tk.LEFT, padx=(0, 4))
        self._enum_input_mode = tk.StringVar(value='dec')
        ttk.Radiobutton(enum_mode_frame, text='Dec', variable=self._enum_input_mode,
                        value='dec', command=self._on_enum_mode_change).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(enum_mode_frame, text='Hex', variable=self._enum_input_mode,
                        value='hex', command=self._on_enum_mode_change).pack(side=tk.LEFT, padx=2)

        enum_list_frame = ttk.Frame(self._enum_frame)
        enum_list_frame.pack(fill=tk.BOTH, expand=True)

        self.enum_listbox = tk.Listbox(enum_list_frame, height=4, width=50)
        self.enum_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        enum_scroll = ttk.Scrollbar(enum_list_frame, orient=tk.VERTICAL, command=self.enum_listbox.yview)
        enum_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.enum_listbox.configure(yscrollcommand=enum_scroll.set)

        self._enum_mappings = field.get('enum_mappings', []) if field else []
        self._refresh_enum_listbox()

        enum_btn_frame = ttk.Frame(self._enum_frame)
        enum_btn_frame.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(enum_btn_frame, text='添加', command=self._add_enum_mapping, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(enum_btn_frame, text='删除', command=self._delete_enum_mapping, width=8).pack(side=tk.LEFT, padx=2)

        self._bit_frame = ttk.LabelFrame(frame, text=' 位标志配置 ', padding=6)
        self._bit_frame.grid(row=7, column=0, columnspan=4, sticky=tk.EW, pady=(4, 0))
        self._bit_frame.grid_remove()

        ttk.Label(self._bit_frame, text='请勾选需要定义的位，并填写含义：',
                 font=('', 9, 'bold')).pack(anchor=tk.W, pady=(0, 6))

        self._bit_inner = ttk.Frame(self._bit_frame)
        self._bit_inner.pack(fill=tk.BOTH, expand=True)

        self._bit_flags = field.get('bit_flags', []) if field else []
        self._bit_checkboxes = []
        self._bit_entries = []
        self._build_bit_checkboxes()

        self.count_var.trace_add('write', self._on_byte_count_change)

        self._on_type_change()
        self._on_parse_mode_change()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=9, column=0, columnspan=4, pady=(12, 0))
        ttk.Button(btn_frame, text='确定', command=self._ok, width=8).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text='取消', command=self.destroy, width=8).pack(side=tk.LEFT, padx=4)

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f'+{x}+{y}')
        self.deiconify()
        self.wait_window()

    def _on_mode_switch(self):
        raw = self.hex_var.get().strip()
        mode = self._input_mode.get()
        if mode == 'dec':
            self.value_label.config(text='Dec值:')
            try:
                val = int(raw, 16) if raw else 0
                self.hex_var.set(str(val))
            except ValueError:
                pass
        else:
            self.value_label.config(text='Hex值:')
            try:
                val = int(raw) if raw else 0
                hex_str = format(val, 'X')
                if len(hex_str) % 2:
                    hex_str = '0' + hex_str
                self.hex_var.set(hex_str)
            except ValueError:
                pass

    def _get_hex_value(self) -> str:
        raw = self.hex_var.get().strip().replace(' ', '')
        if self._input_mode.get() == 'dec':
            try:
                val = int(raw) if raw else 0
                hex_str = format(val, 'X')
                if len(hex_str) % 2:
                    hex_str = '0' + hex_str
                return hex_str
            except ValueError:
                return '00'
        return raw

    def _keep_on_top(self):
        try:
            self.attributes('-topmost', True)
        except Exception:
            pass

    def destroy(self):
        try:
            self.grab_release()
        except:
            pass
        super().destroy()

    def _on_type_change(self, event=None):
        if self.type_var.get() == '长度':
            self.len_config_frame.grid()
        else:
            self.len_config_frame.grid_remove()

        if self.type_var.get() == '校验':
            self.chk_config_frame.grid()
        else:
            self.chk_config_frame.grid_remove()

        if self.type_var.get() in ('数据', '固定值'):
            current_hex = self.hex_var.get().strip()
            if not current_hex or current_hex == '(自动)':
                try:
                    byte_count = int(self.count_var.get())
                    self.hex_var.set(' '.join(['00'] * byte_count))
                except ValueError:
                    self.hex_var.set('00')

        if self.type_var.get() == '固定值':
            self.parse_mode_var.set('固定值')
            for child in self.winfo_children():
                self._set_combobox_state(child, 'disabled')
        else:
            for child in self.winfo_children():
                self._set_combobox_state(child, 'readonly')

    def _set_combobox_state(self, widget, state):
        if isinstance(widget, ttk.Combobox):
            widget.configure(state=state)
        for child in widget.winfo_children():
            self._set_combobox_state(child, state)

    def _on_parse_mode_change(self, event=None):
        mode = self.parse_mode_var.get()
        if mode == '枚举映射':
            self._enum_frame.grid()
            self._bit_frame.grid_remove()
        elif mode == '位解析':
            self._enum_frame.grid()
            self._bit_frame.grid_remove()
        elif mode == '位标志':
            self._enum_frame.grid_remove()
            self._bit_frame.grid()
        else:
            self._enum_frame.grid_remove()
            self._bit_frame.grid_remove()

    def _build_bit_checkboxes(self):
        for w in self._bit_inner.winfo_children():
            w.destroy()
        self._bit_checkboxes.clear()
        self._bit_entries.clear()

        try:
            byte_count = int(self.count_var.get())
        except ValueError:
            byte_count = 1
        total_bits = min(byte_count * 8, 32)

        for i in range(total_bits):
            bit_frame = ttk.Frame(self._bit_inner)
            bit_frame.pack(fill=tk.X, pady=2)
            cb_var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(bit_frame, text=f'Bit{i}', variable=cb_var)
            cb.pack(side=tk.LEFT, padx=(0, 8))
            self._bit_checkboxes.append(cb_var)
            ttk.Label(bit_frame, text='含义:').pack(side=tk.LEFT, padx=(0, 4))
            entry_var = tk.StringVar()
            entry = ttk.Entry(bit_frame, textvariable=entry_var, width=20)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            add_entry_context_menu(entry)
            self._bit_entries.append(entry_var)

        for flag in self._bit_flags:
            bit_idx = flag['bit']
            if 0 <= bit_idx < len(self._bit_checkboxes):
                self._bit_checkboxes[bit_idx].set(True)
                self._bit_entries[bit_idx].set(flag['label'])

    def _on_byte_count_change(self, *args):
        if self.parse_mode_var.get() == '位标志':
            self._build_bit_checkboxes()

    def _on_enum_mode_change(self):
        self._refresh_enum_listbox()

    def _refresh_enum_listbox(self):
        self.enum_listbox.delete(0, tk.END)
        for mapping in self._enum_mappings:
            value = mapping['value']
            label = mapping['label']
            if self._enum_input_mode.get() == 'hex':
                display_value = f'0x{value:02X}'
            else:
                display_value = str(value)
            self.enum_listbox.insert(tk.END, f"{display_value} -> {label}")

    def _add_enum_mapping(self):
        from tkinter import simpledialog

        if self.parse_mode_var.get() == '位解析':
            self._add_enum_mapping_with_bits()
            return

        if self._enum_input_mode.get() == 'hex':
            value_str = simpledialog.askstring('枚举值', '请输入十六进制数值 (如: FF):', parent=self)
            if not value_str:
                return
            try:
                value = int(value_str.strip(), 16)
            except ValueError:
                self._msgbox('错误', '无效的十六进制数值', 'error')
                return
        else:
            value = simpledialog.askinteger('枚举值', '请输入十进制数值:', parent=self)
            if value is None:
                return

        label = simpledialog.askstring('含义', '请输入该值的含义:', parent=self)
        if not label:
            return

        self._enum_mappings.append({'value': value, 'label': label})
        self._refresh_enum_listbox()

    def _add_enum_mapping_with_bits(self):
        dialog = tk.Toplevel(self)
        dialog.title('添加位解析值')
        dialog.withdraw()
        dialog.transient(self)
        dialog.grab_set()
        dialog.attributes('-topmost', True)
        dialog.resizable(False, False)
        self._center_toplevel(dialog, 480, 320)

        dialog_frame = ttk.Frame(dialog, padding=12)
        dialog_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(dialog_frame, text='含义:').grid(row=0, column=0, sticky=tk.W, pady=4)
        label_var = tk.StringVar()
        label_entry = ttk.Entry(dialog_frame, textvariable=label_var, width=20)
        label_entry.grid(row=0, column=1, padx=(8, 0), pady=4)
        add_entry_context_menu(label_entry)

        ttk.Label(dialog_frame, text='勾选要匹配的位：',
                 font=('', 9, 'bold')).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(12, 6))

        try:
            byte_count = int(self.count_var.get())
        except ValueError:
            byte_count = 1
        total_bits = min(byte_count * 8, 32)
        bits_per_row = 4

        bits_frame = ttk.Frame(dialog_frame)
        bits_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(4, 8))

        bit_vars = []
        for i in range(total_bits):
            var = tk.BooleanVar(value=False)
            row = i // bits_per_row
            col = i % bits_per_row
            cb = ttk.Checkbutton(bits_frame, text=f'Bit{i:<2d}', variable=var, width=8)
            cb.grid(row=row, column=col, padx=4, pady=2, sticky=tk.W)
            bit_vars.append(var)

        value_frame = ttk.Frame(dialog_frame)
        value_frame.grid(row=4, column=0, columnspan=2, pady=(8, 0))

        ttk.Label(value_frame, text='匹配值:').pack(side=tk.LEFT)
        value_label = ttk.Label(value_frame, text='0x00 (0)', foreground='blue', font=('', 9, 'bold'))
        value_label.pack(side=tk.LEFT, padx=(4, 0))

        def update_value():
            value = 0
            for i, var in enumerate(bit_vars):
                if var.get():
                    value |= (1 << i)
            value_label.config(text=f'0x{value:02X} ({value})')

        for var in bit_vars:
            var.trace_add('write', lambda *args: update_value())

        btn_frame = ttk.Frame(dialog_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(12, 0))

        result_data = {'value': None, 'label': None}

        def on_ok():
            label = label_var.get().strip()
            if not label:
                self._msgbox('提示', '请输入含义', 'warning')
                return
            value = 0
            for i, var in enumerate(bit_vars):
                if var.get():
                    value |= (1 << i)
            result_data['value'] = value
            result_data['label'] = label
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        ttk.Button(btn_frame, text='确定', command=on_ok, width=8).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text='取消', command=on_cancel, width=8).pack(side=tk.LEFT, padx=4)

        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f'+{x}+{y}')
        dialog.deiconify()

        self.wait_window(dialog)

        if result_data['value'] is not None:
            self._enum_mappings.append({
                'value': result_data['value'],
                'label': result_data['label']
            })
            self._refresh_enum_listbox()

    def _delete_enum_mapping(self):
        sel = self.enum_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.enum_listbox.delete(idx)
        del self._enum_mappings[idx]

    @staticmethod
    def _parse_range_index(val: str) -> int:
        if not val:
            return 0
        try:
            return int(val.split(':')[0].strip())
        except (ValueError, IndexError):
            return 0

    def _ok(self):
        try:
            count = int(self.count_var.get())
        except ValueError:
            count = 1
        name = self.name_var.get().strip()
        if not name:
            name = '未命名'

        bit_flags = []
        for i in range(8):
            if i < len(self._bit_checkboxes) and self._bit_checkboxes[i].get():
                label = self._bit_entries[i].get().strip()
                if label:
                    bit_flags.append({'bit': i, 'label': label})

        self.result = {
            'name': name,
            'hex_value': self._get_hex_value(),
            'byte_count': count,
            'field_type': self.type_var.get(),
            'parse_mode': self.parse_mode_var.get(),
            'enum_mappings': self._enum_mappings,
            'bit_flags': bit_flags,
            'length_start': self._parse_range_index(self.len_start_var.get()),
            'length_end': self._parse_range_index(self.len_end_var.get()),
            'length_byte_order': self.len_endian_var.get(),
            'checksum_algorithm': self.chk_algo_var.get(),
            'checksum_start': self._parse_range_index(self.chk_start_var.get()),
            'checksum_end': self._parse_range_index(self.chk_end_var.get()),
            'checksum_byte_order': self.chk_endian_var.get(),
            'description': self.desc_var.get().strip(),
        }
        self.destroy()

    @staticmethod
    def _msgbox(title, message, kind='info'):
        getattr(messagebox, f'show{kind}')(title, message)

    def _center_toplevel(self, win, w, h):
        win.withdraw()
        win.update_idletasks()
        pw = self.winfo_screenwidth()
        ph = self.winfo_screenheight()
        pw2 = self.winfo_rootx() + self.winfo_width()
        px = max(0, (pw - w) // 2)
        py = max(0, (ph - h) // 2)
        win.geometry(f'{w}x{h}+{px}+{py}')
        win.deiconify()


class JsonFieldEditDialog(tk.Toplevel):
    """JSON 字段编辑对话框 - 支持 JSON Schema 约束"""

    def __init__(self, parent, title='编辑JSON字段', field=None):
        super().__init__(parent)
        self.title(title)
        self.withdraw()
        self.resizable(False, False)
        self.result = None
        self.transient(parent)
        self.grab_set()
        self.attributes('-topmost', True)

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)

        # 键路径
        ttk.Label(frame, text='键路径:').grid(row=0, column=0, sticky=tk.W, pady=3)
        self.key_var = tk.StringVar(value=field.get('key', '') if field else '')
        key_entry = ttk.Entry(frame, textvariable=self.key_var, width=22)
        key_entry.grid(row=0, column=1, padx=(8, 0), pady=3, sticky=tk.EW)
        add_entry_context_menu(key_entry)

        # 类型
        ttk.Label(frame, text='类型:').grid(row=0, column=2, sticky=tk.W, pady=3, padx=(16, 0))
        self.type_var = tk.StringVar(value=field.get('type', 'string') if field else 'string')
        type_cb = ttk.Combobox(frame, textvariable=self.type_var,
                               values=['string', 'integer', 'number', 'boolean', 'object', 'array'],
                               state='readonly', width=10)
        type_cb.grid(row=0, column=3, padx=(4, 0), pady=3, sticky=tk.W)

        # 必填
        ttk.Label(frame, text='必填:').grid(row=1, column=0, sticky=tk.W, pady=3)
        self.required_var = tk.BooleanVar(value=field.get('required', False) if field else False)
        ttk.Checkbutton(frame, variable=self.required_var).grid(row=1, column=1, padx=(8, 0), pady=3, sticky=tk.W)

        # 默认值
        ttk.Label(frame, text='默认值:').grid(row=2, column=0, sticky=tk.W, pady=3)
        self.default_var = tk.StringVar(value=str(field.get('default', '')) if field else '')
        default_entry = ttk.Entry(frame, textvariable=self.default_var, width=22)
        default_entry.grid(row=2, column=1, padx=(8, 0), pady=3, sticky=tk.EW)
        add_entry_context_menu(default_entry)

        # 枚举
        ttk.Label(frame, text='枚举(逗号分隔):').grid(row=3, column=0, sticky=tk.W, pady=3)
        self.enum_var = tk.StringVar(value=','.join(field.get('enum', [])) if field else '')
        enum_entry = ttk.Entry(frame, textvariable=self.enum_var, width=22)
        enum_entry.grid(row=3, column=1, padx=(8, 0), pady=3, sticky=tk.EW)
        add_entry_context_menu(enum_entry)

        # 最小值
        ttk.Label(frame, text='最小值:').grid(row=4, column=0, sticky=tk.W, pady=3)
        self.min_var = tk.StringVar(value=str(field.get('minimum', '')) if field and field.get('minimum') is not None else '')
        self.min_entry = ttk.Entry(frame, textvariable=self.min_var, width=10)
        self.min_entry.grid(row=4, column=1, padx=(8, 0), pady=3, sticky=tk.W)
        add_entry_context_menu(self.min_entry)

        # 最大值
        ttk.Label(frame, text='最大值:').grid(row=4, column=2, sticky=tk.W, pady=3, padx=(16, 0))
        self.max_var = tk.StringVar(value=str(field.get('maximum', '')) if field and field.get('maximum') is not None else '')
        self.max_entry = ttk.Entry(frame, textvariable=self.max_var, width=10)
        self.max_entry.grid(row=4, column=3, padx=(4, 0), pady=3, sticky=tk.W)
        add_entry_context_menu(self.max_entry)

        # 正则
        ttk.Label(frame, text='正则:').grid(row=5, column=0, sticky=tk.W, pady=3)
        self.pattern_var = tk.StringVar(value=field.get('pattern', '') if field else '')
        pattern_entry = ttk.Entry(frame, textvariable=self.pattern_var, width=22)
        pattern_entry.grid(row=5, column=1, padx=(8, 0), pady=3, sticky=tk.EW)
        add_entry_context_menu(pattern_entry)

        # 描述
        ttk.Label(frame, text='描述:').grid(row=6, column=0, sticky=tk.W, pady=3)
        self.desc_var = tk.StringVar(value=field.get('description', '') if field else '')
        desc_entry = ttk.Entry(frame, textvariable=self.desc_var, width=22)
        desc_entry.grid(row=6, column=1, padx=(8, 0), pady=3, columnspan=3, sticky=tk.EW)
        add_entry_context_menu(desc_entry)

        # 提示
        tip_frame = ttk.Frame(frame)
        tip_frame.grid(row=7, column=0, columnspan=4, pady=(8, 0))
        tip_text = '提示: 约束字段留空表示无约束 | 枚举值用逗号分隔 (如: online,offline,error)'
        ttk.Label(tip_frame, text=tip_text, font=('', 8), foreground='gray').pack()

        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=8, column=0, columnspan=4, pady=(12, 0))
        ttk.Button(btn_frame, text='确定', command=self._ok, width=8).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text='取消', command=self.destroy, width=8).pack(side=tk.LEFT, padx=4)

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f'+{x}+{y}')
        self.deiconify()
        self.wait_window()

    def _ok(self):
        key = self.key_var.get().strip()
        if not key:
            messagebox.showwarning('提示', '请输入键路径', parent=self)
            return

        ftype = self.type_var.get()

        default_raw = self.default_var.get().strip()
        default_val = self._parse_default(ftype, default_raw) if default_raw else None

        enum_raw = self.enum_var.get().strip()
        enum_vals = []
        if enum_raw:
            for item in [x.strip() for x in enum_raw.split(',') if x.strip()]:
                enum_vals.append(self._parse_default(ftype, item))

        min_val = self._parse_number(self.min_var.get().strip())
        max_val = self._parse_number(self.max_var.get().strip())

        pattern = self.pattern_var.get().strip() or ''

        self.result = {
            'key': key,
            'type': ftype,
            'required': self.required_var.get(),
            'default': default_val,
            'enum': enum_vals if enum_vals else [],
            'minimum': min_val,
            'maximum': max_val,
            'pattern': pattern if pattern else '',
            'description': self.desc_var.get().strip(),
        }
        self.destroy()

    @staticmethod
    def _parse_default(ftype, raw):
        if ftype == 'integer':
            try:
                return int(raw)
            except ValueError:
                return raw
        elif ftype == 'number':
            try:
                return float(raw)
            except ValueError:
                return raw
        elif ftype == 'boolean':
            return raw.lower() in ('true', '1', 'yes')
        else:
            return raw

    @staticmethod
    def _parse_number(raw):
        if not raw:
            return None
        try:
            if '.' in raw:
                return float(raw)
            return int(raw)
        except ValueError:
            return None

    def destroy(self):
        try:
            self.grab_release()
        except:
            pass
        super().destroy()


class ProtocolEditor(ttk.LabelFrame):
    """协议编辑器 - 合并模板库 + 组包 + 解析"""

    def __init__(self, parent, on_send=None, log_panel=None, parse_panel=None):
        super().__init__(parent, text=' 协议编辑器 ', padding=8)
        self._on_send = on_send
        self._log_panel = log_panel
        self._parse_panel = parse_panel
        self._custom_templates = {}
        self._fields = []
        self._undo_stack = []
        self._current_proto_type = 'hex'
        self._build_ui()
        self._load_presets()

    def _msgbox(self, title, message, kind='info'):
        win = self.winfo_toplevel()
        getattr(messagebox, f'show{kind}')(title, message, parent=win)

    def _askyesno(self, title, message):
        return messagebox.askyesno(title, message, parent=self.winfo_toplevel())

    def _center_toplevel(self, win, w, h):
        win.withdraw()
        win.update_idletasks()
        pw = self.winfo_toplevel().winfo_width()
        ph = self.winfo_toplevel().winfo_height()
        px = self.winfo_toplevel().winfo_rootx()
        py = self.winfo_toplevel().winfo_rooty()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        win.geometry(f'{w}x{h}+{x}+{y}')
        win.deiconify()

    def _build_ui(self):
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # ===== 左侧：模板树 =====
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=2)

        ttk.Label(left_frame, text='📂 模板库', font=('', 10, 'bold')).pack(anchor=tk.W)

        tree_toolbar = ttk.Frame(left_frame)
        tree_toolbar.pack(fill=tk.X, pady=(2, 4))
        ttk.Button(tree_toolbar, text='➕ 协议', command=self._new_protocol, width=8).pack(side=tk.LEFT, padx=1)
        ttk.Button(tree_toolbar, text='➕ 命令', command=self._new_command, width=8).pack(side=tk.LEFT, padx=1)
        _del_btn = ttk.Button(tree_toolbar, text='🗑', command=self._delete_item, width=3)
        _del_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(_del_btn, '删除')
        _import_btn = ttk.Button(tree_toolbar, text='📥', command=self._import_templates, width=3)
        _import_btn.pack(side=tk.RIGHT, padx=1)
        ToolTip(_import_btn, '导入模板')
        _export_btn = ttk.Button(tree_toolbar, text='📤', command=self._export_templates, width=3)
        _export_btn.pack(side=tk.RIGHT, padx=1)
        ToolTip(_export_btn, '导出模板')

        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=('desc',), show='tree', height=8)
        self.tree.heading('#0', text='协议/命令')
        self.tree.heading('desc', text='说明')
        self.tree.column('#0', width=160, minwidth=100)
        self.tree.column('desc', width=120, minwidth=60)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)

        # ===== 中间：字段编辑 =====
        mid_frame = ttk.Frame(main_paned)
        main_paned.add(mid_frame, weight=3)

        info_frame = ttk.Frame(mid_frame)
        info_frame.pack(fill=tk.X, pady=(0, 4))
        self._info_var = tk.StringVar(value='(请选择命令)')
        ttk.Label(info_frame, textvariable=self._info_var, font=('', 10, 'bold')).pack(side=tk.LEFT)
        self._desc_var = tk.StringVar(value='')
        ttk.Label(info_frame, textvariable=self._desc_var, foreground='gray').pack(side=tk.LEFT, padx=(8, 0))

        # 协议类型指示
        self._proto_type_var = tk.StringVar(value='')
        ttk.Label(info_frame, textvariable=self._proto_type_var, font=('', 8)).pack(side=tk.RIGHT, padx=(4, 0))

        table_frame = ttk.Frame(mid_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        self._json_columns = ('key', 'jtype', 'required', 'default', 'enum', 'desc')
        self._hex_columns = ('name', 'hex', 'bytes', 'type', 'desc')
        self.treeview = ttk.Treeview(table_frame, columns=self._hex_columns, show='headings', selectmode='browse', height=6)
        self._setup_hex_columns()
        self._hex_shown = True

        tv_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.treeview.yview)
        self.treeview.configure(yscrollcommand=tv_scroll.set)
        self.treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tv_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.treeview.bind('<Double-1>', self._on_field_double_click)

        btn_row = ttk.Frame(mid_frame)
        btn_row.pack(fill=tk.X, pady=(0, 4))
        for text, cmd, w in [('➕ 添加', self._add_field, 8), ('✏️ 编辑', self._edit_field, 8),
                             ('🗑 删除', self._delete_field, 6), ('↑ 上移', self._move_up, 6),
                             ('↓ 下移', self._move_down, 6), ('↩ 撤销', self._undo, 6)]:
            ttk.Button(btn_row, text=text, command=cmd, width=w).pack(side=tk.LEFT, padx=1)

        gen_frame = ttk.LabelFrame(mid_frame, text=' 生成数据 ', padding=4)
        gen_frame.pack(fill=tk.X)

        self._data_var = tk.StringVar(value='')
        self._data_entry = ttk.Entry(gen_frame, textvariable=self._data_var,
                                     font=('Courier New', 11), state='readonly')
        self._data_entry.pack(fill=tk.X, pady=(0, 4))
        ToolTip(self._data_entry, '')
        self._data_entry._tooltip_text = ''
        self._data_var.trace_add('write', self._on_data_var_change)
        self._on_data_var_change()

        btn_row2 = ttk.Frame(gen_frame)
        btn_row2.pack(fill=tk.X)
        _send_btn = ttk.Button(btn_row2, text='📤', command=self._send_data, width=3)
        _send_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(_send_btn, '发送数据')
        _copy_btn = ttk.Button(btn_row2, text='📋', command=self._copy_data, width=3)
        _copy_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(_copy_btn, '复制数据')
        _refresh_btn = ttk.Button(btn_row2, text='🔄', command=self._refresh_data, width=3)
        _refresh_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(_refresh_btn, '刷新数据')

        # JSON 专用按钮
        self._json_btn_frame = ttk.Frame(btn_row2)
        self._json_btn_frame.pack(side=tk.LEFT, padx=(4, 0))
        _fmt_btn = ttk.Button(self._json_btn_frame, text='格式化', command=self._json_format, width=6)
        _fmt_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(_fmt_btn, 'JSON 格式化')
        _cmp_btn = ttk.Button(self._json_btn_frame, text='压缩', command=self._json_compress, width=5)
        _cmp_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(_cmp_btn, 'JSON 压缩')
        _val_btn = ttk.Button(self._json_btn_frame, text='验证', command=self._json_validate, width=5)
        _val_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(_val_btn, '验证 JSON')
        self._json_btn_frame.pack_forget()

        _save_btn = ttk.Button(btn_row2, text='💾', command=self._save_as_template, width=3)
        _save_btn.pack(side=tk.RIGHT, padx=1)
        ToolTip(_save_btn, '保存为模板')
        _load_btn = ttk.Button(btn_row2, text='🔽', command=self._load_to_parser, width=3)
        _load_btn.pack(side=tk.RIGHT, padx=1)
        ToolTip(_load_btn, '加载到解析器')

    def _setup_hex_columns(self):
        self.treeview.configure(columns=self._hex_columns)
        self.treeview.heading('name', text='字段名')
        self.treeview.heading('hex', text='Hex值')
        self.treeview.heading('bytes', text='字节数')
        self.treeview.heading('type', text='类型')
        self.treeview.heading('desc', text='含义')
        self.treeview.column('name', width=100, minwidth=60)
        self.treeview.column('hex', width=100, minwidth=60)
        self.treeview.column('bytes', width=60, minwidth=40, anchor=tk.CENTER)
        self.treeview.column('type', width=70, minwidth=50, anchor=tk.CENTER)
        self.treeview.column('desc', width=150, minwidth=60)
        for c in self._json_columns:
            if c not in self._hex_columns:
                try:
                    self.treeview.column(c, width=0, minwidth=0, stretch=False)
                except:
                    pass

    def _setup_json_columns(self):
        self.treeview.configure(columns=self._json_columns)
        self.treeview.heading('key', text='键路径')
        self.treeview.heading('jtype', text='类型')
        self.treeview.heading('required', text='必填')
        self.treeview.heading('default', text='默认值')
        self.treeview.heading('enum', text='枚举/约束')
        self.treeview.heading('desc', text='描述')
        self.treeview.column('key', width=120, minwidth=80)
        self.treeview.column('jtype', width=70, minwidth=50, anchor=tk.CENTER)
        self.treeview.column('required', width=40, minwidth=30, anchor=tk.CENTER)
        self.treeview.column('default', width=80, minwidth=50)
        self.treeview.column('enum', width=120, minwidth=60)
        self.treeview.column('desc', width=120, minwidth=60)
        for c in self._hex_columns:
            if c not in self._json_columns:
                try:
                    self.treeview.column(c, width=0, minwidth=0, stretch=False)
                except:
                    pass

    def _load_presets(self):
        for protocol, commands in PRESET_TEMPLATES.items():
            is_json = any(
                isinstance(cmd_info, dict) and cmd_info.get('type') == 'json'
                for cmd_info in commands.values()
            )
            prefix = '[J] ' if is_json else '[H] '
            proto_id = self.tree.insert('', tk.END, text=f'📦 {prefix}{protocol}',
                                        values=('预设',), open=False)
            for cmd_name, cmd_info in commands.items():
                cmd_type = ''
                if isinstance(cmd_info, dict):
                    cmd_type = cmd_info.get('type', '')
                self.tree.insert(proto_id, tk.END, text=f'  {cmd_name}',
                                 values=(cmd_info.get('desc', ''),))
        if self._custom_templates:
            self._refresh_custom_tree()

    def _refresh_custom_tree(self):
        for item in self.tree.get_children():
            if self.tree.item(item, 'text').startswith('📁'):
                self.tree.delete(item)
        for protocol, commands in self._custom_templates.items():
            is_json = commands.get('_proto_type') == 'json' or any(
                isinstance(cmd_info, dict) and cmd_info.get('type') == 'json'
                for cmd_info in commands.values()
            )
            prefix = '[J] ' if is_json else '[H] '
            proto_id = self.tree.insert('', tk.END, text=f'📁 {prefix}{protocol}',
                                        values=('自定义',), open=True)
            for cmd_name, cmd_info in commands.items():
                if cmd_name == '_proto_type':
                    continue
                self.tree.insert(proto_id, tk.END, text=f'  {cmd_name}',
                                 values=(cmd_info.get('desc'),))

    def _get_proto_type(self, protocol, command=None):
        if protocol in PRESET_TEMPLATES:
            if command and command in PRESET_TEMPLATES[protocol]:
                cmd_info = PRESET_TEMPLATES[protocol][command]
                if isinstance(cmd_info, dict):
                    return cmd_info.get('type', 'hex')
            else:
                for cmd_name, cmd_info in PRESET_TEMPLATES[protocol].items():
                    if isinstance(cmd_info, dict) and cmd_info.get('type') == 'json':
                        return 'json'
                return 'hex'
        if protocol in self._custom_templates:
            if command and command in self._custom_templates[protocol]:
                cmd_info = self._custom_templates[protocol][command]
                if isinstance(cmd_info, dict):
                    return cmd_info.get('type', 'hex')
            else:
                for cmd_name, cmd_info in self._custom_templates[protocol].items():
                    if isinstance(cmd_info, dict) and cmd_info.get('type') == 'json':
                        return 'json'
                return 'hex'
        return 'hex'

    def _save_current_fields(self):
        if not self._fields:
            return
        current_info = self._info_var.get()
        if '→' not in current_info:
            return
        parts = current_info.split('→')
        proto_name = parts[0].strip()
        cmd_name = parts[1].strip()
        if proto_name in self._custom_templates and cmd_name in self._custom_templates[proto_name]:
            self._custom_templates[proto_name][cmd_name]['fields'] = copy.deepcopy(self._fields)

    def _on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        item = selected[0]
        parent = self.tree.parent(item)
        if not parent:
            return

        proto_text = self.tree.item(parent, 'text').strip()
        protocol = proto_text.replace('📦 ', '').replace('📁 ', '')
        for pfx in ['[H] ', '[J] ']:
            if protocol.startswith(pfx):
                protocol = protocol[len(pfx):]
                break
        command = self.tree.item(item, 'text').strip()

        self._save_current_fields()

        cmd_info = None
        if protocol in PRESET_TEMPLATES:
            for n, info in PRESET_TEMPLATES[protocol].items():
                if n == command:
                    cmd_info = info
                    break
        if not cmd_info and protocol in self._custom_templates:
            for n, info in self._custom_templates[protocol].items():
                if n == command:
                    cmd_info = info
                    break

        if cmd_info:
            self._info_var.set(f'{protocol} → {command}')
            self._desc_var.set(cmd_info.get('desc', ''))

            proto_type = cmd_info.get('type', 'hex') if isinstance(cmd_info, dict) else 'hex'
            self._current_proto_type = proto_type

            if proto_type == 'json':
                self._proto_type_var.set('[JSON]')
                self._setup_json_columns()
                self._hex_shown = False
                if hasattr(self, '_json_btn_frame'):
                    self._json_btn_frame.pack(in_=self._json_btn_frame.master, side=tk.LEFT, padx=(4, 0))
            else:
                self._proto_type_var.set('[HEX]')
                self._setup_hex_columns()
                self._hex_shown = True
                if hasattr(self, '_json_btn_frame'):
                    self._json_btn_frame.pack_forget()

            self._fields = copy.deepcopy(cmd_info.get('fields', []))
            self._refresh_fields()
            self._refresh_data()

    def _refresh_fields(self):
        for item in self.treeview.get_children():
            self.treeview.delete(item)

        if self._current_proto_type == 'json':
            for i, f in enumerate(self._fields):
                key = f.get('key', '')
                ftype = f.get('type', 'string')
                required = '是' if f.get('required') else '否'
                default = str(f.get('default', '')) if f.get('default') is not None else ''
                enum_vals = f.get('enum', [])
                constraints = []
                if enum_vals:
                    constraints.append(f'enum:{len(enum_vals)}')
                if f.get('minimum') is not None:
                    constraints.append(f'min:{f["minimum"]}')
                if f.get('maximum') is not None:
                    constraints.append(f'max:{f["maximum"]}')
                if f.get('pattern'):
                    constraints.append('regex')
                enum_str = ', '.join(constraints) if constraints else ''
                desc = f.get('description', '')
                self.treeview.insert('', tk.END, iid=str(i),
                                    values=(key, ftype, required, default, enum_str, desc))
        else:
            computed = self._compute_auto_fields()
            for i, f in enumerate(self._fields):
                ft = f.get('field_type', '')
                if ft in ('长度', '校验'):
                    real = computed.get(i, '')
                    hex_display = f'(自动) {real}' if real else '(自动)'
                else:
                    hex_display = f.get('hex_value', '')
                self.treeview.insert('', tk.END, iid=str(i),
                                   values=(f.get('name', ''),
                                          hex_display,
                                          f.get('byte_count', 1),
                                          ft,
                                          f.get('description', '')))

    def _compute_auto_fields(self) -> dict:
        result = {}
        parts = []
        for f in self._fields:
            bc = f.get('byte_count', 1)
            ft = f.get('field_type', '')
            if ft in ('长度', '校验'):
                parts.append(b'\x00' * bc)
            else:
                try:
                    data = hex_str_to_bytes(f.get('hex_value', ''))
                    if len(data) < bc:
                        data = b'\x00' * (bc - len(data)) + data
                    elif len(data) > bc:
                        data = data[-bc:]
                    parts.append(data)
                except Exception:
                    parts.append(b'\x00' * bc)

        for i, f in enumerate(self._fields):
            if f.get('field_type') == '长度':
                try:
                    start = f.get('length_start', 0)
                    end = f.get('length_end', 0)
                    if start == 0 and end == 0:
                        total_len = 0
                        for j, f2 in enumerate(self._fields):
                            if j != i:
                                total_len += f2.get('byte_count', 0)
                    else:
                        start = max(0, start)
                        end = min(len(self._fields) - 1, end)
                        total_len = 0
                        for j in range(start, end + 1):
                            total_len += self._fields[j].get('byte_count', 0)
                    bc = f.get('byte_count', 1)
                    bo = f.get('length_byte_order', 'big')
                    b = total_len.to_bytes(bc, byteorder=bo)
                    parts[i] = b
                    result[i] = bytes_to_hex_str(b)
                except Exception:
                    pass

        for i, f in enumerate(self._fields):
            if f.get('field_type') == '校验':
                try:
                    algo = f.get('checksum_algorithm', 'CRC16/MODBUS')
                    bo = f.get('checksum_byte_order', 'big')
                    start = f.get('checksum_start', 0)
                    end = f.get('checksum_end', 0)
                    chk_data = b''
                    if start == 0 and end == 0:
                        for j, p in enumerate(parts):
                            if j != i:
                                chk_data += p
                    else:
                        start = max(0, start)
                        end = min(len(self._fields) - 1, end)
                        for j in range(start, end + 1):
                            if j != i:
                                chk_data += parts[j]
                    val, val_bytes = calc_checksum(chk_data, algo)
                    if bo == 'little':
                        val_bytes = val_bytes[::-1]
                    bc = f.get('byte_count', 1)
                    if len(val_bytes) < bc:
                        val_bytes = b'\x00' * (bc - len(val_bytes)) + val_bytes
                    elif len(val_bytes) > bc:
                        val_bytes = val_bytes[-bc:]
                    parts[i] = val_bytes
                    result[i] = bytes_to_hex_str(val_bytes)
                except Exception:
                    pass

        return result

    def _on_data_var_change(self, *args):
        text = self._data_var.get().strip()
        if hasattr(self, '_data_entry'):
            self._data_entry._tooltip_text = text if text else ''

    def _refresh_data(self):
        if self._current_proto_type == 'json':
            self._refresh_json_data()
        else:
            self._refresh_hex_data()

    def _refresh_json_data(self):
        data = {}
        for f in self._fields:
            key = f.get('key', '')
            if not key:
                continue
            default = f.get('default', '')
            data[key] = default
        if data:
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            self._data_var.set(json_str)
        else:
            self._data_var.set('')

    def _refresh_hex_data(self):
        computed = self._compute_auto_fields()
        parts = []
        for i, f in enumerate(self._fields):
            ft = f.get('field_type', '')
            if ft in ('长度', '校验'):
                real = computed.get(i, '')
                if real:
                    parts.append(real.replace(' ', ''))
                else:
                    parts.append('00' * f.get('byte_count', 1))
            else:
                parts.append(f.get('hex_value', ''))
        combined = ''.join(parts)
        if combined:
            data = ' '.join(combined[i:i+2] for i in range(0, len(combined), 2))
            self._data_var.set(data.upper())
        else:
            self._data_var.set('')

    def _json_format(self):
        raw = self._data_var.get().strip()
        if not raw:
            return
        try:
            data = json.loads(raw)
            self._data_var.set(json.dumps(data, ensure_ascii=False, indent=2))
        except json.JSONDecodeError as e:
            self._msgbox('格式化失败', f'无效的 JSON:\n{e}')

    def _json_compress(self):
        raw = self._data_var.get().strip()
        if not raw:
            return
        try:
            data = json.loads(raw)
            self._data_var.set(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
        except json.JSONDecodeError as e:
            self._msgbox('压缩失败', f'无效的 JSON:\n{e}')

    def _json_validate(self):
        raw = self._data_var.get().strip()
        if not raw:
            self._msgbox('验证', '请输入 JSON 数据')
            return
        try:
            json.loads(raw)
            self._msgbox('验证', '✅ JSON 格式正确')
        except json.JSONDecodeError as e:
            self._msgbox('验证失败', str(e), 'error')

    def _send_data(self):
        data_str = self._data_var.get().strip()
        if not data_str:
            self._msgbox('提示', '请先生成数据', 'warning')
            return
        if not self._on_send:
            self._msgbox('提示', '未设置发送回调', 'warning')
            return
        try:
            if self._current_proto_type == 'json':
                data = data_str.encode('utf-8')
            else:
                data = bytes.fromhex(data_str.replace(' ', ''))
            self._on_send(data)
            if self._log_panel:
                self._log_panel.log_info(f'[协议编辑器] 已发送: {data_str}')
        except Exception as e:
            self._msgbox('发送失败', str(e), 'error')

    def _copy_data(self):
        data_str = self._data_var.get().strip()
        if data_str:
            self.clipboard_clear()
            self.clipboard_append(data_str)

    def _check_command_selected(self) -> bool:
        if not self._fields and not self._undo_stack:
            selected = self.tree.selection()
            if not selected:
                self._msgbox('提示', '请先在左侧模板库中选择一个命令', 'warning')
                return False
            item = selected[0]
            parent = self.tree.parent(item)
            if not parent:
                self._msgbox('提示', '请先在左侧模板库中选择一个命令', 'warning')
                return False
        return True

    def _add_field(self):
        if not self._check_command_selected():
            return
        if self._current_proto_type == 'json':
            dlg = JsonFieldEditDialog(self.winfo_toplevel(), title='添加JSON字段')
            if dlg.result:
                self._push_undo()
                self._fields.append(dlg.result)
                self._refresh_fields()
                self._refresh_data()
        else:
            field_names = [f.get('name', '') for f in self._fields]
            dlg = FieldEditDialog(self.winfo_toplevel(), title='添加字段', field_names=field_names)
            if dlg.result:
                self._push_undo()
                self._fields.append(dlg.result)
                self._refresh_fields()
                self._refresh_data()

    def _edit_field(self):
        if not self._check_command_selected():
            return
        sel = self.treeview.selection()
        if not sel:
            self._msgbox('提示', '请先在字段列表中选择一个字段', "warning")
            return
        idx = int(sel[0])
        if self._current_proto_type == 'json':
            dlg = JsonFieldEditDialog(self.winfo_toplevel(), title='编辑JSON字段', field=self._fields[idx])
            if dlg.result:
                self._push_undo()
                self._fields[idx] = dlg.result
                self._refresh_fields()
                self._refresh_data()
        else:
            field_names = [f.get('name', '') for f in self._fields]
            dlg = FieldEditDialog(self.winfo_toplevel(), title='编辑字段', field=self._fields[idx], field_names=field_names)
            if dlg.result:
                self._push_undo()
                self._fields[idx] = dlg.result
                self._refresh_fields()
                self._refresh_data()

    def _delete_field(self):
        if not self._check_command_selected():
            return
        sel = self.treeview.selection()
        if not sel:
            self._msgbox('提示', '请先在字段列表中选择一个字段', "warning")
            return
        idx = int(sel[0])
        self._push_undo()
        self._fields.pop(idx)
        self._refresh_fields()
        self._refresh_data()

    def _move_up(self):
        if not self._check_command_selected():
            return
        sel = self.treeview.selection()
        if not sel:
            self._msgbox('提示', '请先在字段列表中选择一个字段', "warning")
            return
        idx = int(sel[0])
        if idx < 1:
            return
        self._push_undo()
        self._fields[idx], self._fields[idx-1] = self._fields[idx-1], self._fields[idx]
        self._refresh_fields()
        self.treeview.selection_set(str(idx-1))

    def _move_down(self):
        if not self._check_command_selected():
            return
        sel = self.treeview.selection()
        if not sel:
            self._msgbox('提示', '请先在字段列表中选择一个字段', "warning")
            return
        idx = int(sel[0])
        if idx >= len(self._fields) - 1:
            return
        self._push_undo()
        self._fields[idx], self._fields[idx+1] = self._fields[idx+1], self._fields[idx]
        self._refresh_fields()
        self.treeview.selection_set(str(idx+1))

    def _undo(self):
        if not self._undo_stack:
            self._msgbox('提示', '没有可撤销的操作', "info")
            return
        self._fields = self._undo_stack.pop()
        self._refresh_fields()
        self._refresh_data()

    def _push_undo(self):
        self._undo_stack.append(copy.deepcopy(self._fields))
        if len(self._undo_stack) > 20:
            self._undo_stack.pop(0)

    def _on_field_double_click(self, event):
        self._edit_field()

    def _save_as_template(self):
        if not self._fields:
            self._msgbox('提示', '没有字段可保存', 'warning')
            return

        dialog = tk.Toplevel(self)
        dialog.title('保存为模板')
        dialog.transient(self)
        dialog.grab_set()
        self._center_toplevel(dialog, 400, 250)

        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text='协议名称:').pack(anchor=tk.W)
        proto_var = tk.StringVar(value='自定义')
        ttk.Combobox(frame, textvariable=proto_var,
                     values=['自定义'] + [k for k in self._custom_templates.keys()],
                     state='normal', width=25).pack(fill=tk.X, pady=(4, 8))

        ttk.Label(frame, text='命令名称:').pack(anchor=tk.W)
        name_var = tk.StringVar(value='新命令')
        ttk.Entry(frame, textvariable=name_var, width=25).pack(fill=tk.X, pady=(4, 8))

        ttk.Label(frame, text='说明:').pack(anchor=tk.W)
        desc_var = tk.StringVar(value='')
        ttk.Entry(frame, textvariable=desc_var, width=25).pack(fill=tk.X, pady=(0, 12))

        proto_type = self._current_proto_type

        def _confirm():
            proto = proto_var.get().strip()
            name = name_var.get().strip()
            if not proto or not name:
                self._msgbox('提示', '请输入协议和命令名称', "warning")
                return
            if proto not in self._custom_templates:
                self._custom_templates[proto] = {}
            record = {
                'fields': copy.deepcopy(self._fields),
                'desc': desc_var.get().strip(),
            }
            if proto_type == 'json':
                record['type'] = 'json'
                record['example'] = self._data_var.get().strip()
            self._custom_templates[proto][name] = record
            self._refresh_custom_tree()
            if self._log_panel:
                self._log_panel.log_info(f'[协议编辑器] 已保存模板: {proto} → {name}')
            dialog.destroy()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text='确定', command=_confirm, width=8).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btn_frame, text='取消', command=dialog.destroy, width=8).pack(side=tk.RIGHT)

    def _new_protocol(self):
        dialog = tk.Toplevel(self)
        dialog.title('新建协议')
        dialog.transient(self)
        dialog.grab_set()
        self._center_toplevel(dialog, 350, 200)

        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text='协议名称:').pack(anchor=tk.W)
        name_var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=name_var, width=25)
        entry.pack(fill=tk.X, pady=(4, 8))
        entry.focus_set()

        ttk.Label(frame, text='协议类型:').pack(anchor=tk.W)
        type_var = tk.StringVar(value='hex')
        type_frame = ttk.Frame(frame)
        type_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Radiobutton(type_frame, text='HEX 协议', variable=type_var,
                        value='hex').pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(type_frame, text='JSON 协议', variable=type_var,
                        value='json').pack(side=tk.LEFT)

        def _confirm():
            name = name_var.get().strip()
            if not name:
                self._msgbox('提示', '请输入协议名称', "warning")
                return
            if name in self._custom_templates:
                self._msgbox('提示', '协议名称已存在', "warning")
                return
            proto_type = type_var.get()
            self._custom_templates[name] = {'_proto_type': proto_type}
            self._refresh_custom_tree()
            if self._log_panel:
                self._log_panel.log_info(f'[协议编辑器] 新建协议: {name} (type={proto_type})')
            dialog.destroy()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text='确定', command=_confirm, width=8).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btn_frame, text='取消', command=dialog.destroy, width=8).pack(side=tk.RIGHT)

    def _new_command(self):
        if not self._custom_templates:
            self._msgbox('提示', '请先新建协议', "warning")
            return

        self._save_current_fields()

        protocols = list(self._custom_templates.keys())
        if not protocols:
            self._msgbox('提示', '请先新建协议', "warning")
            return

        default_proto = protocols[0]
        selected = self.tree.selection()
        if selected:
            item = selected[0]
            parent = self.tree.parent(item)
            if not parent:
                proto_text = self.tree.item(item, 'text').strip()
            else:
                proto_text = self.tree.item(parent, 'text').strip()
            raw = proto_text.replace('📦 ', '').replace('📁 ', '')
            for pfx in ['[H] ', '[J] ']:
                if raw.startswith(pfx):
                    raw = raw[len(pfx):]
                    break
            if raw in self._custom_templates:
                default_proto = raw

        dialog = tk.Toplevel(self)
        dialog.title('新建命令')
        dialog.transient(self)
        dialog.grab_set()
        self._center_toplevel(dialog, 400, 250)

        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text='所属协议:').pack(anchor=tk.W)
        proto_var = tk.StringVar(value=default_proto)
        ttk.Combobox(frame, textvariable=proto_var, values=protocols,
                     state='readonly', width=20).pack(fill=tk.X, pady=(4, 8))

        ttk.Label(frame, text='命令名称:').pack(anchor=tk.W)
        name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=name_var, width=25).pack(fill=tk.X, pady=(4, 8))

        ttk.Label(frame, text='说明:').pack(anchor=tk.W)
        desc_var = tk.StringVar()
        ttk.Entry(frame, textvariable=desc_var, width=25).pack(fill=tk.X, pady=(0, 12))

        def _confirm():
            proto = proto_var.get()
            name = name_var.get().strip()
            if not name:
                self._msgbox('提示', '请输入命令名称', "warning")
                return
            if proto not in self._custom_templates:
                self._custom_templates[proto] = {}
            # 从协议标记或已有命令推断协议类型
            proto_data = self._custom_templates[proto]
            proto_type = proto_data.get('_proto_type', 'hex')
            if proto_type == 'hex':
                for cmd_info in proto_data.values():
                    if isinstance(cmd_info, dict) and cmd_info.get('type') == 'json':
                        proto_type = 'json'
                        break
            record = {
                'fields': [],
                'desc': desc_var.get().strip(),
            }
            if proto_type == 'json':
                record['type'] = 'json'
            self._custom_templates[proto][name] = record
            self._refresh_custom_tree()
            if self._log_panel:
                self._log_panel.log_info(f'[协议编辑器] 新建命令: {proto} → {name}')
            dialog.destroy()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text='确定', command=_confirm, width=8).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btn_frame, text='取消', command=dialog.destroy, width=8).pack(side=tk.RIGHT)

    def _delete_item(self):
        selected = self.tree.selection()
        if not selected:
            return
        item = selected[0]
        parent = self.tree.parent(item)
        text = self.tree.item(item, 'text').strip()

        if not parent:
            protocol = text.replace('📦 ', '').replace('📁 ', '')
            for pfx in ['[H] ', '[J] ']:
                if protocol.startswith(pfx):
                    protocol = protocol[len(pfx):]
                    break
            if protocol in PRESET_TEMPLATES:
                self._msgbox('提示', '预设模板不能删除', "warning")
                return
            if protocol in self._custom_templates:
                if self._askyesno('确认', f'确定要删除协议 "{protocol}" 吗？'):
                    del self._custom_templates[protocol]
                    self.tree.delete(item)
        else:
            proto_text = self.tree.item(parent, 'text').strip()
            protocol = proto_text.replace('📦 ', '').replace('📁 ', '')
            for pfx in ['[H] ', '[J] ']:
                if protocol.startswith(pfx):
                    protocol = protocol[len(pfx):]
                    break
            command = text
            if protocol in PRESET_TEMPLATES:
                self._msgbox('提示', '预设模板不能删除', "warning")
                return
            if protocol in self._custom_templates and command in self._custom_templates[protocol]:
                if self._askyesno('确认', f'确定要删除命令 "{command}" 吗？'):
                    del self._custom_templates[protocol][command]
                    self.tree.delete(item)

    def _import_templates(self):
        filepath = filedialog.askopenfilename(
            title='导入模板',
            filetypes=[('JSON文件', '*.json'), ('所有文件', '*.*')]
        )
        if not filepath:
            return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                for protocol, commands in data.items():
                    if protocol not in self._custom_templates:
                        self._custom_templates[protocol] = {}
                    self._custom_templates[protocol].update(commands)
                self._refresh_custom_tree()
                self._msgbox('成功', f'已导入协议', 'info')
        except Exception as e:
            self._msgbox('导入失败', str(e), 'error')

    def _export_templates(self):
        if not self._custom_templates:
            self._msgbox('提示', '没有自定义模板可导出', "warning")
            return

        default_name = ''
        selected = self.tree.selection()
        if selected:
            item = selected[0]
            parent = self.tree.parent(item)
            if parent:
                proto_text = self.tree.item(parent, 'text').strip()
                default_name = proto_text.replace('📦 ', '').replace('📁 ', '')
            else:
                proto_text = self.tree.item(item, 'text').strip()
                default_name = proto_text.replace('📦 ', '').replace('📁 ', '')
            for pfx in ['[H] ', '[J] ']:
                if default_name.startswith(pfx):
                    default_name = default_name[len(pfx):]
                    break

        if not default_name:
            default_name = '协议模板'

        filepath = filedialog.asksaveasfilename(
            title='导出模板',
            defaultextension='.json',
            filetypes=[('JSON文件', '*.json'), ('所有文件', '*.*')],
            initialfile=f'{default_name}.json'
        )
        if not filepath:
            return
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self._custom_templates, f, ensure_ascii=False, indent=2)
            self._msgbox('成功', f'已导出到: {filepath}', "info")
        except Exception as e:
            self._msgbox('导出失败', str(e), 'error')

    def _load_to_parser(self, target=None):
        if not self._fields:
            self._msgbox('提示', '没有字段可加载', "warning")
            return
        data_str = self._data_var.get().strip()
        proto_name = ''
        cmd_name = ''
        selected = self.tree.selection()
        if selected:
            item = selected[0]
            parent = self.tree.parent(item)
            if parent:
                proto_text = self.tree.item(parent, 'text').strip()
                proto_name = proto_text.replace('📦 ', '').replace('📁 ', '')
                for pfx in ['[H] ', '[J] ']:
                    if proto_name.startswith(pfx):
                        proto_name = proto_name[len(pfx):]
                        break
                cmd_name = self.tree.item(item, 'text').strip()

        parse_panel = target or self._parse_panel
        if parse_panel:
            # JSON 类型：直接传递 example 字符串
            if self._current_proto_type == 'json':
                parse_panel.add_json_protocol(
                    self._fields, data_str, proto_name, cmd_name
                )
            else:
                parse_panel.add_protocol(self._fields, proto_name, cmd_name)
                if data_str:
                    parse_panel.set_input_data(data_str)
                    parse_panel.do_parse()
            if self._log_panel:
                self._log_panel.log_info(f'[协议编辑器] 已加载 {len(self._fields)} 个字段到解析面板')
        else:
            if data_str:
                self.clipboard_clear()
                self.clipboard_append(data_str)
                if self._log_panel:
                    self._log_panel.log_info('[协议编辑器] 已复制数据到剪贴板')
            else:
                self._msgbox('提示', '请先生成数据', "info")

    def get_current_fields(self) -> list:
        return self._fields

    def get_current_selection(self) -> tuple:
        proto_name = ''
        cmd_name = ''
        selected = self.tree.selection()
        if selected:
            item = selected[0]
            parent = self.tree.parent(item)
            if parent:
                proto_text = self.tree.item(parent, 'text').strip()
                proto_name = proto_text.replace('📦 ', '').replace('📁 ', '')
                for pfx in ['[H] ', '[J] ']:
                    if proto_name.startswith(pfx):
                        proto_name = proto_name[len(pfx):]
                        break
                cmd_name = self.tree.item(item, 'text').strip()
        return proto_name, cmd_name

    def get_settings(self) -> dict:
        return {
            'custom_templates': self._custom_templates,
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        custom = settings.get('custom_templates', {})
        if custom:
            self._custom_templates = custom
            self._refresh_custom_tree()
