"""实时波形面板 - 将接收到的数据以波形图形式展示"""

import tkinter as tk
from tkinter import ttk, messagebox
from collections import deque
import math
from ui.theme import get_theme


class WaveformPanel(ttk.LabelFrame):
    """实时波形面板"""

    def __init__(self, parent):
        super().__init__(parent, text=' 实时波形 ', padding=8)
        self._data_queue = deque(maxlen=500)  # 最多保留500个数据点
        self._running = False
        self._max_value = 255
        self._min_value = 0
        self._auto_scale = True
        self._build_ui()

    def _build_ui(self):
        # 控制栏
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill=tk.X, pady=(0, 4))

        self.start_btn = ttk.Button(ctrl_frame, text='▶ 开始', command=self._toggle, width=8)
        self.start_btn.pack(side=tk.LEFT, padx=2)

        ttk.Label(ctrl_frame, text='数据点:').pack(side=tk.LEFT, padx=(8, 2))
        self.points_var = tk.IntVar(value=200)
        ttk.Spinbox(ctrl_frame, from_=50, to=500, textvariable=self.points_var,
                    width=5).pack(side=tk.LEFT)

        self.auto_scale_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ctrl_frame, text='自动缩放', variable=self.auto_scale_var,
                        command=self._on_auto_scale).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(ctrl_frame, text='最大值:').pack(side=tk.LEFT, padx=(8, 2))
        self.max_var = tk.IntVar(value=255)
        self.max_spin = ttk.Spinbox(ctrl_frame, from_=1, to=65535,
                                    textvariable=self.max_var, width=6)
        self.max_spin.pack(side=tk.LEFT)

        ttk.Button(ctrl_frame, text='清空', command=self._clear, width=6).pack(side=tk.RIGHT, padx=2)

        # 画布
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, height=150,
                                highlightthickness=1, highlightbackground='#555',
                                bg=get_theme().color('bg'))
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind('<Configure>', self._on_resize)

        # 状态信息
        info_frame = ttk.Frame(self)
        info_frame.pack(fill=tk.X, pady=(2, 0))

        theme = get_theme()
        self.info_var = tk.StringVar(value='就绪')
        ttk.Label(info_frame, textvariable=self.info_var,
                  foreground=theme.color('gray')).pack(side=tk.LEFT)

        self.value_var = tk.StringVar(value='')
        ttk.Label(info_frame, textvariable=self.value_var,
                  foreground=theme.color('tx')).pack(side=tk.RIGHT)

    def _toggle(self):
        if self._running:
            self._running = False
            self.start_btn.configure(text='▶ 开始')
        else:
            self._running = True
            self.start_btn.configure(text='⏸ 暂停')
            self._draw()

    def _on_auto_scale(self):
        self._auto_scale = self.auto_scale_var.get()
        self.max_spin.configure(state='disabled' if self._auto_scale else 'normal')

    def _on_resize(self, event):
        if self._data_queue:
            self._draw()

    def add_data(self, data: bytes):
        """添加接收到的数据到波形"""
        if not data:
            return
        # 取第一个字节作为波形数据点
        for byte in data:
            self._data_queue.append(byte)
        if self._running:
            self._draw()

    def _draw(self):
        """绘制波形"""
        if not self._data_queue:
            return

        self.canvas.delete('waveform')

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width < 10 or height < 10:
            return

        data = list(self._data_queue)
        points_to_show = min(self.points_var.get(), len(data))
        if points_to_show < 2:
            return

        # 取最后 N 个点
        data = data[-points_to_show:]

        # 自动缩放
        if self._auto_scale and data:
            data_min = min(data)
            data_max = max(data)
            if data_max > data_min:
                self._min_value = data_min
                self._max_value = data_max
            else:
                self._min_value = 0
                self._max_value = max(data_max, 1)
        else:
            self._min_value = 0
            self._max_value = self.max_var.get()

        value_range = self._max_value - self._min_value
        if value_range <= 0:
            value_range = 1

        # 绘制网格
        self._draw_grid(width, height)

        # 绘制波形
        margin = 20
        draw_width = width - margin * 2
        draw_height = height - margin * 2

        points = []
        for i, val in enumerate(data):
            x = margin + (i / (len(data) - 1)) * draw_width
            y = margin + draw_height - ((val - self._min_value) / value_range) * draw_height
            points.extend([x, y])

        if len(points) >= 4:
            self.canvas.create_line(points, fill=get_theme().color('tx'), width=1.5, tags='waveform')

        # 显示当前值
        if data:
            current_val = data[-1]
            self.value_var.set(f'当前值: {current_val} (0x{current_val:02X})')

        # 更新信息
        self.info_var.set(f'数据点: {len(data)} | 范围: {self._min_value}-{self._max_value}')

    def _draw_grid(self, width, height):
        """绘制网格线"""
        self.canvas.delete('grid')
        margin = 20
        draw_width = width - margin * 2
        draw_height = height - margin * 2

        # 水平网格线
        grid_color = '#333'
        for i in range(5):
            y = margin + (i / 4) * draw_height
            self.canvas.create_line(margin, y, width - margin, y,
                                    fill=grid_color, dash=(2, 4), tags='grid')
            # 刻度值
            val = self._max_value - (i / 4) * (self._max_value - self._min_value)
            self.canvas.create_text(margin - 4, y, text=str(int(val)),
                                    anchor=tk.E, fill='#888', font=('', 8), tags='grid')

        # 垂直网格线
        for i in range(9):
            x = margin + (i / 8) * draw_width
            self.canvas.create_line(x, margin, x, height - margin,
                                    fill=grid_color, dash=(2, 4), tags='grid')

        # 边框
        self.canvas.create_rectangle(margin, margin, width - margin, height - margin,
                                     outline='#555', tags='grid')

    def _clear(self):
        """清空数据"""
        self._data_queue.clear()
        self.canvas.delete('all')
        self.value_var.set('')
        self.info_var.set('已清空')

    def destroy(self):
        self._running = False
        super().destroy()

    def get_settings(self) -> dict:
        return {
            'points': self.points_var.get(),
            'auto_scale': self.auto_scale_var.get(),
            'max_value': self.max_var.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        if 'points' in settings:
            self.points_var.set(settings['points'])
        if 'auto_scale' in settings:
            self.auto_scale_var.set(settings['auto_scale'])
            self._auto_scale = settings['auto_scale']
            self.max_spin.configure(state='disabled' if self._auto_scale else 'normal')
        if 'max_value' in settings:
            self.max_var.set(settings['max_value'])
