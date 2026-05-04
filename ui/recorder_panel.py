"""操作录制面板 - 录制用户操作并生成可执行的 Python 脚本"""

import os
import json
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime


class RecorderPanel(ttk.LabelFrame):
    """操作录制面板 - 录制用户操作并生成脚本"""

    def __init__(self, parent, on_send=None, log_panel=None):
        super().__init__(parent, text=' 操作录制 ', padding=8)
        self._on_send = on_send
        self._log_panel = log_panel
        self._recording = False
        self._records = []  # [(timestamp, action, data), ...]
        self._start_time = 0
        self._build_ui()

    def _build_ui(self):
        # 工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 4))

        self.record_btn = ttk.Button(toolbar, text='● 开始录制', command=self._toggle_record, width=12)
        self.record_btn.pack(side=tk.LEFT, padx=(0, 4))

        ttk.Button(toolbar, text='▶ 回放', command=self._playback, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text='⏹ 停止回放', command=self._stop_playback, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text='📤 导出脚本', command=self._export_script, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text='🗑 清空', command=self._clear_records, width=6).pack(side=tk.RIGHT, padx=2)

        # 录制状态
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, pady=(0, 4))

        self._status_indicator = tk.Canvas(status_frame, width=12, height=12,
                                           highlightthickness=0)
        self._status_indicator.pack(side=tk.LEFT, padx=(0, 4))
        self._draw_indicator('gray')

        self._status_label = ttk.Label(status_frame, text='就绪', foreground='gray')
        self._status_label.pack(side=tk.LEFT)

        self._count_label = ttk.Label(status_frame, text='已录制: 0 条')
        self._count_label.pack(side=tk.RIGHT)

        # 录制列表
        list_frame = ttk.LabelFrame(self, text=' 录制记录 ', padding=4)
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('time', 'action', 'data')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        self.tree.heading('time', text='时间偏移')
        self.tree.heading('action', text='操作')
        self.tree.heading('data', text='数据')

        self.tree.column('time', width=80, minwidth=60, anchor=tk.CENTER)
        self.tree.column('action', width=80, minwidth=60, anchor=tk.CENTER)
        self.tree.column('data', width=300, minwidth=100, anchor=tk.W)

        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 右键菜单
        menu = tk.Menu(self.tree, tearoff=0)
        menu.add_command(label='删除选中', command=self._delete_selected)
        menu.add_command(label='清空全部', command=self._clear_records)
        self.tree.bind('<Button-3>', lambda e: menu.tk_popup(e.x_root, e.y_root))
        self.tree.bind('<Control-Button-1>', lambda e: menu.tk_popup(e.x_root, e.y_root))

    def _draw_indicator(self, color: str):
        """绘制状态指示灯"""
        self._status_indicator.delete('all')
        self._status_indicator.create_oval(2, 2, 10, 10, fill=color, outline=color)

    def _toggle_record(self):
        """切换录制状态"""
        if not self._recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        """开始录制"""
        self._recording = True
        self._records = []
        self._start_time = time.time()
        self.record_btn.configure(text='■ 停止录制')
        self._draw_indicator('red')
        self._status_label.configure(text='录制中...', foreground='red')
        self._refresh_list()
        if self._log_panel:
            self._log_panel.log_info('[录制] 开始录制操作')

    def _stop_recording(self):
        """停止录制"""
        self._recording = False
        self.record_btn.configure(text='● 开始录制')
        self._draw_indicator('gray')
        self._status_label.configure(text=f'已停止 (共 {len(self._records)} 条)', foreground='gray')
        if self._log_panel:
            self._log_panel.log_info(f'[录制] 录制完成，共 {len(self._records)} 条操作')

    def record_action(self, action: str, data: str = ''):
        """记录一个操作（供外部调用）"""
        if not self._recording:
            return
        timestamp = time.time() - self._start_time
        self._records.append((timestamp, action, data))
        self._refresh_list()
        self._count_label.configure(text=f'已录制: {len(self._records)} 条')

    def record_send(self, data: bytes):
        """记录发送操作（供外部调用）"""
        if not self._recording:
            return
        hex_str = data.hex().upper()
        # 格式化显示
        formatted = ' '.join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))
        self.record_action('发送', formatted)

    def record_receive(self, data: bytes):
        """记录接收操作（供外部调用）"""
        if not self._recording:
            return
        hex_str = data.hex().upper()
        formatted = ' '.join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))
        self.record_action('接收', formatted)

    def _playback(self):
        """回放录制的操作"""
        if not self._records:
            messagebox.showwarning('提示', '没有录制的操作')
            return
        
        if not self._on_send:
            messagebox.showwarning('提示', '未设置发送回调')
            return

        # 在后台线程中回放
        import threading
        self._playback_stop = False
        thread = threading.Thread(target=self._do_playback, daemon=True)
        thread.start()

    def _do_playback(self):
        """执行回放"""
        try:
            for i, (timestamp, action, data) in enumerate(self._records):
                if self._playback_stop:
                    break
                
                # 计算等待时间
                if i > 0:
                    wait_ms = int((timestamp - self._records[i-1][0]) * 1000)
                    if wait_ms > 0:
                        import time as _time
                        _time.sleep(wait_ms / 1000.0)
                
                if action == '发送' and data:
                    # 解析 Hex 数据并发送
                    try:
                        hex_str = data.replace(' ', '')
                        raw_data = bytes.fromhex(hex_str)
                        self._on_send(raw_data)
                    except Exception:
                        pass
                
                # 更新 UI
                self.root().after(0, lambda i=i: self._highlight_row(i))
            
            if not self._playback_stop:
                self.root().after(0, lambda: self._log_panel.log_info('[录制] 回放完成'))
        except Exception as e:
            self.root().after(0, lambda: self._log_panel.log_info(f'[录制] 回放失败: {e}'))

    def _stop_playback(self):
        """停止回放"""
        self._playback_stop = True
        if self._log_panel:
            self._log_panel.log_info('[录制] 回放已停止')

    def _highlight_row(self, index: int):
        """高亮当前回放的行"""
        # 清除之前的高亮
        for item in self.tree.get_children():
            self.tree.item(item, tags=())
        
        # 高亮当前行
        children = self.tree.get_children()
        if 0 <= index < len(children):
            self.tree.selection_set(children[index])
            self.tree.see(children[index])

    def _export_script(self):
        """导出为 Python 脚本"""
        if not self._records:
            messagebox.showwarning('提示', '没有录制的操作')
            return

        filepath = filedialog.asksaveasfilename(
            title='导出脚本',
            defaultextension='.py',
            filetypes=[('Python 脚本', '*.py'), ('所有文件', '*.*')]
        )
        if not filepath:
            return

        try:
            script = self._generate_script()
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(script)
            messagebox.showinfo('成功', f'脚本已导出到:\n{filepath}')
            if self._log_panel:
                self._log_panel.log_info(f'[录制] 脚本已导出: {filepath}')
        except Exception as e:
            messagebox.showerror('导出失败', str(e))

    def _generate_script(self) -> str:
        """生成 Python 脚本"""
        lines = []
        lines.append('#!/usr/bin/env python3')
        lines.append('# -*- coding: utf-8 -*-')
        lines.append(f'# 自动生成的测试脚本')
        lines.append(f'# 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        lines.append(f'# 操作数: {len(self._records)}')
        lines.append('')
        lines.append('')
        lines.append('def send(data):')
        lines.append('    """发送数据 - 请替换为实际的发送函数"""')
        lines.append('    print(f"发送: {data.hex().upper()}")')
        lines.append('')
        lines.append('')
        lines.append('def wait(ms):')
        lines.append('    """等待指定毫秒"""')
        lines.append('    import time')
        lines.append('    time.sleep(ms / 1000.0)')
        lines.append('')
        lines.append('')
        lines.append('def log(msg):')
        lines.append('    """输出日志"""')
        lines.append('    print(f"[LOG] {msg}")')
        lines.append('')
        lines.append('')
        lines.append('# ===== 测试流程 =====')
        lines.append('log("开始测试...")')
        lines.append('')

        for i, (timestamp, action, data) in enumerate(self._records):
            if i > 0:
                wait_ms = int((timestamp - self._records[i-1][0]) * 1000)
                if wait_ms > 0:
                    lines.append(f'wait({wait_ms})  # 等待 {wait_ms}ms')
            
            if action == '发送' and data:
                hex_str = data.replace(' ', '')
                lines.append(f'send(bytes.fromhex("{hex_str}"))  # 发送: {data}')
            elif action == '接收' and data:
                hex_str = data.replace(' ', '')
                lines.append(f'# 接收: {data}')
                lines.append(f'# assert_eq(received, bytes.fromhex("{hex_str}"))')

        lines.append('')
        lines.append('log("测试完成!")')
        return '\n'.join(lines)

    def _clear_records(self):
        """清空录制记录"""
        if self._records and messagebox.askyesno('确认', '确定要清空所有录制记录吗？'):
            self._records = []
            self._refresh_list()
            self._count_label.configure(text='已录制: 0 条')
            if self._log_panel:
                self._log_panel.log_info('[录制] 已清空录制记录')

    def _delete_selected(self):
        """删除选中的记录"""
        selected = self.tree.selection()
        if not selected:
            return
        indices = [self.tree.get_children().index(item) for item in selected]
        for idx in sorted(indices, reverse=True):
            if 0 <= idx < len(self._records):
                self._records.pop(idx)
        self._refresh_list()
        self._count_label.configure(text=f'已录制: {len(self._records)} 条')

    def _refresh_list(self):
        """刷新录制列表"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for timestamp, action, data in self._records:
            time_str = f'{timestamp:.1f}s'
            self.tree.insert('', tk.END, values=(time_str, action, data))

    def root(self):
        w = self
        while w.master:
            w = w.master
        return w

    def get_settings(self) -> dict:
        return {
            'records': self._records,
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        records = settings.get('records', [])
        if records:
            self._records = [(t, a, d) for t, a, d in records]
            self._refresh_list()
            self._count_label.configure(text=f'已录制: {len(self._records)} 条')
