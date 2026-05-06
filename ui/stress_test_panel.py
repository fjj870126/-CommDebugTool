"""压力测试面板 - 批量发送数据包，测试通信稳定性（集成数据生成器）"""

import tkinter as tk
from tkinter import ttk, messagebox
import time
import threading
import random
from utils.hex_utils import hex_str_to_bytes, bytes_to_hex_str
from ui.theme import get_theme
from ui.status_bus import StatusBus


class StressTestPanel(ttk.LabelFrame):
    """压力测试面板 - 支持固定数据/递增/随机/循环模式"""

    def __init__(self, parent, on_send=None):
        super().__init__(parent, text=' 压力测试 ', padding=8)
        self._on_send = on_send
        self._on_send_silent = None  # 由外部设置静默发送回调
        self._running = False
        self._stop_flag = False
        self._thread = None
        
        # 统计
        self._sent_count = 0
        self._success_count = 0
        self._fail_count = 0
        self._start_time = 0
        
        self._build_ui()

    def _build_ui(self):
        # 数据模式
        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill=tk.X, pady=(0, 4))
        
        ttk.Label(mode_frame, text='数据模式:').pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value='固定数据')
        mode_cb = ttk.Combobox(mode_frame, textvariable=self.mode_var,
                               values=['固定数据', '递增', '递减', '随机', '循环'],
                               state='readonly', width=10)
        mode_cb.pack(side=tk.LEFT, padx=(4, 0))
        mode_cb.bind('<<ComboboxSelected>>', self._on_mode_change)

        # 固定数据
        self.fixed_frame = ttk.Frame(self)
        self.fixed_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(self.fixed_frame, text='发送数据(Hex):').pack(side=tk.LEFT)
        self.data_var = tk.StringVar(value='AA BB CC DD')
        self.data_entry = ttk.Entry(self.fixed_frame, textvariable=self.data_var, width=30)
        self.data_entry.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)

        # 递增/递减设置
        self.inc_frame = ttk.LabelFrame(self, text=' 递增/递减设置 ', padding=4)
        ttk.Label(self.inc_frame, text='起始值(Hex):').pack(side=tk.LEFT)
        self.start_var = tk.StringVar(value='00')
        ttk.Entry(self.inc_frame, textvariable=self.start_var, width=8).pack(side=tk.LEFT, padx=(4, 8))
        ttk.Label(self.inc_frame, text='步进:').pack(side=tk.LEFT)
        self.step_var = tk.StringVar(value='1')
        ttk.Entry(self.inc_frame, textvariable=self.step_var, width=6).pack(side=tk.LEFT, padx=(4, 8))
        ttk.Label(self.inc_frame, text='长度(字节):').pack(side=tk.LEFT)
        self.length_var = tk.StringVar(value='8')
        ttk.Entry(self.inc_frame, textvariable=self.length_var, width=6).pack(side=tk.LEFT, padx=(4, 0))

        # 循环设置
        self.loop_frame = ttk.LabelFrame(self, text=' 循环设置 ', padding=4)
        ttk.Label(self.loop_frame, text='循环列表(Hex,空格分隔):').pack(side=tk.LEFT)
        self.loop_var = tk.StringVar(value='00 01 02 03 04 05')
        ttk.Entry(self.loop_frame, textvariable=self.loop_var, width=30).pack(side=tk.LEFT, padx=(4, 0))

        # 参数设置
        row2 = ttk.Frame(self)
        row2.pack(fill=tk.X, pady=(0, 4))
        
        ttk.Label(row2, text='发送次数:').pack(side=tk.LEFT)
        self.count_var = tk.StringVar(value='100')
        ttk.Spinbox(row2, from_=1, to=100000, textvariable=self.count_var,
                    width=8).pack(side=tk.LEFT, padx=(2, 10))
        
        ttk.Label(row2, text='间隔(ms):').pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value='100')
        ttk.Spinbox(row2, from_=1, to=10000, textvariable=self.interval_var,
                    width=8).pack(side=tk.LEFT, padx=(2, 10))
        
        ttk.Label(row2, text='超时(ms):').pack(side=tk.LEFT)
        self.timeout_var = tk.StringVar(value='1000')
        ttk.Spinbox(row2, from_=10, to=60000, textvariable=self.timeout_var,
                    width=8).pack(side=tk.LEFT, padx=(2, 0))

        # 控制按钮
        row3 = ttk.Frame(self)
        row3.pack(fill=tk.X, pady=(0, 4))
        
        self.start_btn = ttk.Button(row3, text='▶ 开始', command=self._start_test, width=10)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 4))
        
        self.stop_btn = ttk.Button(row3, text='■ 停止', command=self._stop_test,
                                   state=tk.DISABLED, width=10)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 4))
        
        ttk.Button(row3, text='重置', command=self._reset_stats, width=6).pack(side=tk.LEFT)

        # 进度条
        self.progress = ttk.Progressbar(self, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(0, 4))

        # 统计信息
        stats_frame = ttk.LabelFrame(self, text=' 测试统计 ', padding=6)
        stats_frame.pack(fill=tk.X)
        
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X)
        
        theme = get_theme()
        # 第一行
        ttk.Label(stats_grid, text='已发送:').grid(row=0, column=0, sticky=tk.W, pady=2)
        self.sent_label = ttk.Label(stats_grid, text='0', foreground=theme.color('tx'))
        self.sent_label.grid(row=0, column=1, sticky=tk.W, padx=(4, 20), pady=2)
        
        ttk.Label(stats_grid, text='成功:').grid(row=0, column=2, sticky=tk.W, pady=2)
        self.success_label = ttk.Label(stats_grid, text='0', foreground=theme.color('rx'))
        self.success_label.grid(row=0, column=3, sticky=tk.W, padx=(4, 20), pady=2)
        
        ttk.Label(stats_grid, text='失败:').grid(row=0, column=4, sticky=tk.W, pady=2)
        self.fail_label = ttk.Label(stats_grid, text='0', foreground=theme.color('info'))
        self.fail_label.grid(row=0, column=5, sticky=tk.W, padx=(4, 0), pady=2)
        
        # 第二行
        ttk.Label(stats_grid, text='耗时:').grid(row=1, column=0, sticky=tk.W, pady=2)
        self.time_label = ttk.Label(stats_grid, text='0s')
        self.time_label.grid(row=1, column=1, sticky=tk.W, padx=(4, 20), pady=2)
        
        ttk.Label(stats_grid, text='速率:').grid(row=1, column=2, sticky=tk.W, pady=2)
        self.rate_label = ttk.Label(stats_grid, text='0 包/s')
        self.rate_label.grid(row=1, column=3, sticky=tk.W, padx=(4, 20), pady=2)
        
        ttk.Label(stats_grid, text='状态:').grid(row=1, column=4, sticky=tk.W, pady=2)
        self.status_dot = ttk.Label(stats_grid, text='●', foreground=get_theme().color('gray'))
        self.status_dot.grid(row=1, column=5, sticky=tk.W, padx=(4, 0), pady=2)
        self.status_label = ttk.Label(stats_grid, text='就绪')
        self.status_label.grid(row=1, column=6, sticky=tk.W, padx=(2, 0), pady=2)

    def _on_mode_change(self, event=None):
        """切换数据模式"""
        mode = self.mode_var.get()
        self.fixed_frame.pack_forget()
        self.inc_frame.pack_forget()
        self.loop_frame.pack_forget()
        
        if mode == '固定数据':
            self.fixed_frame.pack(fill=tk.X, pady=(0, 4))
        elif mode in ('递增', '递减'):
            self.inc_frame.pack(fill=tk.X, pady=(0, 4))
        elif mode == '循环':
            self.loop_frame.pack(fill=tk.X, pady=(0, 4))
        elif mode == '随机':
            pass  # 随机模式不需要额外设置

    def _start_test(self):
        """开始压力测试"""
        # 验证参数
        try:
            hex_data = self.data_var.get().strip()
            if not hex_data:
                self.status_label.configure(text='⚠️ 请输入发送数据', foreground='red')
                self.status_dot.configure(foreground='red')
                return
            data = hex_str_to_bytes(hex_data)
            if not data:
                self.status_label.configure(text='⚠️ 无效的 Hex 数据', foreground='red')
                self.status_dot.configure(foreground='red')
                return
            
            count = int(self.count_var.get())
            interval = int(self.interval_var.get())
            timeout = int(self.timeout_var.get())
        except ValueError:
            self.status_label.configure(text='⚠️ 参数格式错误', foreground='red')
            self.status_dot.configure(foreground='red')
            return
        
        # 检查连接状态 - 使用静默发送检查
        if self._on_send_silent:
            if not self._on_send_silent(b''):
                self.status_label.configure(text='⚠️ 未连接', foreground='red')
                self.status_dot.configure(foreground='red')
                return
        elif not self._on_send:
            self.status_label.configure(text='⚠️ 未连接', foreground='red')
            self.status_dot.configure(foreground='red')
            return
        
        # 重置统计
        self._sent_count = 0
        self._success_count = 0
        self._fail_count = 0
        self._start_time = time.time()
        self._stop_flag = False
        self._running = True
        
        # 更新 UI
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.progress['maximum'] = count
        self.progress['value'] = 0
        self.status_label.configure(text='运行中...', foreground='blue')
        self.status_dot.configure(foreground='#2196F3')
        StatusBus.send('压力测试', f'发送 {count} 包', 'info')
        
        # 在后台线程中执行
        self._thread = threading.Thread(
            target=self._test_worker,
            args=(data, count, interval, timeout),
            daemon=True
        )
        self._thread.start()
        
        # 启动 UI 更新
        self._update_stats()

    def _test_worker(self, data: bytes, count: int, interval: int, timeout: int):
        """压力测试工作线程"""
        for i in range(count):
            if self._stop_flag:
                break
            
            try:
                # 优先使用静默发送（不弹窗），如果失败则停止测试
                if self._on_send_silent:
                    if self._on_send_silent(data):
                        self._sent_count += 1
                        self._success_count += 1
                    else:
                        self._fail_count += 1
                        self._stop_flag = True  # 未连接，停止测试
                        self.root().after(0, lambda: self.status_label.configure(
                            text='⚠️ 未连接，测试已停止', foreground='red'))
                        self.root().after(0, lambda: self.status_dot.configure(foreground='red'))
                        break
                elif self._on_send:
                    self._on_send(data)
                    self._sent_count += 1
                    self._success_count += 1
                else:
                    self._fail_count += 1
                    self._stop_flag = True  # 无发送回调，停止测试
                    self.root().after(0, lambda: self.status_label.configure(
                        text='⚠️ 未连接，测试已停止', foreground='red'))
                    self.root().after(0, lambda: self.status_dot.configure(foreground='red'))
                    break
            except Exception:
                self._fail_count += 1
            
            # 更新进度
            self.root().after(0, lambda: self.progress.step(1))
            
            # 间隔
            if interval > 0 and i < count - 1:
                time.sleep(interval / 1000.0)
        
        # 完成
        self._running = False
        self.root().after(0, self._on_test_complete)

    def _on_test_complete(self):
        """测试完成"""
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self.status_label.configure(text='完成', foreground='green')
        self.status_dot.configure(foreground='green')
        StatusBus.send('压力测试',
                       f'完成: 发送 {self._sent_count}, 成功 {self._success_count}, 失败 {self._fail_count}',
                       'success')

    def _stop_test(self):
        """停止测试"""
        self._stop_flag = True
        self.stop_btn.configure(state=tk.DISABLED)
        self.status_label.configure(text='停止中...', foreground='orange')
        self.status_dot.configure(foreground='orange')
        StatusBus.send('压力测试', '正在停止...', 'warning')

    def _update_stats(self):
        """更新统计显示"""
        if self._running or self._sent_count > 0:
            elapsed = time.time() - self._start_time
            rate = self._sent_count / elapsed if elapsed > 0 else 0
            
            self.sent_label.configure(text=str(self._sent_count))
            self.success_label.configure(text=str(self._success_count))
            self.fail_label.configure(text=str(self._fail_count))
            self.time_label.configure(text=f'{elapsed:.1f}s')
            self.rate_label.configure(text=f'{rate:.0f} 包/s')
            
            if self._running:
                self.after(200, self._update_stats)

    def _reset_stats(self):
        """重置统计"""
        self._sent_count = 0
        self._success_count = 0
        self._fail_count = 0
        self._start_time = 0
        
        self.sent_label.configure(text='0')
        self.success_label.configure(text='0')
        self.fail_label.configure(text='0')
        self.time_label.configure(text='0s')
        self.rate_label.configure(text='0 包/s')
        self.progress['value'] = 0
        self.status_label.configure(text='就绪', foreground=get_theme().color('gray'))
        self.status_dot.configure(foreground=get_theme().color('gray'))

    def destroy(self):
        self._running = False
        self._stop_flag = True
        super().destroy()

    def root(self):
        """获取根窗口"""
        w = self
        while w.master:
            w = w.master
        return w

    def get_settings(self) -> dict:
        return {
            'data': self.data_var.get(),
            'count': self.count_var.get(),
            'interval': self.interval_var.get(),
            'timeout': self.timeout_var.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        if 'data' in settings:
            self.data_var.set(settings['data'])
        if 'count' in settings:
            self.count_var.set(settings['count'])
        if 'interval' in settings:
            self.interval_var.set(settings['interval'])
        if 'timeout' in settings:
            self.timeout_var.set(settings['timeout'])
