"""定时任务面板 - 在指定时间执行发送任务"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, time
import threading
import time as time_module
from utils.hex_utils import hex_str_to_bytes, bytes_to_hex_str
from utils.context_menu import add_entry_context_menu
from ui.status_bus import StatusBus


class SchedulerPanel(ttk.LabelFrame):
    """定时任务面板"""

    def __init__(self, parent, on_send=None, log_panel=None):
        super().__init__(parent, text=' 定时任务 ', padding=8)
        self._on_send = on_send
        self._log_panel = log_panel
        self._tasks = []  # [{name, time, data, repeat, enabled, ...}]
        self._running = False
        self._thread = None
        self._build_ui()

    def _build_ui(self):
        # 任务列表
        list_frame = ttk.LabelFrame(self, text=' 任务列表 ', padding=4)
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('enabled', 'name', 'time', 'data', 'repeat')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=5)
        self.tree.heading('enabled', text='启用')
        self.tree.heading('name', text='任务名')
        self.tree.heading('time', text='执行时间')
        self.tree.heading('data', text='数据(Hex)')
        self.tree.heading('repeat', text='重复')

        self.tree.column('enabled', width=40, minwidth=30, anchor=tk.CENTER)
        self.tree.column('name', width=80, minwidth=60)
        self.tree.column('time', width=80, minwidth=60)
        self.tree.column('data', width=150, minwidth=80)
        self.tree.column('repeat', width=50, minwidth=40, anchor=tk.CENTER)

        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        tree_scroll.grid(row=0, column=1, sticky='ns')
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.tree.bind('<Double-Button-1>', self._on_double_click)

        # 添加任务区域
        add_frame = ttk.LabelFrame(self, text=' 添加任务 ', padding=6)
        add_frame.pack(fill=tk.X, pady=(4, 0))

        # 第一行
        row1 = ttk.Frame(add_frame)
        row1.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(row1, text='任务名:').pack(side=tk.LEFT)
        self.name_var = tk.StringVar(value='任务1')
        self.name_entry = ttk.Entry(row1, textvariable=self.name_var, width=12)
        self.name_entry.pack(side=tk.LEFT, padx=(4, 12))
        add_entry_context_menu(self.name_entry)

        ttk.Label(row1, text='执行时间:').pack(side=tk.LEFT)
        self.hour_var = tk.StringVar(value='00')
        self.hour_entry = ttk.Entry(row1, textvariable=self.hour_var, width=3)
        self.hour_entry.pack(side=tk.LEFT, padx=(4, 0))
        add_entry_context_menu(self.hour_entry)
        ttk.Label(row1, text=':').pack(side=tk.LEFT)
        self.min_var = tk.StringVar(value='00')
        self.min_entry = ttk.Entry(row1, textvariable=self.min_var, width=3)
        self.min_entry.pack(side=tk.LEFT)
        add_entry_context_menu(self.min_entry)
        ttk.Label(row1, text=':').pack(side=tk.LEFT)
        self.sec_var = tk.StringVar(value='00')
        self.sec_entry = ttk.Entry(row1, textvariable=self.sec_var, width=3)
        self.sec_entry.pack(side=tk.LEFT)
        add_entry_context_menu(self.sec_entry)

        # 第二行
        row2 = ttk.Frame(add_frame)
        row2.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(row2, text='数据 (Hex):').pack(side=tk.LEFT)
        self.data_var = tk.StringVar(value='AA 55 00 01 FE')
        self.data_entry = ttk.Entry(row2, textvariable=self.data_var,
                                    font=('Courier New', 10))
        self.data_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 8))
        add_entry_context_menu(self.data_entry)

        self.repeat_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text='每天重复', variable=self.repeat_var).pack(side=tk.LEFT)

        # 按钮
        btn_frame = ttk.Frame(add_frame)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text='➕ 添加任务', command=self._add_task, width=10).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text='🗑 删除任务', command=self._delete_task, width=10).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(btn_frame, text='⏹ 停止所有', command=self._stop_all, width=10).pack(side=tk.RIGHT)

        self.start_btn = ttk.Button(btn_frame, text='▶ 启动调度', command=self._toggle_scheduler, width=10)
        self.start_btn.pack(side=tk.RIGHT, padx=(0, 4))

        self.status_var = tk.StringVar(value='已停止')
        ttk.Label(btn_frame, textvariable=self.status_var, foreground='gray').pack(side=tk.RIGHT, padx=(8, 0))

    def _add_task(self):
        """添加任务"""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning('提示', '请输入任务名')
            return

        try:
            hour = int(self.hour_var.get())
            minute = int(self.min_var.get())
            second = int(self.sec_var.get())
        except ValueError:
            messagebox.showerror('错误', '时间格式错误')
            return

        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            messagebox.showerror('错误', '时间超出范围')
            return

        data_hex = self.data_var.get().strip()
        if not data_hex:
            messagebox.showwarning('提示', '请输入数据')
            return

        try:
            data = hex_str_to_bytes(data_hex)
        except ValueError as e:
            messagebox.showerror('错误', f'Hex格式错误: {e}')
            return

        task = {
            'name': name,
            'hour': hour,
            'minute': minute,
            'second': second,
            'data_hex': data_hex,
            'data': data,
            'repeat': self.repeat_var.get(),
            'enabled': True,
        }
        self._tasks.append(task)
        self._refresh_list()

    def _delete_task(self):
        """删除选中的任务"""
        selected = self.tree.selection()
        if not selected:
            return
        index = self.tree.index(selected[0])
        if messagebox.askyesno('确认', f'删除任务 "{self._tasks[index]["name"]}"？'):
            self._tasks.pop(index)
            self._refresh_list()

    def _on_double_click(self, event):
        """双击切换启用状态"""
        selected = self.tree.selection()
        if not selected:
            return
        index = self.tree.index(selected[0])
        self._tasks[index]['enabled'] = not self._tasks[index]['enabled']
        self._refresh_list()

    def _refresh_list(self):
        """刷新列表"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        for task in self._tasks:
            time_str = f'{task["hour"]:02d}:{task["minute"]:02d}:{task["second"]:02d}'
            enabled = '✓' if task['enabled'] else '✗'
            repeat = '每天' if task['repeat'] else '一次'
            self.tree.insert('', tk.END, values=(
                enabled, task['name'], time_str, task['data_hex'], repeat
            ))

    def _toggle_scheduler(self):
        """切换调度器状态"""
        if self._running:
            self._stop_all()
        else:
            self._start_scheduler()

    def _start_scheduler(self):
        """启动调度器"""
        if not self._tasks:
            messagebox.showwarning('提示', '没有任务')
            return

        self._running = True
        self.start_btn.configure(text='⏹ 停止调度')
        self.status_var.set('运行中')
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        StatusBus.send('定时任务', f'已启动, {len(self._tasks)} 个任务', 'success')

        if self._log_panel:
            self._log_panel.log_info('▶ 定时调度器已启动')

    def _scheduler_loop(self):
        """调度器主循环"""
        while self._running:
            now = datetime.now()
            current_time = (now.hour, now.minute, now.second)

            for task in self._tasks:
                if not task['enabled']:
                    continue
                task_time = (task['hour'], task['minute'], task['second'])
                if current_time == task_time:
                    # 执行任务
                    if self._on_send and task['data']:
                        self._on_send(task['data'])
                    if self._log_panel:
                        self._log_panel.log_info(f'[定时任务] {task["name"]} 已执行')
                    if not task['repeat']:
                        task['enabled'] = False
                        # 刷新UI
                        self._refresh_list_async()

            time_module.sleep(1)

    def _refresh_list_async(self):
        """异步刷新列表"""
        try:
            self.winfo_toplevel().after(0, self._refresh_list)
        except Exception:
            pass

    def _stop_all(self):
        """停止所有"""
        self._running = False
        self.start_btn.configure(text='▶ 启动调度')
        self.status_var.set('已停止')
        StatusBus.send('定时任务', '已停止', 'info')

        if self._log_panel:
            self._log_panel.log_info('⏹ 定时调度器已停止')

    def destroy(self):
        self._running = False
        super().destroy()

    def get_settings(self) -> dict:
        return {
            'tasks': [{
                'name': t['name'],
                'hour': t['hour'],
                'minute': t['minute'],
                'second': t['second'],
                'data_hex': t['data_hex'],
                'repeat': t['repeat'],
                'enabled': t['enabled'],
            } for t in self._tasks],
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        tasks_data = settings.get('tasks', [])
        self._tasks = []
        for t in tasks_data:
            try:
                data = hex_str_to_bytes(t.get('data_hex', ''))
            except Exception:
                data = b''
            self._tasks.append({
                'name': t.get('name', ''),
                'hour': t.get('hour', 0),
                'minute': t.get('minute', 0),
                'second': t.get('second', 0),
                'data_hex': t.get('data_hex', ''),
                'data': data,
                'repeat': t.get('repeat', False),
                'enabled': t.get('enabled', True),
            })
        self._refresh_list()
