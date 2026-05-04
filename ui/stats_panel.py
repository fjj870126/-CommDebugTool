"""数据统计面板 - 收发字节数、频率、错误率统计"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import time
from ui.theme import get_theme


class StatsPanel(ttk.LabelFrame):
    """数据统计面板"""

    def __init__(self, parent):
        super().__init__(parent, text=' 数据统计 ', padding=8)
        
        # 统计数据
        self._tx_count = 0      # 发送包数
        self._rx_count = 0      # 接收包数
        self._tx_bytes = 0      # 发送字节数
        self._rx_bytes = 0      # 接收字节数
        self._tx_errors = 0     # 发送错误数
        self._rx_errors = 0     # 接收错误数
        
        # 频率统计（最近1分钟内的数据）
        self._tx_history = []   # [(timestamp, bytes), ...]
        self._rx_history = []   # [(timestamp, bytes), ...]
        
        self._running = True
        self._build_ui()
        self._start_updater()

    def _build_ui(self):
        # 使用 grid 布局，两列
        self.columnconfigure(1, weight=1)
        
        row = 0
        theme = get_theme()
        # 标题行
        ttk.Label(self, text='', font=('', 9, 'bold')).grid(row=row, column=0, sticky=tk.W, pady=(0, 4))
        ttk.Label(self, text='TX', font=('', 9, 'bold'), foreground=theme.color('tx')).grid(
            row=row, column=1, sticky=tk.W, pady=(0, 4))
        ttk.Label(self, text='RX', font=('', 9, 'bold'), foreground=theme.color('rx')).grid(
            row=row, column=2, sticky=tk.W, padx=(10, 0), pady=(0, 4))
        
        row += 1
        ttk.Label(self, text='包数:').grid(row=row, column=0, sticky=tk.W, pady=2)
        self._tx_count_label = ttk.Label(self, text='0', foreground=theme.color('tx'))
        self._tx_count_label.grid(row=row, column=1, sticky=tk.W, pady=2)
        self._rx_count_label = ttk.Label(self, text='0', foreground=theme.color('rx'))
        self._rx_count_label.grid(row=row, column=2, sticky=tk.W, padx=(10, 0), pady=2)
        
        row += 1
        ttk.Label(self, text='字节数:').grid(row=row, column=0, sticky=tk.W, pady=2)
        self._tx_bytes_label = ttk.Label(self, text='0 B', foreground=theme.color('tx'))
        self._tx_bytes_label.grid(row=row, column=1, sticky=tk.W, pady=2)
        self._rx_bytes_label = ttk.Label(self, text='0 B', foreground=theme.color('rx'))
        self._rx_bytes_label.grid(row=row, column=2, sticky=tk.W, padx=(10, 0), pady=2)
        
        row += 1
        ttk.Label(self, text='速率:').grid(row=row, column=0, sticky=tk.W, pady=2)
        self._tx_rate_label = ttk.Label(self, text='0 B/s', foreground=theme.color('tx'))
        self._tx_rate_label.grid(row=row, column=1, sticky=tk.W, pady=2)
        self._rx_rate_label = ttk.Label(self, text='0 B/s', foreground=theme.color('rx'))
        self._rx_rate_label.grid(row=row, column=2, sticky=tk.W, padx=(10, 0), pady=2)
        
        row += 1
        ttk.Label(self, text='错误:').grid(row=row, column=0, sticky=tk.W, pady=2)
        self._tx_err_label = ttk.Label(self, text='0', foreground=theme.color('info'))
        self._tx_err_label.grid(row=row, column=1, sticky=tk.W, pady=2)
        self._rx_err_label = ttk.Label(self, text='0', foreground=theme.color('info'))
        self._rx_err_label.grid(row=row, column=2, sticky=tk.W, padx=(10, 0), pady=2)
        
        row += 1
        ttk.Separator(self, orient=tk.HORIZONTAL).grid(
            row=row, column=0, columnspan=3, sticky=tk.EW, pady=(6, 2))
        
        row += 1
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=row, column=0, columnspan=3, sticky=tk.EW, pady=(2, 0))
        ttk.Button(btn_frame, text='重置统计', command=self.reset, width=10).pack(side=tk.LEFT)

    def _format_bytes(self, n: int) -> str:
        """格式化字节数显示"""
        if n < 1024:
            return f'{n} B'
        elif n < 1024 * 1024:
            return f'{n / 1024:.1f} KB'
        else:
            return f'{n / 1024 / 1024:.1f} MB'

    def _format_rate(self, bytes_per_sec: float) -> str:
        """格式化速率显示"""
        if bytes_per_sec < 1024:
            return f'{bytes_per_sec:.0f} B/s'
        elif bytes_per_sec < 1024 * 1024:
            return f'{bytes_per_sec / 1024:.1f} KB/s'
        else:
            return f'{bytes_per_sec / 1024 / 1024:.1f} MB/s'

    def record_tx(self, data: bytes):
        """记录发送数据"""
        self._tx_count += 1
        self._tx_bytes += len(data)
        now = time.time()
        self._tx_history.append((now, len(data)))
        self._update_display()

    def record_rx(self, data: bytes):
        """记录接收数据"""
        self._rx_count += 1
        self._rx_bytes += len(data)
        now = time.time()
        self._rx_history.append((now, len(data)))
        self._update_display()

    def record_tx_error(self):
        """记录发送错误"""
        self._tx_errors += 1
        self._update_display()

    def record_rx_error(self):
        """记录接收错误"""
        self._rx_errors += 1
        self._update_display()

    def _update_display(self):
        """更新显示"""
        self._tx_count_label.configure(text=str(self._tx_count))
        self._rx_count_label.configure(text=str(self._rx_count))
        self._tx_bytes_label.configure(text=self._format_bytes(self._tx_bytes))
        self._rx_bytes_label.configure(text=self._format_bytes(self._rx_bytes))
        self._tx_err_label.configure(text=str(self._tx_errors))
        self._rx_err_label.configure(text=str(self._rx_errors))

    def _update_rate(self):
        """更新速率显示（每秒调用）"""
        now = time.time()
        cutoff = now - 60  # 只统计最近60秒
        
        # 清理过期数据
        self._tx_history = [(t, b) for t, b in self._tx_history if t > cutoff]
        self._rx_history = [(t, b) for t, b in self._rx_history if t > cutoff]
        
        # 计算速率
        tx_bytes = sum(b for _, b in self._tx_history)
        rx_bytes = sum(b for _, b in self._rx_history)
        
        self._tx_rate_label.configure(text=self._format_rate(tx_bytes / 60))
        self._rx_rate_label.configure(text=self._format_rate(rx_bytes / 60))

    def _start_updater(self):
        """启动定时更新"""
        if self._running:
            self._update_rate()
            self.after(1000, self._start_updater)

    def reset(self):
        """重置所有统计"""
        self._tx_count = 0
        self._rx_count = 0
        self._tx_bytes = 0
        self._rx_bytes = 0
        self._tx_errors = 0
        self._rx_errors = 0
        self._tx_history.clear()
        self._rx_history.clear()
        self._update_display()
        self._tx_rate_label.configure(text='0 B/s')
        self._rx_rate_label.configure(text='0 B/s')

    def destroy(self):
        self._running = False
        super().destroy()

    def get_settings(self) -> dict:
        return {}

    def load_settings(self, settings: dict):
        pass
