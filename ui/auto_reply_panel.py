"""批量自动回复面板 - 支持多条规则，每条规则可独立启用/禁用"""
import tkinter as tk
from tkinter import ttk, messagebox
from utils.hex_utils import hex_str_to_bytes, bytes_to_hex_str
from utils.context_menu import add_entry_context_menu


class AutoReplyPanel(ttk.LabelFrame):
    """批量自动回复面板"""

    def __init__(self, parent, on_send=None, log_panel=None):
        super().__init__(parent, text=' 批量自动回复 ', padding=8)
        self._on_send = on_send
        self._log_panel = log_panel
        self._rules = []
        self._build_ui()

    def _build_ui(self):
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, pady=(0, 4))

        self.enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top_frame, text='启用批量自动回复', variable=self.enabled_var).pack(side=tk.LEFT)
        ttk.Label(top_frame, text='收到匹配数据时自动回复', foreground='gray').pack(side=tk.RIGHT)

        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        columns = ('enabled', 'match', 'reply', 'mode')
        self.rule_tree = ttk.Treeview(list_frame, columns=columns, show='headings',
                                      height=4, selectmode='browse')
        self.rule_tree.heading('enabled', text='启用')
        self.rule_tree.heading('match', text='判断数据(Hex)')
        self.rule_tree.heading('reply', text='回复数据(Hex)')
        self.rule_tree.heading('mode', text='匹配模式')

        self.rule_tree.column('enabled', width=40, minwidth=30, anchor=tk.CENTER)
        self.rule_tree.column('match', width=140, minwidth=80)
        self.rule_tree.column('reply', width=140, minwidth=80)
        self.rule_tree.column('mode', width=80, minwidth=50, anchor=tk.CENTER)

        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.rule_tree.yview)
        self.rule_tree.configure(yscrollcommand=tree_scroll.set)

        self.rule_tree.grid(row=0, column=0, sticky='nsew')
        tree_scroll.grid(row=0, column=1, sticky='ns')
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.rule_tree.bind('<ButtonRelease-1>', self._on_tree_click)

        edit_frame = ttk.LabelFrame(self, text=' 添加/编辑规则 ', padding=6)
        edit_frame.pack(fill=tk.X)

        r1 = ttk.Frame(edit_frame)
        r1.pack(fill=tk.X, pady=2)

        ttk.Label(r1, text='判断数据(Hex):').pack(side=tk.LEFT)
        self.match_var = tk.StringVar(value='')
        self.match_entry = ttk.Entry(r1, textvariable=self.match_var,
                                     font=('Courier New', 10), width=16)
        self.match_entry.pack(side=tk.LEFT, padx=(4, 8), fill=tk.X, expand=True)
        add_entry_context_menu(self.match_entry)

        ttk.Label(r1, text='匹配模式:').pack(side=tk.LEFT)
        self.match_mode_var = tk.StringVar(value='完全匹配')
        ttk.Combobox(r1, textvariable=self.match_mode_var,
                     values=['完全匹配', '包含匹配', '开头匹配', '结尾匹配', '正则匹配'],
                     state='readonly', width=10).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Label(r1, text='延迟(ms):').pack(side=tk.LEFT, padx=(8, 2))
        self.delay_var = tk.StringVar(value='0')
        ttk.Spinbox(r1, from_=0, to=10000, textvariable=self.delay_var,
                    width=5).pack(side=tk.LEFT)

        r2 = ttk.Frame(edit_frame)
        r2.pack(fill=tk.X, pady=2)

        ttk.Label(r2, text='回复数据(Hex):').pack(side=tk.LEFT)
        self.reply_var = tk.StringVar(value='')
        self.reply_entry = ttk.Entry(r2, textvariable=self.reply_var,
                                     font=('Courier New', 10), width=16)
        self.reply_entry.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)
        add_entry_context_menu(self.reply_entry)
        ttk.Label(r2, text='{data}=原始数据', foreground='gray', font=('', 8)).pack(side=tk.LEFT, padx=(4, 0))

        btn_frame = ttk.Frame(edit_frame)
        btn_frame.pack(fill=tk.X, pady=(4, 0))

        ttk.Button(btn_frame, text='添加规则', command=self._add_rule, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='删除规则', command=self._delete_rule, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='清空规则', command=self._clear_rules, width=10).pack(side=tk.LEFT, padx=2)

    def _on_tree_click(self, event):
        region = self.rule_tree.identify_region(event.x, event.y)
        column = self.rule_tree.identify_column(event.x)
        item = self.rule_tree.identify_row(event.y)
        if not item or region != 'cell' or column != '#0':
            return
        idx = self.rule_tree.index(item)
        if 0 <= idx < len(self._rules):
            rule = self._rules[idx]
            rule['enabled'] = not rule['enabled']
            values = ('✓' if rule['enabled'] else '✗', rule['match'], rule['reply'], rule['mode'])
            self.rule_tree.item(item, values=values)

    def _add_rule(self):
        match_hex = self.match_var.get().strip()
        reply_hex = self.reply_var.get().strip()
        if not match_hex or not reply_hex:
            messagebox.showwarning('提示', '请输入判断数据和回复数据')
            return
        try:
            hex_str_to_bytes(match_hex)
            hex_str_to_bytes(reply_hex)
        except Exception:
            messagebox.showerror('错误', '无效的 Hex 数据')
            return

        mode = self.match_mode_var.get()
        try:
            delay = int(self.delay_var.get())
        except ValueError:
            delay = 0
        rule = {'enabled': True, 'match': match_hex, 'reply': reply_hex,
                'mode': mode, 'delay': delay}
        self._rules.append(rule)
        self.rule_tree.insert('', tk.END, values=('✓', match_hex, reply_hex, mode))
        self.match_var.set('')
        self.reply_var.set('')

    def _delete_rule(self):
        selected = self.rule_tree.selection()
        if not selected:
            return
        idx = self.rule_tree.index(selected[0])
        self.rule_tree.delete(selected[0])
        if 0 <= idx < len(self._rules):
            self._rules.pop(idx)

    def _clear_rules(self):
        if not self._rules:
            return
        if messagebox.askyesno('确认', '确定要清空所有规则吗？'):
            self._rules.clear()
            for item in self.rule_tree.get_children():
                self.rule_tree.delete(item)

    def check_and_reply(self, received_data: bytes) -> bool:
        """检查接收数据是否匹配任何规则，匹配则自动回复（支持正则、变量替换、延迟）"""
        if not self.enabled_var.get() or not self._rules:
            return False

        import re
        matched = False

        def do_reply(rule, reply_bytes):
            if self._on_send and reply_bytes:
                self._on_send(reply_bytes, is_heartbeat=True)
            if self._log_panel:
                hex_str = bytes_to_hex_str(reply_bytes)
                self._log_panel.log_info(f'[批量自动回复] 匹配规则, 已回复: {hex_str}')

        for rule in self._rules:
            if not rule['enabled']:
                continue
            try:
                match_bytes = hex_str_to_bytes(rule['match'])
            except Exception:
                continue

            is_match = False
            mode = rule['mode']
            if mode == '完全匹配':
                is_match = (received_data == match_bytes)
            elif mode == '包含匹配':
                is_match = (match_bytes in received_data)
            elif mode == '开头匹配':
                is_match = received_data.startswith(match_bytes)
            elif mode == '结尾匹配':
                is_match = received_data.endswith(match_bytes)
            elif mode == '正则匹配':
                try:
                    pattern = re.compile(rule['match'])
                    is_match = bool(pattern.search(bytes_to_hex_str(received_data)))
                except re.error:
                    continue

            if not is_match:
                continue

            matched = True
            # 变量替换：{data} → 原始数据的 HEX
            reply_hex = rule['reply']
            if '{data}' in reply_hex:
                reply_hex = reply_hex.replace('{data}', bytes_to_hex_str(received_data))
            try:
                reply_bytes = hex_str_to_bytes(reply_hex)
            except Exception:
                continue

            delay = rule.get('delay', 0)
            if delay > 0:
                self.after(delay, lambda rb=reply_bytes: do_reply(rule, rb))
            else:
                do_reply(rule, reply_bytes)

        return matched

    def get_settings(self) -> dict:
        return {
            'enabled': self.enabled_var.get(),
            'rules': self._rules,
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        self.enabled_var.set(settings.get('enabled', True))
        for rule in settings.get('rules', []):
            r = {
                'enabled': rule.get('enabled', True),
                'match': rule.get('match', ''),
                'reply': rule.get('reply', ''),
                'mode': rule.get('mode', '完全匹配'),
                'delay': rule.get('delay', 0),
            }
            self._rules.append(r)
            enabled_text = '✓' if r['enabled'] else '✗'
            self.rule_tree.insert('', tk.END, values=(enabled_text, r['match'], r['reply'], r['mode']))
