"""时间戳转换器 - Unix 时间戳 ↔ 可读时间互转"""

import tkinter as tk
from tkinter import ttk
import time
from datetime import datetime
from utils.context_menu import add_entry_context_menu


class TimestampPanel(ttk.LabelFrame):
    """时间戳转换器"""

    def __init__(self, parent):
        super().__init__(parent, text=' 时间戳转换器 ', padding=8)
        self._build_ui()

    def _build_ui(self):
        # ===== 当前时间 =====
        now_frame = ttk.LabelFrame(self, text=' 当前时间 ', padding=6)
        now_frame.pack(fill=tk.X, pady=(0, 8))

        now_row = ttk.Frame(now_frame)
        now_row.pack(fill=tk.X)

        self.now_label = ttk.Label(now_row, text='', font=('Courier New', 14, 'bold'))
        self.now_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(now_row, text='刷新', command=self._update_now, width=6).pack(side=tk.RIGHT)
        ttk.Button(now_row, text='复制时间戳', command=self._copy_now_timestamp, width=10).pack(side=tk.RIGHT, padx=(0, 4))

        # 每秒更新
        self._update_now()
        self._now_job = None
        self._start_clock()

        # ===== 时间戳 → 时间 =====
        ts_to_time_frame = ttk.LabelFrame(self, text=' 时间戳 → 可读时间 ', padding=6)
        ts_to_time_frame.pack(fill=tk.X, pady=(0, 8))

        row1 = ttk.Frame(ts_to_time_frame)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text='时间戳:', font=('', 12)).pack(side=tk.LEFT)
        self.ts_input_var = tk.StringVar(value=str(int(time.time())))
        self.ts_input = ttk.Entry(row1, textvariable=self.ts_input_var,
                                  font=('Courier New', 12), width=20)
        self.ts_input.pack(side=tk.LEFT, padx=(4, 8))
        add_entry_context_menu(self.ts_input)

        ttk.Button(row1, text='→ 转换', command=self._ts_to_time, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text='当前时间戳', command=self._insert_current_ts, width=10).pack(side=tk.LEFT, padx=2)

        # 时间戳精度选择
        self.ts_unit = tk.StringVar(value='秒')
        ttk.Radiobutton(row1, text='秒(10位)', variable=self.ts_unit,
                        value='秒').pack(side=tk.LEFT, padx=(8, 2))
        ttk.Radiobutton(row1, text='毫秒(13位)', variable=self.ts_unit,
                        value='毫秒').pack(side=tk.LEFT, padx=2)

        # 结果
        result_frame1 = ttk.Frame(ts_to_time_frame)
        result_frame1.pack(fill=tk.X, pady=2)

        self.ts_result_var = tk.StringVar(value='')
        self.ts_result = ttk.Entry(result_frame1, textvariable=self.ts_result_var,
                                   font=('Courier New', 12), state='readonly')
        self.ts_result.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(result_frame1, text='复制', command=lambda: self._copy_text(self.ts_result_var.get()), width=6).pack(side=tk.LEFT, padx=(4, 0))

        # 多种格式显示
        self.ts_formats_var = tk.StringVar(value='')
        self.ts_formats_label = ttk.Label(ts_to_time_frame, textvariable=self.ts_formats_var,
                                          font=('Courier New', 10), foreground='gray')
        self.ts_formats_label.pack(anchor=tk.W, pady=(2, 0))

        # 绑定输入变化自动转换
        self.ts_input_var.trace_add('write', lambda *args: self._ts_to_time())

        # ===== 时间 → 时间戳 =====
        time_to_ts_frame = ttk.LabelFrame(self, text=' 可读时间 → 时间戳 ', padding=6)
        time_to_ts_frame.pack(fill=tk.X, pady=(0, 8))

        row2 = ttk.Frame(time_to_ts_frame)
        row2.pack(fill=tk.X, pady=2)

        ttk.Label(row2, text='日期时间:', font=('', 12)).pack(side=tk.LEFT)
        self.dt_input_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.dt_input = ttk.Entry(row2, textvariable=self.dt_input_var,
                                  font=('Courier New', 12), width=25)
        self.dt_input.pack(side=tk.LEFT, padx=(4, 8))
        add_entry_context_menu(self.dt_input)

        ttk.Button(row2, text='→ 转换', command=self._time_to_ts, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(row2, text='当前时间', command=self._insert_current_time, width=8).pack(side=tk.LEFT, padx=2)

        # 时区选择
        self.tz_var = tk.StringVar(value='本地时区')
        ttk.Combobox(row2, textvariable=self.tz_var,
                     values=['本地时区', 'UTC'], state='readonly', width=10).pack(side=tk.LEFT, padx=(8, 0))

        # 结果
        result_frame2 = ttk.Frame(time_to_ts_frame)
        result_frame2.pack(fill=tk.X, pady=2)

        self.dt_result_var = tk.StringVar(value='')
        self.dt_result = ttk.Entry(result_frame2, textvariable=self.dt_result_var,
                                   font=('Courier New', 12), state='readonly')
        self.dt_result.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(result_frame2, text='复制', command=lambda: self._copy_text(self.dt_result_var.get()), width=6).pack(side=tk.LEFT, padx=(4, 0))

        # 绑定输入变化自动转换
        self.dt_input_var.trace_add('write', lambda *args: self._time_to_ts())

        # ===== 常用时间格式参考 =====
        ref_frame = ttk.LabelFrame(self, text=' 常用时间格式参考 ', padding=6)
        ref_frame.pack(fill=tk.X)

        ref_text = tk.Text(ref_frame, height=6, font=('Courier New', 10),
                           wrap=tk.WORD, state=tk.DISABLED)
        ref_text.pack(fill=tk.X)

        ref_content = """格式                    示例
%Y-%m-%d %H:%M:%S     2024-01-15 14:30:00
%Y/%m/%d %H:%M:%S     2024/01/15 14:30:00
%Y-%m-%dT%H:%M:%S     2024-01-15T14:30:00 (ISO 8601)
%Y-%m-%d              2024-01-15
%H:%M:%S              14:30:00
Unix 秒               1705314600
Unix 毫秒             1705314600000"""

        ref_text.configure(state=tk.NORMAL)
        ref_text.insert('1.0', ref_content)
        ref_text.configure(state=tk.DISABLED)

        # 状态栏
        self.status_var = tk.StringVar(value='就绪')
        ttk.Label(self, textvariable=self.status_var, foreground='gray').pack(anchor=tk.W, pady=(4, 0))

    def _update_now(self):
        """更新当前时间显示"""
        now = datetime.now()
        self.now_label.configure(text=now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])

    def _start_clock(self):
        """启动时钟"""
        self._update_now()
        self._now_job = self.after(100, self._start_clock)

    def _copy_now_timestamp(self):
        """复制当前时间戳"""
        ts = str(int(time.time()))
        self._copy_text(ts)
        self.status_var.set(f'已复制当前时间戳: {ts}')

    def _insert_current_ts(self):
        """插入当前时间戳"""
        self.ts_input_var.set(str(int(time.time())))

    def _insert_current_time(self):
        """插入当前时间"""
        self.dt_input_var.set(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    def _ts_to_time(self):
        """时间戳 → 可读时间"""
        raw = self.ts_input_var.get().strip()
        if not raw:
            self.ts_result_var.set('')
            self.ts_formats_var.set('')
            return

        try:
            # 解析时间戳
            ts = float(raw)
            unit = self.ts_unit.get()
            if unit == '毫秒':
                ts = ts / 1000.0

            # 转换为时间
            dt = datetime.fromtimestamp(ts)

            # 主结果
            self.ts_result_var.set(dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])

            # 多种格式
            formats = [
                dt.strftime('%Y-%m-%d %H:%M:%S'),
                dt.strftime('%Y/%m/%d %H:%M:%S'),
                dt.strftime('%Y-%m-%dT%H:%M:%S'),
                dt.strftime('%Y-%m-%d'),
                dt.strftime('%H:%M:%S'),
                dt.strftime('%A'),
            ]
            self.ts_formats_var.set(' | '.join(formats))

            self.status_var.set(f'时间戳 {raw} → {dt.strftime("%Y-%m-%d %H:%M:%S")}')

        except (ValueError, OSError, OverflowError) as e:
            self.ts_result_var.set(f'错误: {e}')
            self.ts_formats_var.set('')

    def _time_to_ts(self):
        """可读时间 → 时间戳"""
        raw = self.dt_input_var.get().strip()
        if not raw:
            self.dt_result_var.set('')
            return

        try:
            # 尝试多种格式解析
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y/%m/%d %H:%M',
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%H:%M:%S',
                '%Y%m%d%H%M%S',
                '%Y%m%d',
            ]

            dt = None
            used_format = ''
            for fmt in formats:
                try:
                    dt = datetime.strptime(raw, fmt)
                    used_format = fmt
                    break
                except ValueError:
                    continue

            if dt is None:
                self.dt_result_var.set('无法解析此时间格式')
                return

            # 转换为时间戳
            ts = dt.timestamp()
            ts_ms = int(ts * 1000)

            self.dt_result_var.set(f'秒: {int(ts)}  毫秒: {ts_ms}')

            self.status_var.set(f'时间 {raw} → 秒: {int(ts)}, 毫秒: {ts_ms} (格式: {used_format})')

        except Exception as e:
            self.dt_result_var.set(f'错误: {e}')

    def _copy_text(self, text):
        """复制文本到剪贴板"""
        if text and not text.startswith('错误'):
            try:
                self.winfo_toplevel().clipboard_clear()
                self.winfo_toplevel().clipboard_append(text)
                self.status_var.set(f'已复制: {text[:50]}')
            except Exception:
                pass

    def destroy(self):
        """销毁时停止时钟"""
        if self._now_job:
            try:
                self.after_cancel(self._now_job)
            except Exception:
                pass
        super().destroy()

    def get_settings(self) -> dict:
        return {
            'ts_unit': self.ts_unit.get(),
            'tz': self.tz_var.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        self.ts_unit.set(settings.get('ts_unit', '秒'))
        self.tz_var.set(settings.get('tz', '本地时区'))
