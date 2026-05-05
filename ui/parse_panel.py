"""协议解析面板 - 支持多协议加载 + JSON 自动识别解析"""

import copy
import json
import re
import tkinter as tk
from tkinter import ttk, messagebox
from utils.hex_utils import hex_str_to_bytes, bytes_to_hex_str
from packet.checksum import calc_checksum



class ProtocolEntry:
    def __init__(self, fields, protocol_name='', command_name=''):
        self.fields = copy.deepcopy(fields)
        self.protocol_name = protocol_name
        self.command_name = command_name
        self.enabled = True
        self.proto_type = 'hex'


class JsonProtocolEntry:
    def __init__(self, fields, example='', protocol_name='', command_name=''):
        self.fields = copy.deepcopy(fields)
        self.example = example
        self.protocol_name = protocol_name
        self.command_name = command_name
        self.enabled = True
        self.proto_type = 'json'


class ParsePanel(ttk.LabelFrame):
    """协议解析面板 - 支持多协议加载 + JSON 自动识别解析"""

    def __init__(self, parent, on_send=None, log_panel=None):
        super().__init__(parent, text=' 协议解析结果 ', padding=6)
        self._on_send = on_send
        self._log_panel = log_panel
        self._protocols: list[ProtocolEntry] = []
        self._json_protocols: list[JsonProtocolEntry] = []
        self._build_ui()

    def _build_ui(self):
        self._build_top_bar()
        self._build_input_area()
        self._build_result_area()
        self._build_status_bar()

    def _build_top_bar(self):
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, pady=(0, 4))

        proto_frame = ttk.LabelFrame(top_frame, text=' 已加载协议 ', padding=4)
        proto_frame.pack(fill=tk.X, expand=True)

        right_col = ttk.Frame(proto_frame)
        right_col.pack(side=tk.RIGHT, padx=(4, 0), fill=tk.Y)

        btn_row = ttk.Frame(right_col)
        btn_row.pack(side=tk.TOP, anchor=tk.W)
        self._add_proto_btn = ttk.Button(btn_row, text='＋', width=3, command=self._on_add_protocol)
        self._add_proto_btn.pack(side=tk.LEFT)
        self._remove_proto_btn = ttk.Button(btn_row, text='－', width=3, command=self._on_remove_protocol)
        self._remove_proto_btn.pack(side=tk.LEFT)

        self._auto_parse_var = tk.BooleanVar(value=False)
        self._auto_parse_cb = ttk.Checkbutton(
            right_col, text='⚡自动解析', variable=self._auto_parse_var,
            command=self._on_auto_parse_toggle)
        self._auto_parse_cb.pack(side=tk.TOP, anchor=tk.W, pady=(6, 0))

        self._proto_listbox = tk.Listbox(proto_frame, height=3, selectmode=tk.SINGLE)
        proto_scroll = ttk.Scrollbar(proto_frame, orient=tk.VERTICAL, command=self._proto_listbox.yview)
        self._proto_listbox.configure(yscrollcommand=proto_scroll.set)
        self._proto_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        proto_scroll.pack(side=tk.RIGHT, fill=tk.Y, before=self._proto_listbox)
        self._proto_listbox.bind('<<ListboxSelect>>', self._on_proto_select)

    def _build_input_area(self):
        input_frame = ttk.LabelFrame(self, text=' 输入待解析数据 ', padding=4)
        input_frame.pack(fill=tk.X, pady=(0, 4))

        input_row = ttk.Frame(input_frame)
        input_row.pack(fill=tk.X)

        self._input_var = tk.StringVar()
        self._input_entry = ttk.Entry(input_row, textvariable=self._input_var,
                                      font=('Courier New', 11))
        self._input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self._parse_btn = ttk.Button(input_row, text='🔍 解析', command=self._do_parse, width=8)
        self._parse_btn.pack(side=tk.LEFT, padx=2)

        self._load_btn = ttk.Button(input_row, text='📋 加载', command=self._do_load_fields, width=8)
        self._load_btn.pack(side=tk.LEFT, padx=2)

        self._clear_btn = ttk.Button(input_row, text='🗑 清除', command=self._clear_results, width=8)
        self._clear_btn.pack(side=tk.LEFT, padx=2)

        self._input_entry.bind('<Return>', lambda e: self._do_parse())
        self._input_entry.bind('<KeyRelease>', self._on_input_change)
        self._input_var.trace_add('write', self._on_input_var_change)

    def _build_result_area(self):
        result_frame = ttk.LabelFrame(self, text=' 解析结果 ', padding=4)
        result_frame.pack(fill=tk.BOTH, expand=True)

        self._result_notebook = ttk.Notebook(result_frame)
        self._result_notebook.pack(fill=tk.BOTH, expand=True)

        # --- HEX 结果表格 ---
        hex_frame = ttk.Frame(self._result_notebook)
        self._result_notebook.add(hex_frame, text='  HEX  ')

        columns = ('proto', 'index', 'field', 'expected', 'actual', 'status', 'desc')
        self._result_tree = ttk.Treeview(hex_frame, columns=columns,
                                         show='headings', selectmode='browse', height=10)
        self._result_tree.heading('proto', text='协议')
        self._result_tree.heading('index', text='序号')
        self._result_tree.heading('field', text='字段名')
        self._result_tree.heading('expected', text='期望值')
        self._result_tree.heading('actual', text='实际值')
        self._result_tree.heading('status', text='比对结果')
        self._result_tree.heading('desc', text='含义')

        self._result_tree.column('proto', width=80, minwidth=60, anchor=tk.W, stretch=False)
        self._result_tree.column('index', width=40, minwidth=30, anchor=tk.CENTER, stretch=False)
        self._result_tree.column('field', width=100, minwidth=60, anchor=tk.W, stretch=False)
        self._result_tree.column('expected', width=110, minwidth=60, anchor=tk.W, stretch=False)
        self._result_tree.column('actual', width=110, minwidth=60, anchor=tk.W, stretch=False)
        self._result_tree.column('status', width=90, minwidth=60, anchor=tk.CENTER, stretch=False)
        self._result_tree.column('desc', width=180, minwidth=80, anchor=tk.W, stretch=False)

        v_scroll = ttk.Scrollbar(hex_frame, orient=tk.VERTICAL, command=self._result_tree.yview)
        h_scroll = ttk.Scrollbar(hex_frame, orient=tk.HORIZONTAL, command=self._result_tree.xview)
        self._result_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self._result_tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        hex_frame.rowconfigure(0, weight=1)
        hex_frame.columnconfigure(0, weight=1)

        # --- JSON 结果表格 ---
        json_frame = ttk.Frame(self._result_notebook)
        self._result_notebook.add(json_frame, text='  JSON  ')

        jcolumns = ('key', 'jtype', 'constraints', 'actual', 'status')
        self._json_result_tree = ttk.Treeview(json_frame, columns=jcolumns,
                                               show='headings', selectmode='browse', height=10)
        self._json_result_tree.heading('key', text='键路径')
        self._json_result_tree.heading('jtype', text='期望类型')
        self._json_result_tree.heading('constraints', text='约束')
        self._json_result_tree.heading('actual', text='实际值')
        self._json_result_tree.heading('status', text='比对结果')

        self._json_result_tree.column('key', width=160, minwidth=100, anchor=tk.W)
        self._json_result_tree.column('jtype', width=80, minwidth=60, anchor=tk.CENTER)
        self._json_result_tree.column('constraints', width=180, minwidth=100, anchor=tk.W)
        self._json_result_tree.column('actual', width=180, minwidth=100, anchor=tk.W)
        self._json_result_tree.column('status', width=120, minwidth=80, anchor=tk.CENTER)

        jv_scroll = ttk.Scrollbar(json_frame, orient=tk.VERTICAL, command=self._json_result_tree.yview)
        jh_scroll = ttk.Scrollbar(json_frame, orient=tk.HORIZONTAL, command=self._json_result_tree.xview)
        self._json_result_tree.configure(yscrollcommand=jv_scroll.set, xscrollcommand=jh_scroll.set)

        self._json_result_tree.grid(row=0, column=0, sticky='nsew')
        jv_scroll.grid(row=0, column=1, sticky='ns')
        jh_scroll.grid(row=1, column=0, sticky='ew')
        json_frame.rowconfigure(0, weight=1)
        json_frame.columnconfigure(0, weight=1)

        self._json_result_tree.tag_configure('match', foreground='green')
        self._json_result_tree.tag_configure('mismatch', foreground='red')
        self._json_result_tree.tag_configure('missing', foreground='orange')
        self._json_result_tree.tag_configure('undefined', foreground='gray')

    def _build_status_bar(self):
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, pady=(4, 0))

        self._status_var = tk.StringVar(value='就绪')
        self._status_label = ttk.Label(bottom_frame, textvariable=self._status_var,
                                       font=('', 9, 'bold'))
        self._status_label.pack(side=tk.LEFT)

        self._match_count_var = tk.StringVar(value='匹配: 0/0')
        ttk.Label(bottom_frame, textvariable=self._match_count_var,
                 foreground='blue').pack(side=tk.RIGHT, padx=(0, 8))

        self._total_len_var = tk.StringVar(value='数据长度: 0 字节')
        ttk.Label(bottom_frame, textvariable=self._total_len_var,
                 foreground='gray').pack(side=tk.RIGHT, padx=(0, 8))

    # ============================================================
    # 协议管理
    # ============================================================

    def add_protocol(self, fields, protocol_name='', command_name=''):
        entry = ProtocolEntry(fields, protocol_name, command_name)
        self._protocols.append(entry)
        self._refresh_proto_list()
        if self._log_panel:
            display = f'{protocol_name} → {command_name}' if protocol_name and command_name else f'{len(fields)} 个字段'
            self._log_panel.log_info(f'[协议解析] 已加载协议: {display}')

    def add_json_protocol(self, fields, example='', protocol_name='', command_name=''):
        entry = JsonProtocolEntry(fields, example, protocol_name, command_name)
        self._json_protocols.append(entry)
        self._refresh_proto_list()
        if self._log_panel:
            display = f'{protocol_name} → {command_name}' if protocol_name and command_name else f'{len(fields)} 个字段'
            self._log_panel.log_info(f'[协议解析] 已加载JSON协议: {display}')

    def remove_protocol(self, index: int):
        if 0 <= index < len(self._protocols):
            entry = self._protocols.pop(index)
            self._refresh_proto_list()
            if self._log_panel:
                display = f'{entry.protocol_name} → {entry.command_name}' if entry.protocol_name and entry.command_name else '未命名'
                self._log_panel.log_info(f'[协议解析] 已移除协议: {display}')
            return
        json_start = len(self._protocols)
        if 0 <= index - json_start < len(self._json_protocols):
            entry = self._json_protocols.pop(index - json_start)
            self._refresh_proto_list()
            if self._log_panel:
                display = f'{entry.protocol_name} → {entry.command_name}' if entry.protocol_name and entry.command_name else '未命名'
                self._log_panel.log_info(f'[协议解析] 已移除JSON协议: {display}')

    def _refresh_proto_list(self):
        self._proto_listbox.delete(0, tk.END)
        for entry in self._protocols:
            display = self._get_entry_display(entry, '[H] ')
            prefix = '✅ ' if entry.enabled else '☐ '
            self._proto_listbox.insert(tk.END, f'{prefix}{display}')
        for entry in self._json_protocols:
            display = self._get_entry_display(entry, '[J] ')
            prefix = '✅ ' if entry.enabled else '☐ '
            self._proto_listbox.insert(tk.END, f'{prefix}{display}')

    def _get_entry_display(self, entry, pfx=''):
        if entry.protocol_name and entry.command_name:
            return f'{pfx}{entry.protocol_name} → {entry.command_name}'
        elif entry.protocol_name:
            return f'{pfx}{entry.protocol_name}'
        elif entry.fields:
            return f'{pfx}{len(entry.fields)} 个字段'
        return f'{pfx}(空)'

    def _on_proto_select(self, event=None):
        pass

    def _on_add_protocol(self):
        parent = self.master
        from ui.tools_notebook import ToolsContainer
        editor = None
        while parent is not None:
            if isinstance(parent, ToolsContainer):
                try:
                    editor = parent.protocol_editor
                except AttributeError:
                    break
                break
            parent = parent.master
        if not editor or not hasattr(editor, '_custom_templates'):
            messagebox.showwarning('提示', '请先在协议编辑器中打开一个模板', parent=self.winfo_toplevel())
            return
        self._show_proto_selector(editor)

    def _show_proto_selector(self, editor):
        from protocols import PRESET_TEMPLATES
        all_protos = {}
        for proto, cmds in PRESET_TEMPLATES.items():
            all_protos[proto] = {k: v for k, v in cmds.items()}
        for proto, cmds in editor._custom_templates.items():
            if proto not in all_protos:
                all_protos[proto] = {}
            all_protos[proto].update(cmds)

        dialog = tk.Toplevel(self.winfo_toplevel())
        dialog.title('选择要加载的协议')
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.withdraw()
        dialog.update_idletasks()
        pw = self.winfo_toplevel().winfo_width()
        ph = self.winfo_toplevel().winfo_height()
        px = self.winfo_toplevel().winfo_rootx()
        py = self.winfo_toplevel().winfo_rooty()
        w, h = 450, 400
        dialog.geometry(f'{w}x{h}+{px + (pw - w) // 2}+{py + (ph - h) // 2}')
        dialog.deiconify()

        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        def _on_canvas_cfg(event):
            canvas.itemconfig(canvas_win, width=event.width)
        scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas_win = canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.bind('<Configure>', _on_canvas_cfg)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _on_wheel(event):
            canvas.yview_scroll(int(-1 * event.delta), 'units')
        dialog.bind('<MouseWheel>', _on_wheel)
        scroll_frame.bind('<MouseWheel>', _on_wheel)
        main_frame.bind('<MouseWheel>', _on_wheel)
        canvas.bind('<MouseWheel>', _on_wheel)
        canvas.bind('<Enter>', lambda e: canvas.focus_set())

        check_vars = {}
        row = 0
        proto_frames = {}
        cmd_row_ranges = {}
        for proto, cmds in all_protos.items():
            proto_var = tk.BooleanVar(value=False)
            proto_frame = ttk.Frame(scroll_frame)
            proto_frame.grid(row=row, column=0, sticky=tk.W, pady=(4, 0))
            cb = ttk.Checkbutton(proto_frame, text=f'📁 {proto}',
                                 variable=proto_var)
            cb.pack(side=tk.LEFT)
            proto_frames[proto] = proto_frame
            collapse_var = tk.BooleanVar(value=True)
            row += 1
            cmd_vars = {}
            cmd_frames = []
            for cmd_name in cmds:
                cmd_var = tk.BooleanVar(value=False)
                cmd_frame = ttk.Frame(scroll_frame)
                cmd_frame.grid(row=row, column=0, sticky=tk.W, padx=(24, 0))
                ttk.Checkbutton(cmd_frame, text=f'  {cmd_name}',
                               variable=cmd_var).pack(side=tk.LEFT)
                cmd_vars[cmd_name] = cmd_var
                cmd_frames.append(cmd_frame)
                cmd_frame.collapse_var = collapse_var
                row += 1
            check_vars[proto] = (proto_var, cmd_vars, cmd_frames, collapse_var)

            def _toggle_collapse(event=None, _frames=cmd_frames, _var=collapse_var, _cb=cb):
                _var.set(not _var.get())
                visible = _var.get()
                for f in _frames:
                    if visible:
                        f.grid()
                    else:
                        f.grid_remove()
            cb.bind('<Button-3>', _toggle_collapse)

            def _on_proto_toggle(*args, _cmd_vars=cmd_vars, _proto_var=proto_var):
                checked = _proto_var.get()
                for cv in _cmd_vars.values():
                    cv.set(checked)
            proto_var.trace_add('write', _on_proto_toggle)

        def _select_all():
            for proto_var, cmd_vars, _, _ in check_vars.values():
                proto_var.set(True)
                for cv in cmd_vars.values():
                    cv.set(True)

        def _deselect_all():
            for proto_var, cmd_vars, _, _ in check_vars.values():
                proto_var.set(False)
                for cv in cmd_vars.values():
                    cv.set(False)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text='全选', command=_select_all, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='全不选', command=_deselect_all, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='取消', command=dialog.destroy, width=6).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_frame, text='加载选中', command=lambda: self._do_load_selected(dialog, editor, all_protos, check_vars), width=8).pack(side=tk.RIGHT)

    def _do_load_selected(self, dialog, editor, all_protos, check_vars):
        loaded = 0
        for proto, (proto_var, cmd_vars, _, _) in check_vars.items():
            for cmd_name, cmd_var in cmd_vars.items():
                if not cmd_var.get():
                    continue
                cmd_info = all_protos[proto][cmd_name]
                fields = cmd_info.get('fields', [])
                if not fields:
                    continue
                proto_type = cmd_info.get('type', 'hex') if isinstance(cmd_info, dict) else 'hex'
                if proto_type == 'json':
                    example = cmd_info.get('example', '')
                    self.add_json_protocol(fields, example, proto, cmd_name)
                else:
                    self.add_protocol(fields, proto, cmd_name)
                loaded += 1
        if loaded == 0:
            messagebox.showinfo('提示', '请至少勾选一个协议命令', parent=self.winfo_toplevel())
            return
        if self._log_panel:
            self._log_panel.log_info(f'[协议解析] 批量加载 {loaded} 个协议')
        dialog.destroy()

    def _on_remove_protocol(self):
        sel = self._proto_listbox.curselection()
        if sel:
            if messagebox.askyesno('确认', '确定移除选中的协议？', parent=self.winfo_toplevel()):
                self.remove_protocol(sel[0])

    def load_fields(self, fields, protocol_name='', command_name=''):
        self._protocols.clear()
        self.add_protocol(fields, protocol_name, command_name)

    # ============================================================
    # 自动解析
    # ============================================================

    def _on_auto_parse_toggle(self):
        if self._auto_parse_var.get():
            if self._log_panel:
                self._log_panel.log_info('[协议解析] 自动解析已开启')
        else:
            if self._log_panel:
                self._log_panel.log_info('[协议解析] 自动解析已关闭')

    def auto_parse(self, raw_str: str):
        if not self._auto_parse_var.get() or not raw_str:
            return

        # 先尝试将 HEX 字符串解码为 UTF-8 文本，再尝试 JSON
        decoded = None
        try:
            hex_clean = ''.join(c for c in raw_str if c in '0123456789abcdefABCDEF')
            if hex_clean:
                if len(hex_clean) % 2 != 0:
                    hex_clean = hex_clean[:-1]
                decoded = bytes.fromhex(hex_clean).decode('utf-8')
        except:
            pass

        json_candidates = [raw_str, decoded] if decoded else [raw_str]
        for candidate in json_candidates:
            if not candidate:
                continue
            try:
                data = json.loads(candidate)
                self._input_var.set(candidate)
                if self._json_protocols:
                    entry = self._get_selected_json_entry()
                    if entry:
                        self._parse_json_with_fields(data, entry)
                    else:
                        self._parse_json_with_fields(data, self._json_protocols[0])
                else:
                    self._show_json_result(data)
                self._result_notebook.select(1)
                if self._log_panel:
                    self._log_panel.log_info('[协议解析] ✅ JSON 解析完成')
                return
            except (json.JSONDecodeError, ValueError):
                continue

        hex_chars = ''.join(c for c in raw_str if c in '0123456789abcdefABCDEF')
        if not hex_chars:
            self._clear_results()
            self._status_var.set('❌ 无法解析：既不是 JSON 也不是 HEX 数据')
            return
        formatted = ' '.join(f'{hex_chars[i:i+2].upper()}' for i in range(0, len(hex_chars), 2))
        self._input_var.set(formatted)
        matched, proto_display = self._try_match_all(formatted)
        if matched:
            self._status_var.set(f'✅ 匹配协议: {proto_display}')
            self._result_notebook.select(0)
            if self._log_panel:
                self._log_panel.log_info(f'[协议解析] ✅ 自动匹配: {proto_display}')
        else:
            self._status_var.set('❌ 未匹配到任何协议')

    def _try_match_all(self, hex_str: str):
        try:
            hex_chars = ''.join(c for c in hex_str if c in '0123456789abcdefABCDEF')
            if len(hex_chars) % 2 != 0:
                hex_chars = hex_chars[:-1] + '0' + hex_chars[-1]
            data = hex_str_to_bytes(hex_chars)
        except Exception:
            return None, ''

        self._clear_results()
        self._total_len_var.set(f'数据长度: {len(data)} 字节')

        for entry in self._protocols:
            if not entry.enabled:
                continue
            if self._match_fixed_fields(data, entry.fields):
                display = f'{entry.protocol_name} → {entry.command_name}' if entry.protocol_name and entry.command_name else (entry.protocol_name or entry.command_name or '')
                self._parse_with_fields(data, entry.fields, display)
                return entry, display
        return None, ''

    def _match_fixed_fields(self, data: bytes, fields: list) -> bool:
        offset = 0
        for i, field in enumerate(fields):
            bc = field.get('byte_count', 1)
            if offset + bc > len(data):
                return False
            if field.get('field_type') == '固定值':
                actual = bytes_to_hex_str(data[offset:offset + bc])
                expected = field.get('hex_value', '')
                if not self._compare_hex(actual, expected):
                    return False
            offset += bc
        return True

    # ============================================================
    # JSON 解析
    # ============================================================

    def _show_json_result(self, data):
        self._clear_results()
        self._status_var.set('✅ JSON 解析完成')
        self._status_label.configure(foreground='green')
        self._match_count_var.set('字段数: 0 (无字段定义)')

        # 如果没有字段定义，显示原始树形结构
        for item in self._json_result_tree.get_children():
            self._json_result_tree.delete(item)

        def flatten_json(obj, path='', results=None):
            if results is None:
                results = []
            if isinstance(obj, dict):
                for key, value in obj.items():
                    cur_path = f'{path}.{key}' if path else key
                    if isinstance(value, (dict, list)):
                        flatten_json(value, cur_path, results)
                    else:
                        results.append((cur_path, value))
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    cur_path = f'{path}[{i}]'
                    if isinstance(value, (dict, list)):
                        flatten_json(value, cur_path, results)
                    else:
                        results.append((cur_path, value))
            return results

        for path, value in flatten_json(data):
            typ = type(value).__name__
            self._json_result_tree.insert('', tk.END,
                                          values=(path, typ, '', str(value), ''),
                                          tags=('undefined',))

    def _get_selected_json_entry(self):
        sel = self._proto_listbox.curselection()
        if sel:
            idx = sel[0]
            json_start = len(self._protocols)
            if idx >= json_start:
                return self._json_protocols[idx - json_start]
        return None

    def _parse_json_with_fields(self, data, entry: JsonProtocolEntry):
        self._clear_results()
        self._status_var.set('🔍 JSON 字段比对中...')

        fields = entry.fields
        for item in self._json_result_tree.get_children():
            self._json_result_tree.delete(item)

        match_count = 0
        total_count = 0
        status_tag = 'match'

        data_keys = set()
        self._collect_json_keys(data, data_keys)

        defined_keys = set()
        for f in fields:
            key = f.get('key', '')
            if key:
                defined_keys.add(key)

        for f in fields:
            key = f.get('key', '')
            if not key:
                continue
            total_count += 1
            expected_type = f.get('type', 'string')
            required = f.get('required', False)
            enum_vals = f.get('enum', [])
            min_val = f.get('minimum')
            max_val = f.get('maximum')
            pattern = f.get('pattern', '')

            # 构建约束描述
            constraints_parts = []
            if required:
                constraints_parts.append('必填')
            if enum_vals:
                constraints_parts.append(f'enum:{len(enum_vals)}项')
            if min_val is not None:
                constraints_parts.append(f'≥{min_val}')
            if max_val is not None:
                constraints_parts.append(f'≤{max_val}')
            if pattern:
                constraints_parts.append('regex')
            constraints_str = ', '.join(constraints_parts) if constraints_parts else '(无)'

            # 获取实际值
            actual_value = self._get_json_value(data, key)

            if actual_value is None:
                status = '⚠️ 缺失'
                status_tag = 'missing'
            else:
                actual_type = type(actual_value).__name__
                actual_display = str(actual_value)
                status, status_tag = self._check_json_constraint(
                    actual_value, actual_type, expected_type,
                    enum_vals, min_val, max_val, pattern
                )
                if '✅' in status:
                    match_count += 1

            self._json_result_tree.insert('', tk.END,
                                          values=(key, expected_type, constraints_str,
                                                  str(actual_value) if actual_value is not None else '(缺失)',
                                                  status),
                                          tags=(status_tag,))

        # 标记未定义字段
        undefined_keys = data_keys - defined_keys
        for key in sorted(undefined_keys):
            val = self._get_json_value(data, key)
            self._json_result_tree.insert('', tk.END,
                                          values=(key, '(未知)', '(未定义)', str(val) if val is not None else '', '⚠️ 未定义'),
                                          tags=('undefined',))
            total_count += 1

        self._match_count_var.set(f'匹配: {match_count}/{len(fields)}')
        if match_count == len(fields):
            self._status_var.set('✅ JSON 全部字段匹配')
            self._status_label.configure(foreground='green')
        elif match_count > 0:
            self._status_var.set(f'⚠️ 部分匹配 ({match_count}/{len(fields)})')
            self._status_label.configure(foreground='orange')
        else:
            self._status_var.set('❌ 全部不匹配')
            self._status_label.configure(foreground='red')

    def _collect_json_keys(self, data, keys, prefix=''):
        if isinstance(data, dict):
            for k, v in data.items():
                full_key = f'{prefix}.{k}' if prefix else k
                keys.add(full_key)
        elif isinstance(data, list):
            for i, v in enumerate(data):
                full_key = f'{prefix}[{i}]'
                keys.add(full_key)

    def _get_json_value(self, data, key_path):
        parts = key_path.replace('[', '.').replace(']', '').split('.')
        current = data
        for part in parts:
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    return None
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    if 0 <= idx < len(current):
                        current = current[idx]
                    else:
                        return None
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return current

    def _check_json_constraint(self, actual_value, actual_type, expected_type,
                                enum_vals, min_val, max_val, pattern):
        # 类型检查
        type_map = {
            'string': 'str',
            'integer': 'int',
            'number': ('int', 'float'),
            'boolean': 'bool',
            'object': 'dict',
            'array': 'list',
        }
        expected_py_types = type_map.get(expected_type, expected_type)
        if isinstance(expected_py_types, str):
            if actual_type != expected_py_types:
                return '❌ 类型', 'mismatch'
        else:
            if actual_type not in expected_py_types:
                return '❌ 类型', 'mismatch'

        # 枚举检查
        if enum_vals:
            if actual_value not in enum_vals and str(actual_value) not in [str(e) for e in enum_vals]:
                return '❌ 枚举', 'mismatch'

        # 范围检查
        if min_val is not None or max_val is not None:
            if isinstance(actual_value, (int, float)):
                if min_val is not None and actual_value < min_val:
                    return '❌ 超范围', 'mismatch'
                if max_val is not None and actual_value > max_val:
                    return '❌ 超范围', 'mismatch'

        # 正则检查
        if pattern and isinstance(actual_value, str):
            try:
                if not re.match(pattern, actual_value):
                    return '❌ 正则', 'mismatch'
            except re.error:
                pass

        return '✅ 匹配', 'match'

    # ============================================================
    # HEX 解析执行
    # ============================================================

    def set_input_data(self, data_str: str):
        self._input_var.set(data_str)

    def do_parse(self):
        self._do_parse()

    def _do_load_fields(self):
        sel = self._proto_listbox.curselection()
        if not sel:
            messagebox.showwarning('提示', '请先在已加载协议列表中选择一个协议', parent=self.winfo_toplevel())
            return

        idx = sel[0]
        json_start = len(self._protocols)
        if idx >= json_start:
            entry = self._json_protocols[idx - json_start]
            if entry.example:
                self._input_var.set(entry.example)
                try:
                    data = json.loads(entry.example)
                    self._parse_json_with_fields(data, entry)
                    self._result_notebook.select(1)
                except json.JSONDecodeError:
                    self._msgbox('提示', '示例数据无效', 'warning')
            return

        entry = self._protocols[idx]
        if not entry.fields:
            messagebox.showwarning('提示', '该协议没有字段定义', parent=self.winfo_toplevel())
            return

        self._clear_results()
        display = f'{entry.protocol_name} → {entry.command_name}' if entry.protocol_name and entry.command_name else (entry.protocol_name or entry.command_name or '')
        for i, field in enumerate(entry.fields):
            field_name = field.get('name', f'字段{i}')
            byte_count = field.get('byte_count', 1)
            expected = field.get('hex_value', '')
            desc = field.get('description', '')
            self._insert_result(display, i, field_name, expected, '', '', desc)
        self._total_len_var.set(f'数据长度: 0 字节')
        self._status_var.set(f'📋 已加载字段: {display}')

    def _msgbox(self, title, message, kind='info'):
        win = self.winfo_toplevel()
        getattr(messagebox, f'show{kind}')(title, message, parent=win)

    def _do_parse(self):
        input_str = self._input_var.get().strip()
        if not input_str:
            messagebox.showwarning('提示', '请输入待解析的数据', parent=self.winfo_toplevel())
            return

        try:
            data = json.loads(input_str)
            if self._json_protocols:
                entry = self._get_selected_json_entry()
                if entry:
                    self._parse_json_with_fields(data, entry)
                else:
                    self._parse_json_with_fields(data, self._json_protocols[0])
            else:
                self._show_json_result(data)
            self._result_notebook.select(1)
            return
        except (json.JSONDecodeError, ValueError):
            pass

        self._do_hex_parse(input_str)

    def _do_hex_parse(self, input_str):
        if not self._protocols:
            messagebox.showwarning('提示', '请先添加协议', parent=self.winfo_toplevel())
            return
        self._result_notebook.select(0)
        sel = self._proto_listbox.curselection()
        if sel:
            idx = sel[0]
            if idx < len(self._protocols):
                entry = self._protocols[idx]
                self._parse_single(input_str, entry)
            else:
                messagebox.showwarning('提示', '当前协议不是 HEX 协议', parent=self.winfo_toplevel())
        else:
            self._parse_all(input_str)

    def _parse_all(self, input_str: str):
        self._clear_results()
        data = self._prepare_data(input_str)
        if data is None:
            return
        self._total_len_var.set(f'数据长度: {len(data)} 字节')

        any_matched = False
        for entry in self._protocols:
            if self._match_fixed_fields(data, entry.fields):
                display = f'{entry.protocol_name} → {entry.command_name}' if entry.protocol_name and entry.command_name else (entry.protocol_name or entry.command_name or '')
                self._parse_with_fields(data, entry.fields, display)
                any_matched = True

        if not any_matched:
            self._status_var.set('❌ 未匹配到任何协议')
            self._status_label.configure(foreground='red')
            self._match_count_var.set('匹配: 0/0')

    def _parse_single(self, input_str: str, entry: ProtocolEntry):
        self._clear_results()
        data = self._prepare_data(input_str)
        if data is None:
            return
        self._total_len_var.set(f'数据长度: {len(data)} 字节')
        display = f'{entry.protocol_name} → {entry.command_name}' if entry.protocol_name and entry.command_name else (entry.protocol_name or entry.command_name or '')
        self._parse_with_fields(data, entry.fields, display)

    def _prepare_data(self, input_str: str):
        hex_chars = ''.join(c for c in input_str if c in '0123456789abcdefABCDEF')
        if len(hex_chars) % 2 != 0:
            hex_chars = hex_chars[:-1] + '0' + hex_chars[-1]
        formatted = ' '.join(f'{hex_chars[i:i+2].upper()}' for i in range(0, len(hex_chars), 2))
        self._input_var.set(formatted)
        try:
            return hex_str_to_bytes(formatted)
        except Exception as e:
            messagebox.showerror('解析失败', f'无效的 HEX 数据: {e}', parent=self.winfo_toplevel())
            return None

    def _parse_with_fields(self, data: bytes, fields: list, proto_name: str = ''):
        offset = 0
        match_count = 0
        total_count = len(fields)

        for i, field in enumerate(fields):
            field_name = field.get('name', f'字段{i}')
            byte_count = field.get('byte_count', 1)
            field_type = field.get('field_type', '数据')
            parse_mode = field.get('parse_mode', '无需解析(组包指令)')
            description = field.get('description', '')

            if offset + byte_count > len(data):
                self._insert_result(proto_name, i, field_name, f'需要 {byte_count} 字节',
                                    f'剩余 {len(data) - offset} 字节',
                                    '❌ 数据不足', description or '数据长度不足')
                continue

            actual_bytes = data[offset:offset + byte_count]
            actual_hex = bytes_to_hex_str(actual_bytes)
            actual_value = int.from_bytes(actual_bytes, byteorder='big')
            expected_hex = ''
            is_match = False

            if field_type == '固定值':
                expected_hex = field.get('hex_value', '')
                is_match = self._compare_hex(actual_hex, expected_hex)

            elif field_type == '长度':
                try:
                    bo = field.get('length_byte_order', 'big')
                    actual_len = int.from_bytes(actual_bytes, byteorder=bo)
                    expected_len = self._calc_expected_length(fields, i)
                    expected_hex = format(expected_len, 'X')
                    if len(expected_hex) % 2:
                        expected_hex = '0' + expected_hex
                    expected_hex = ' '.join(expected_hex[j:j+2] for j in range(0, len(expected_hex), 2))
                    is_match = (actual_len == expected_len)
                except Exception:
                    expected_hex = '(计算失败)'
                    is_match = False

            elif field_type == '校验':
                try:
                    algo = field.get('checksum_algorithm', 'CRC16/MODBUS')
                    bo = field.get('checksum_byte_order', 'big')
                    chk_data = self._get_checksum_data(data, fields, i)
                    _, expected_bytes = calc_checksum(chk_data, algo)
                    if bo == 'little':
                        expected_bytes = expected_bytes[::-1]
                    expected_hex = bytes_to_hex_str(expected_bytes[:byte_count])
                    is_match = (actual_bytes[:byte_count] == expected_bytes[:byte_count])
                except Exception:
                    expected_hex = '(计算失败)'
                    is_match = False

            else:
                expected_hex = field.get('hex_value', '')

                if parse_mode == '固定值':
                    is_match = self._compare_hex(actual_hex, expected_hex)

                elif parse_mode in ('枚举映射', '位解析'):
                    enum_mappings = field.get('enum_mappings', [])
                    matched_enum = None
                    for mapping in enum_mappings:
                        if mapping['value'] == actual_value:
                            matched_enum = mapping
                            break
                    is_match = (matched_enum is not None)

                elif parse_mode == '位标志':
                    is_match = True

                else:
                    is_match = True

            status_text = '✅ 匹配' if is_match else '❌ 不匹配'
            if is_match:
                match_count += 1

            display_status = status_text
            if parse_mode in ('枚举映射', '位解析', '位标志'):
                enum_mappings = field.get('enum_mappings', [])
                if enum_mappings:
                    matched_label = None
                    for mapping in enum_mappings:
                        if mapping['value'] == actual_value:
                            matched_label = mapping['label']
                            break
                    if matched_label:
                        display_status = f'{status_text} [{matched_label}]'
                    else:
                        display_status = f'{status_text} [未知值]'

            self._insert_result(proto_name, i, field_name, expected_hex, actual_hex,
                                display_status, description)

            offset += byte_count

        self._update_status(match_count, total_count, proto_name)

    def _update_status(self, match_count: int, total_count: int, proto_name: str = ''):
        tag = f' [{proto_name}]' if proto_name else ''
        self._match_count_var.set(f'匹配: {match_count}/{total_count}{tag}')
        if match_count == total_count:
            self._status_var.set(f'✅ 全部匹配{tag}')
            self._status_label.configure(foreground='green')
        elif match_count > 0:
            self._status_var.set(f'⚠️ 部分匹配 ({match_count}/{total_count}){tag}')
            self._status_label.configure(foreground='orange')
        else:
            self._status_var.set(f'❌ 全部不匹配{tag}')
            self._status_label.configure(foreground='red')

        if self._result_tree.get_children():
            self._result_tree.see(self._result_tree.get_children()[0])

    def _insert_result(self, proto_name, index, field_name, expected, actual, status, desc):
        tag = 'match' if '✅' in status else 'mismatch'
        iid = f'{proto_name}_{index}' if proto_name else str(index)
        display_proto = proto_name if proto_name else ''
        self._result_tree.insert('', tk.END, iid=iid,
                                 values=(display_proto, index + 1, field_name,
                                         expected, actual, status, desc),
                                 tags=(tag,))

    # ============================================================
    # 工具方法
    # ============================================================

    def _clear_results(self):
        for item in self._result_tree.get_children():
            self._result_tree.delete(item)
        for item in self._json_result_tree.get_children():
            self._json_result_tree.delete(item)
        self._status_var.set('就绪')
        self._match_count_var.set('匹配: 0/0')
        self._total_len_var.set('数据长度: 0 字节')

    def _on_input_change(self, event=None):
        self._auto_format_input()

    def _on_input_var_change(self, var_name=None, index=None, operation=None):
        pass

    def _auto_format_input(self):
        raw = self._input_var.get().strip()
        if not raw:
            return
        if raw.startswith('{') or raw.startswith('['):
            return
        hex_chars = ''.join(c for c in raw if c in '0123456789abcdefABCDEF')
        if not hex_chars:
            return
        formatted = ' '.join(f'{hex_chars[i:i+2].upper()}' for i in range(0, len(hex_chars), 2))
        if formatted != raw:
            cursor_pos = self._input_entry.index(tk.INSERT)
            before_cursor = raw[:cursor_pos]
            hex_before = ''.join(c for c in before_cursor if c in '0123456789abcdefABCDEF')
            hex_count = len(hex_before)
            new_pos = hex_count + (hex_count // 2)
            self._input_var.set(formatted)
            try:
                self._input_entry.icursor(new_pos)
            except:
                pass

    def _compare_hex(self, actual_hex: str, expected_hex: str) -> bool:
        actual = actual_hex.replace(' ', '').upper()
        expected = expected_hex.replace(' ', '').upper()
        return actual == expected

    def _calc_expected_length(self, fields: list, field_index: int) -> int:
        start = fields[field_index].get('length_start', 0)
        end = fields[field_index].get('length_end', 0)
        if start == 0 and end == 0:
            total = 0
            for j, f in enumerate(fields):
                if j != field_index:
                    total += f.get('byte_count', 0)
            return total
        else:
            start = max(0, start)
            end = min(len(fields) - 1, end)
            total = 0
            for j in range(start, end + 1):
                if j != field_index:
                    total += fields[j].get('byte_count', 0)
            return total

    def _get_checksum_data(self, data: bytes, fields: list, field_index: int) -> bytes:
        start = fields[field_index].get('checksum_start', 0)
        end = fields[field_index].get('checksum_end', 0)
        offset = 0
        chk_data = b''
        for j, f in enumerate(fields):
            bc = f.get('byte_count', 1)
            if j == field_index:
                offset += bc
                continue
            if start <= j <= end:
                chk_data += data[offset:offset + bc]
            offset += bc
        return chk_data

    def get_settings(self) -> dict:
        protocols_data = []
        for entry in self._protocols:
            protocols_data.append({
                'fields': entry.fields,
                'protocol_name': entry.protocol_name,
                'command_name': entry.command_name,
                'enabled': entry.enabled,
                'proto_type': 'hex',
            })
        for entry in self._json_protocols:
            protocols_data.append({
                'fields': entry.fields,
                'example': entry.example,
                'protocol_name': entry.protocol_name,
                'command_name': entry.command_name,
                'enabled': entry.enabled,
                'proto_type': 'json',
            })
        return {
            'protocols': protocols_data,
            'auto_parse': self._auto_parse_var.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        auto_parse = settings.get('auto_parse', False)
        protocols_data = settings.get('protocols', [])
        if protocols_data:
            self._protocols.clear()
            self._json_protocols.clear()
            for p in protocols_data:
                proto_type = p.get('proto_type', 'hex')
                if proto_type == 'json':
                    entry = JsonProtocolEntry(
                        p.get('fields', []),
                        p.get('example', ''),
                        p.get('protocol_name', ''),
                        p.get('command_name', ''),
                    )
                    entry.enabled = p.get('enabled', True)
                    self._json_protocols.append(entry)
                else:
                    entry = ProtocolEntry(
                        p.get('fields', []),
                        p.get('protocol_name', ''),
                        p.get('command_name', ''),
                    )
                    entry.enabled = p.get('enabled', True)
                    self._protocols.append(entry)
            self._refresh_proto_list()
        if auto_parse:
            self._auto_parse_var.set(True)
