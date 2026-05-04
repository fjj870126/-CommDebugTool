"""条件触发告警面板 - 收到特定数据时触发告警"""

import tkinter as tk
from tkinter import ttk, messagebox
from utils.hex_utils import hex_str_to_bytes, bytes_to_hex_str
from utils.context_menu import add_entry_context_menu


class AlertPanel(ttk.LabelFrame):
    """条件触发告警面板"""

    def __init__(self, parent, log_panel=None):
        super().__init__(parent, text=' 条件告警 ', padding=8)
        self._log_panel = log_panel
        self._rules = []  # [(match_hex, match_mode, alert_type, alert_msg), ...]
        self._enabled = True
        self._build_ui()

    def _build_ui(self):
        # 启用开关
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, pady=(0, 4))

        self.enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top_frame, text='启用告警', variable=self.enabled_var,
                        command=self._on_enable_toggle).pack(side=tk.LEFT)

        ttk.Label(top_frame, text='当收到匹配数据时触发告警', foreground='gray').pack(side=tk.RIGHT)

        # 规则列表
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('match', 'mode', 'type', 'message')
        self.rule_tree = ttk.Treeview(list_frame, columns=columns, show='headings',
                                      height=4, selectmode='browse')
        self.rule_tree.heading('match', text='匹配数据(Hex)')
        self.rule_tree.heading('mode', text='模式')
        self.rule_tree.heading('type', text='告警类型')
        self.rule_tree.heading('message', text='告警消息')

        self.rule_tree.column('match', width=120, minwidth=80)
        self.rule_tree.column('mode', width=60, minwidth=40, anchor=tk.CENTER)
        self.rule_tree.column('type', width=60, minwidth=40, anchor=tk.CENTER)
        self.rule_tree.column('message', width=150, minwidth=80)

        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.rule_tree.yview)
        self.rule_tree.configure(yscrollcommand=tree_scroll.set)

        self.rule_tree.grid(row=0, column=0, sticky='nsew')
        tree_scroll.grid(row=0, column=1, sticky='ns')
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # 规则编辑区
        edit_frame = ttk.LabelFrame(self, text=' 添加/编辑规则 ', padding=6)
        edit_frame.pack(fill=tk.X, pady=(4, 0))

        # 第一行
        r1 = ttk.Frame(edit_frame)
        r1.pack(fill=tk.X, pady=2)

        ttk.Label(r1, text='匹配数据(Hex):').pack(side=tk.LEFT)
        self.match_var = tk.StringVar(value='')
        self.match_entry = ttk.Entry(r1, textvariable=self.match_var,
                                     font=('Courier New', 10), width=20)
        self.match_entry.pack(side=tk.LEFT, padx=(4, 8), fill=tk.X, expand=True)
        add_entry_context_menu(self.match_entry)

        ttk.Label(r1, text='匹配模式:').pack(side=tk.LEFT)
        self.match_mode_var = tk.StringVar(value='完全匹配')
        ttk.Combobox(r1, textvariable=self.match_mode_var,
                     values=['完全匹配', '包含匹配', '开头匹配', '结尾匹配'],
                     state='readonly', width=8).pack(side=tk.LEFT, padx=(4, 0))

        # 第二行
        r2 = ttk.Frame(edit_frame)
        r2.pack(fill=tk.X, pady=2)

        ttk.Label(r2, text='告警类型:').pack(side=tk.LEFT)
        self.alert_type_var = tk.StringVar(value='日志告警')
        ttk.Combobox(r2, textvariable=self.alert_type_var,
                     values=['日志告警', '弹窗告警', '日志+弹窗', '播放声音'],
                     state='readonly', width=10).pack(side=tk.LEFT, padx=(4, 8))

        ttk.Label(r2, text='告警消息:').pack(side=tk.LEFT)
        self.msg_var = tk.StringVar(value='收到告警数据!')
        self.msg_entry = ttk.Entry(r2, textvariable=self.msg_var, width=20)
        self.msg_entry.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)
        add_entry_context_menu(self.msg_entry)

        # 按钮
        btn_frame = ttk.Frame(edit_frame)
        btn_frame.pack(fill=tk.X, pady=(4, 0))

        ttk.Button(btn_frame, text='添加规则', command=self._add_rule, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='删除规则', command=self._delete_rule, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='清空规则', command=self._clear_rules, width=10).pack(side=tk.LEFT, padx=2)

    def _on_enable_toggle(self):
        self._enabled = self.enabled_var.get()

    def _add_rule(self):
        """添加规则"""
        match_hex = self.match_var.get().strip()
        if not match_hex:
            messagebox.showwarning('提示', '请输入匹配数据')
            return
        try:
            hex_str_to_bytes(match_hex)
        except Exception:
            messagebox.showerror('错误', '无效的 Hex 数据')
            return

        mode = self.match_mode_var.get()
        alert_type = self.alert_type_var.get()
        msg = self.msg_var.get().strip()
        if not msg:
            msg = '收到告警数据!'

        self._rules.append((match_hex, mode, alert_type, msg))
        self.rule_tree.insert('', tk.END, values=(match_hex, mode, alert_type, msg))

        # 清空输入
        self.match_var.set('')
        self.msg_var.set('收到告警数据!')

    def _delete_rule(self):
        """删除规则"""
        selected = self.rule_tree.selection()
        if not selected:
            return
        idx = self.rule_tree.index(selected[0])
        self.rule_tree.delete(selected[0])
        if 0 <= idx < len(self._rules):
            self._rules.pop(idx)

    def _clear_rules(self):
        """清空规则"""
        if not self._rules:
            return
        if messagebox.askyesno('确认', '确定要清空所有规则吗？'):
            self._rules.clear()
            for item in self.rule_tree.get_children():
                self.rule_tree.delete(item)

    def check_data(self, data: bytes) -> bool:
        """检查数据是否匹配任何规则，匹配则触发告警
        返回: True 表示匹配了某个规则
        """
        if not self._enabled or not self._rules:
            return False

        matched = False
        for match_hex, mode, alert_type, msg in self._rules:
            try:
                match_bytes = hex_str_to_bytes(match_hex)
            except Exception:
                continue

            is_match = False
            if mode == '完全匹配':
                is_match = (data == match_bytes)
            elif mode == '包含匹配':
                is_match = (match_bytes in data)
            elif mode == '开头匹配':
                is_match = data.startswith(match_bytes)
            elif mode == '结尾匹配':
                is_match = data.endswith(match_bytes)

            if is_match:
                matched = True
                self._trigger_alert(alert_type, msg, data)

        return matched

    def _trigger_alert(self, alert_type: str, msg: str, data: bytes):
        """触发告警"""
        hex_str = bytes_to_hex_str(data)

        if alert_type in ('日志告警', '日志+弹窗'):
            if self._log_panel:
                self._log_panel.log_info(f'[告警] {msg} (数据: {hex_str})')

        if alert_type in ('弹窗告警', '日志+弹窗'):
            messagebox.showwarning('告警', f'{msg}\n\n数据: {hex_str}')

        if alert_type == '播放声音':
            # 使用系统 bell
            try:
                self.bell()
            except Exception:
                pass
            if self._log_panel:
                self._log_panel.log_info(f'[告警-声音] {msg} (数据: {hex_str})')

    def get_settings(self) -> dict:
        rules = []
        for match_hex, mode, alert_type, msg in self._rules:
            rules.append({
                'match_hex': match_hex,
                'mode': mode,
                'alert_type': alert_type,
                'message': msg,
            })
        return {
            'enabled': self._enabled,
            'rules': rules,
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        self._enabled = settings.get('enabled', True)
        self.enabled_var.set(self._enabled)
        rules = settings.get('rules', [])
        for rule in rules:
            match_hex = rule.get('match_hex', '')
            mode = rule.get('mode', '完全匹配')
            alert_type = rule.get('alert_type', '日志告警')
            msg = rule.get('message', '收到告警数据!')
            self._rules.append((match_hex, mode, alert_type, msg))
            self.rule_tree.insert('', tk.END, values=(match_hex, mode, alert_type, msg))
