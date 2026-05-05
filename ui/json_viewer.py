"""JSON 查看器 - 加载示例、格式化、树形展示"""

import json
import tkinter as tk
from tkinter import ttk, messagebox
from protocols.json_examples import JSON_TEMPLATES


class JsonViewer(ttk.LabelFrame):
    """JSON 查看器 - 加载示例、格式化、树形展示"""

    def __init__(self, parent, log_panel=None):
        super().__init__(parent, text=' JSON 查看器 ', padding=6)
        self._log_panel = log_panel
        self._last_input = ''
        self._build_ui()

    def _build_ui(self):
        # ===== 工具栏 =====
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(toolbar, text='协议示例:').pack(side=tk.LEFT)
        self._template_var = tk.StringVar(value='')
        proto_names = list(JSON_TEMPLATES.keys())
        self._proto_cb = ttk.Combobox(toolbar, textvariable=self._template_var,
                                       values=proto_names, state='readonly', width=14)
        self._proto_cb.pack(side=tk.LEFT, padx=(4, 2))
        self._proto_cb.bind('<<ComboboxSelected>>', self._on_proto_select)

        self._cmd_var = tk.StringVar(value='')
        self._cmd_cb = ttk.Combobox(toolbar, textvariable=self._cmd_var,
                                     state='readonly', width=18)
        self._cmd_cb.pack(side=tk.LEFT, padx=(2, 4))
        self._cmd_cb.bind('<<ComboboxSelected>>', self._on_cmd_select)

        ttk.Button(toolbar, text='📋 加载', command=self._load_template, width=6).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        ttk.Button(toolbar, text='格式化', command=self._format_json, width=7).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text='压缩', command=self._compress_json, width=5).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text='验证', command=self._validate_json, width=5).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text='🗑 清除', command=self._clear_all, width=6).pack(side=tk.LEFT, padx=1)

        # ===== 输入区 =====
        input_frame = ttk.LabelFrame(self, text=' JSON 数据 ', padding=4)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

        self._input_text = tk.Text(input_frame, wrap=tk.NONE, height=6,
                                   font=('Courier New', 11))
        input_scroll_v = ttk.Scrollbar(input_frame, orient=tk.VERTICAL, command=self._input_text.yview)
        input_scroll_h = ttk.Scrollbar(input_frame, orient=tk.HORIZONTAL, command=self._input_text.xview)
        self._input_text.configure(yscrollcommand=input_scroll_v.set, xscrollcommand=input_scroll_h.set)

        self._input_text.grid(row=0, column=0, sticky='nsew')
        input_scroll_v.grid(row=0, column=1, sticky='ns')
        input_scroll_h.grid(row=1, column=0, sticky='ew')
        input_frame.rowconfigure(0, weight=1)
        input_frame.columnconfigure(0, weight=1)

        self._input_text.bind('<KeyRelease>', self._on_input_change)

        # ===== 结果树 =====
        result_frame = ttk.LabelFrame(self, text=' 解析结果 ', padding=4)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        self._tree = ttk.Treeview(result_frame, columns=('key', 'value', 'type'),
                                  show='tree headings', selectmode='browse', height=10)
        self._tree.heading('#0', text='', anchor=tk.W)
        self._tree.heading('key', text='键', anchor=tk.W)
        self._tree.heading('value', text='值', anchor=tk.W)
        self._tree.heading('type', text='类型', anchor=tk.W)

        self._tree.column('#0', width=30, minwidth=20, stretch=False)
        self._tree.column('key', width=180, minwidth=80, anchor=tk.W)
        self._tree.column('value', width=220, minwidth=80, anchor=tk.W)
        self._tree.column('type', width=80, minwidth=50, anchor=tk.CENTER, stretch=False)

        tv_scroll = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self._tree.yview)
        th_scroll = ttk.Scrollbar(result_frame, orient=tk.HORIZONTAL, command=self._tree.xview)
        self._tree.configure(yscrollcommand=tv_scroll.set, xscrollcommand=th_scroll.set)

        self._tree.grid(row=0, column=0, sticky='nsew')
        tv_scroll.grid(row=0, column=1, sticky='ns')
        th_scroll.grid(row=1, column=0, sticky='ew')
        result_frame.rowconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)

        # 标签颜色
        self._tree.tag_configure('str', foreground='#6a9955')
        self._tree.tag_configure('num', foreground='#4fc1ff')
        self._tree.tag_configure('bool', foreground='#ce9178')
        self._tree.tag_configure('null', foreground='#808080')
        self._tree.tag_configure('container', font=('', 9, 'bold'))

        # 状态栏
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, pady=(4, 0))

        self._status_var = tk.StringVar(value='就绪')
        ttk.Label(status_frame, textvariable=self._status_var,
                 font=('', 9, 'bold')).pack(side=tk.LEFT)

        self._field_count_var = tk.StringVar(value='')
        ttk.Label(status_frame, textvariable=self._field_count_var,
                 foreground='blue').pack(side=tk.RIGHT, padx=(0, 8))

        self._char_count_var = tk.StringVar(value='')
        ttk.Label(status_frame, textvariable=self._char_count_var,
                 foreground='gray').pack(side=tk.RIGHT, padx=(0, 8))

    # ============================================================
    # 模板选择
    # ============================================================

    def _on_proto_select(self, event=None):
        proto = self._template_var.get()
        cmds = JSON_TEMPLATES.get(proto, {})
        self._cmd_cb['values'] = [f'{k} - {v["desc"]}' for k, v in cmds.items()]
        self._cmd_cb.set('')

    def _on_cmd_select(self, event=None):
        self._load_template()

    def _load_template(self):
        proto = self._template_var.get()
        cmd_text = self._cmd_var.get()
        if not proto or not cmd_text:
            return
        cmd_name = cmd_text.split(' - ')[0]
        cmd_info = JSON_TEMPLATES.get(proto, {}).get(cmd_name)
        if cmd_info and 'json' in cmd_info:
            self._input_text.delete('1.0', tk.END)
            self._input_text.insert('1.0', cmd_info['json'].strip())
            self._parse_input()

    # ============================================================
    # JSON 操作
    # ============================================================

    def _format_json(self):
        raw = self._input_text.get('1.0', tk.END).strip()
        if not raw:
            return
        try:
            data = json.loads(raw)
            formatted = json.dumps(data, ensure_ascii=False, indent=2)
            self._input_text.delete('1.0', tk.END)
            self._input_text.insert('1.0', formatted)
        except json.JSONDecodeError as e:
            messagebox.showwarning('格式化失败', f'无效的 JSON:\n{e}')

    def _compress_json(self):
        raw = self._input_text.get('1.0', tk.END).strip()
        if not raw:
            return
        try:
            data = json.loads(raw)
            compressed = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            self._input_text.delete('1.0', tk.END)
            self._input_text.insert('1.0', compressed)
        except json.JSONDecodeError as e:
            messagebox.showwarning('压缩失败', f'无效的 JSON:\n{e}')

    def _validate_json(self):
        raw = self._input_text.get('1.0', tk.END).strip()
        if not raw:
            messagebox.showinfo('验证', '请输入 JSON 数据')
            return
        try:
            json.loads(raw)
            messagebox.showinfo('验证', '✅ JSON 格式正确')
        except json.JSONDecodeError as e:
            messagebox.showerror('验证失败', str(e))

    def _clear_all(self):
        self._input_text.delete('1.0', tk.END)
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._status_var.set('就绪')
        self._field_count_var.set('')
        self._char_count_var.set('')

    def _on_input_change(self, event=None):
        self._parse_input()

    def _parse_input(self):
        raw = self._input_text.get('1.0', tk.END).strip()
        if not raw:
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self._status_var.set('❌ JSON 格式错误')
            self._status_label.configure(foreground='red')
            return

        for item in self._tree.get_children():
            self._tree.delete(item)

        self._status_var.set('✅ JSON 格式正确')
        field_count = [0]

        self._tree.insert('', tk.END, iid='root', text='', open=True,
                          values=('{...}', '', ''), tags=('container',))
        self._build_json_tree('root', data, field_count)

        raw_len = len(raw)
        self._char_count_var.set(f'字符数: {raw_len}')
        self._field_count_var.set(f'字段数: {field_count[0]}')

    def _build_json_tree(self, parent, data, field_count):
        if isinstance(data, dict):
            for key, value in data.items():
                iid = f'{parent}_{key}'
                field_count[0] += 1
                if isinstance(value, (dict, list)):
                    type_str = 'object' if isinstance(value, dict) else f'array[{len(value)}]'
                    self._tree.insert(parent, tk.END, iid=iid, text='',
                                      open=False,
                                      values=(key, '', type_str),
                                      tags=('container',))
                    self._build_json_tree(iid, value, field_count)
                else:
                    val_str, typ = self._format_value(value)
                    self._tree.insert(parent, tk.END, iid=iid, text='',
                                      values=(key, val_str, typ), tags=(typ,))
        elif isinstance(data, list):
            for idx, value in enumerate(data):
                iid = f'{parent}_{idx}'
                field_count[0] += 1
                key = f'[{idx}]'
                if isinstance(value, (dict, list)):
                    type_str = 'object' if isinstance(value, dict) else f'array[{len(value)}]'
                    self._tree.insert(parent, tk.END, iid=iid, text='',
                                      open=False,
                                      values=(key, '', type_str),
                                      tags=('container',))
                    self._build_json_tree(iid, value, field_count)
                else:
                    val_str, typ = self._format_value(value)
                    self._tree.insert(parent, tk.END, iid=iid, text='',
                                      values=(key, val_str, typ), tags=(typ,))

    def _format_value(self, value):
        if isinstance(value, bool):
            return str(value).lower(), 'bool'
        if isinstance(value, int):
            return str(value), 'num'
        if isinstance(value, float):
            if value == int(value):
                return str(int(value)), 'num'
            return f'{value:.6f}', 'num'
        if value is None:
            return 'null', 'null'
        return str(value), 'str'

    # ============================================================
    # 保存/恢复
    # ============================================================

    def get_settings(self) -> dict:
        return {
            'last_input': self._input_text.get('1.0', tk.END).strip(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        last = settings.get('last_input', '')
        if last:
            self._input_text.delete('1.0', tk.END)
            self._input_text.insert('1.0', last)
            self._parse_input()
