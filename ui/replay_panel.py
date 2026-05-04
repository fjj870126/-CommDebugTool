"""数据回放面板 - 记录收发数据并支持回放"""

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from utils.hex_utils import bytes_to_hex_str, hex_str_to_bytes
from utils.context_menu import add_entry_context_menu


class ReplayPanel(ttk.LabelFrame):
    """数据回放面板"""

    def __init__(self, parent, on_send=None, log_panel=None):
        super().__init__(parent, text=' 数据回放 ', padding=8)
        self._on_send = on_send
        self._log_panel = log_panel
        self._records = []  # [(timestamp, direction, data_bytes, hex_str), ...]
        self._recording = False
        self._build_ui()

    def _build_ui(self):
        # 工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 4))

        self.record_btn = ttk.Button(toolbar, text='● 开始记录', command=self._toggle_record, width=12)
        self.record_btn.pack(side=tk.LEFT, padx=(0, 4))

        ttk.Button(toolbar, text='清空记录', command=self._clear_records, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text='导出记录', command=self._export_records, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text='导入记录', command=self._import_records, width=8).pack(side=tk.LEFT, padx=2)

        self.record_count_var = tk.StringVar(value='记录: 0 条')
        ttk.Label(toolbar, textvariable=self.record_count_var, foreground='gray').pack(side=tk.RIGHT)

        # 记录列表
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('time', 'dir', 'data')
        self.record_tree = ttk.Treeview(list_frame, columns=columns, show='headings',
                                        height=6, selectmode='extended')
        self.record_tree.heading('time', text='时间')
        self.record_tree.heading('dir', text='方向')
        self.record_tree.heading('data', text='数据(Hex)')

        self.record_tree.column('time', width=80, minwidth=60, anchor=tk.W)
        self.record_tree.column('dir', width=40, minwidth=30, anchor=tk.CENTER)
        self.record_tree.column('data', width=250, minwidth=100, anchor=tk.W)

        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.record_tree.yview)
        self.record_tree.configure(yscrollcommand=tree_scroll.set)

        self.record_tree.grid(row=0, column=0, sticky='nsew')
        tree_scroll.grid(row=0, column=1, sticky='ns')
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # 回放控制区
        replay_frame = ttk.Frame(self)
        replay_frame.pack(fill=tk.X, pady=(4, 0))

        ttk.Label(replay_frame, text='回放模式:').pack(side=tk.LEFT)
        self.replay_mode_var = tk.StringVar(value='选中回放')
        replay_cb = ttk.Combobox(replay_frame, textvariable=self.replay_mode_var,
                                 values=['选中回放', '全部回放', '循环回放'], state='readonly', width=10)
        replay_cb.pack(side=tk.LEFT, padx=(4, 8))
        add_entry_context_menu(replay_cb)

        ttk.Label(replay_frame, text='间隔(ms):').pack(side=tk.LEFT)
        self.replay_interval_var = tk.StringVar(value='200')
        self.replay_interval_entry = ttk.Entry(replay_frame, textvariable=self.replay_interval_var, width=6)
        self.replay_interval_entry.pack(side=tk.LEFT, padx=(4, 8))
        add_entry_context_menu(self.replay_interval_entry)

        self.replay_btn = ttk.Button(replay_frame, text='▶ 回放', command=self._start_replay, width=8)
        self.replay_btn.pack(side=tk.LEFT, padx=2)

        self.stop_btn = ttk.Button(replay_frame, text='■ 停止', command=self._stop_replay,
                                   state=tk.DISABLED, width=8)
        self.stop_btn.pack(side=tk.LEFT, padx=2)

        self.replay_status_var = tk.StringVar(value='')
        ttk.Label(replay_frame, textvariable=self.replay_status_var, foreground='blue').pack(side=tk.RIGHT)

        self._replay_running = False
        self._replay_timer_id = None

    def _toggle_record(self):
        """切换记录状态"""
        self._recording = not self._recording
        if self._recording:
            self.record_btn.configure(text='● 停止记录')
            self.record_btn.configure(style='')
            if self._log_panel:
                self._log_panel.log_info('▶ 开始记录数据')
        else:
            self.record_btn.configure(text='● 开始记录')
            if self._log_panel:
                self._log_panel.log_info(f'■ 停止记录，共 {len(self._records)} 条')

    def record_data(self, data: bytes, direction: str):
        """记录一条数据"""
        if not self._recording:
            return
        timestamp = datetime.now().strftime('%H:%M:%S')
        hex_str = bytes_to_hex_str(data)
        self._records.append((timestamp, direction, data, hex_str))
        self.record_tree.insert('', tk.END, values=(timestamp, direction, hex_str))
        self.record_count_var.set(f'记录: {len(self._records)} 条')
        # 自动滚动到底部
        self.record_tree.see(self.record_tree.get_children()[-1])

    def _clear_records(self):
        """清空记录"""
        if not self._records:
            return
        if messagebox.askyesno('确认', '确定要清空所有记录吗？'):
            self._records.clear()
            for item in self.record_tree.get_children():
                self.record_tree.delete(item)
            self.record_count_var.set('记录: 0 条')

    def _export_records(self):
        """导出记录到文件"""
        if not self._records:
            messagebox.showwarning('提示', '没有记录可导出')
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension='.json',
            filetypes=[('JSON文件', '*.json'), ('所有文件', '*.*')],
            title='导出记录'
        )
        if not filepath:
            return
        try:
            export_data = []
            for ts, direction, data, hex_str in self._records:
                export_data.append({
                    'time': ts,
                    'direction': direction,
                    'hex': hex_str,
                })
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo('成功', f'已导出 {len(export_data)} 条记录')
        except Exception as e:
            messagebox.showerror('导出失败', str(e))

    def _import_records(self):
        """从文件导入记录"""
        filepath = filedialog.askopenfilename(
            filetypes=[('JSON文件', '*.json'), ('所有文件', '*.*')],
            title='导入记录'
        )
        if not filepath:
            return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            for item in import_data:
                ts = item.get('time', '')
                direction = item.get('direction', 'RX')
                hex_str = item.get('hex', '')
                try:
                    data = hex_str_to_bytes(hex_str)
                except Exception:
                    data = b''
                self._records.append((ts, direction, data, hex_str))
                self.record_tree.insert('', tk.END, values=(ts, direction, hex_str))
            self.record_count_var.set(f'记录: {len(self._records)} 条')
            messagebox.showinfo('成功', f'已导入 {len(import_data)} 条记录')
        except Exception as e:
            messagebox.showerror('导入失败', str(e))

    def _start_replay(self):
        """开始回放"""
        if not self._records:
            messagebox.showwarning('提示', '没有记录可回放')
            return

        mode = self.replay_mode_var.get()
        if mode == '选中回放':
            selected = self.record_tree.selection()
            if not selected:
                messagebox.showwarning('提示', '请先选择要回放的记录')
                return
            indices = [int(self.record_tree.index(item)) for item in selected]
            self._replay_queue = [self._records[i] for i in indices]
        else:
            self._replay_queue = list(self._records)

        if not self._replay_queue:
            return

        try:
            interval = int(self.replay_interval_var.get())
        except ValueError:
            interval = 200
        interval = max(10, interval)

        self._replay_running = True
        self._replay_index = 0
        self._replay_interval = interval
        self._replay_mode = mode

        self.replay_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.replay_status_var.set(f'回放中... 0/{len(self._replay_queue)}')

        self._do_replay_step()

    def _do_replay_step(self):
        """执行一步回放"""
        if not self._replay_running or self._replay_index >= len(self._replay_queue):
            self._on_replay_done()
            return

        ts, direction, data, hex_str = self._replay_queue[self._replay_index]
        if self._on_send and data:
            self._on_send(data)

        self._replay_index += 1
        self.replay_status_var.set(f'回放中... {self._replay_index}/{len(self._replay_queue)}')

        # 高亮当前行
        for item in self.record_tree.get_children():
            self.record_tree.selection_remove(item)
        items = self.record_tree.get_children()
        if self._replay_index - 1 < len(items):
            self.record_tree.selection_set(items[self._replay_index - 1])
            self.record_tree.see(items[self._replay_index - 1])

        self._replay_timer_id = self.after(self._replay_interval, self._do_replay_step)

    def _on_replay_done(self):
        """回放完成"""
        self._replay_running = False
        self.replay_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)

        if self._replay_mode == '循环回放' and self._replay_queue:
            # 循环回放
            self._replay_index = 0
            self.replay_status_var.set(f'循环回放中... 0/{len(self._replay_queue)}')
            self._replay_timer_id = self.after(self._replay_interval, self._do_replay_step)
        else:
            self.replay_status_var.set(f'回放完成 ({len(self._replay_queue)} 条)')

    def _stop_replay(self):
        """停止回放"""
        self._replay_running = False
        if self._replay_timer_id:
            self.after_cancel(self._replay_timer_id)
            self._replay_timer_id = None
        self.replay_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self.replay_status_var.set('已停止')

    def destroy(self):
        self._stop_replay()
        super().destroy()

    def get_settings(self) -> dict:
        return {
            'replay_mode': self.replay_mode_var.get(),
            'replay_interval': self.replay_interval_var.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        self.replay_mode_var.set(settings.get('replay_mode', '选中回放'))
        self.replay_interval_var.set(settings.get('replay_interval', '200'))
