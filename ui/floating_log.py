"""收发日志浮动面板 - 支持多窗口独立浮动、实时数据同步、可拖拽定位、自适应缩放显示"""

import tkinter as tk
from tkinter import ttk
import time
import threading
from collections import deque
from datetime import datetime
from typing import Optional, Callable, Deque, List, Tuple


class LogEntry:
    """单条日志条目"""
    
    def __init__(self, timestamp: float, direction: str, data: bytes, 
                 hex_str: str, level: str = 'info'):
        self.timestamp = timestamp
        self.time_str = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:12]
        self.direction = direction  # 'TX' 或 'RX'
        self.data = data
        self.hex_str = hex_str
        self.level = level  # 'info', 'warning', 'error'
        self.ascii_str = self._to_ascii(data)
    
    @staticmethod
    def _to_ascii(data: bytes) -> str:
        """将字节转换为可读ASCII字符串"""
        result = []
        for b in data:
            if 32 <= b <= 126:
                result.append(chr(b))
            else:
                result.append('.')
        return ''.join(result)


class FloatingLogPanel(tk.Toplevel):
    """收发日志浮动面板 - 独立窗口，支持拖拽、缩放、过滤"""
    
    # 类变量：所有实例共享的日志数据
    _shared_logs: Deque[LogEntry] = deque(maxlen=5000)
    _shared_summary: dict = {'tx_count': 0, 'rx_count': 0, 'tx_bytes': 0, 'rx_bytes': 0}
    _shared_lock = threading.Lock()
    _instances: List['FloatingLogPanel'] = []
    _update_timer_id = None
    
    def __init__(self, parent=None, title: str = '收发日志', 
                 filter_level: str = 'all',
                 on_send: Optional[Callable] = None):
        super().__init__(parent)
        
        self.title(title)
        self._filter_level = filter_level
        self._on_send = on_send
        
        # 窗口属性
        self.overrideredirect(True)  # 无边框
        self.attributes('-topmost', True)
        self.configure(bg='#2b2b2b')
        
        # 窗口尺寸和位置
        self._window_width = 520
        self._window_height = 380
        self._min_width = 300
        self._min_height = 200
        
        # 拖拽相关
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_start_win_x = 0
        self._drag_start_win_y = 0
        self._is_dragging = False
        self._resize_mode = None
        self._resize_start_x = 0
        self._resize_start_y = 0
        self._resize_start_w = 0
        self._resize_start_h = 0
        
        # 边缘吸附
        self._snap_margin = 20
        
        # 显示模式
        self._display_mode = 'detail'  # 'detail' 或 'summary'
        
        # 构建UI
        self._build_ui()
        
        # 设置窗口大小和位置
        self.geometry(f'{self._window_width}x{self._window_height}+{self._calc_x()}+{self._calc_y()}')
        
        # 注册实例
        with FloatingLogPanel._shared_lock:
            FloatingLogPanel._instances.append(self)
        
        # 启动定时更新
        self._start_update_timer()
        
        # 绑定关闭事件
        self.protocol('WM_DELETE_WINDOW', self._on_close)
        
        # 绑定键盘事件
        self.bind('<Escape>', lambda e: self._on_close())
        self.bind('<Control-f>', lambda e: self._toggle_filter())
        self.bind('<Control-l>', lambda e: self._clear_logs())
        self.bind('<Control-m>', lambda e: self._toggle_display_mode())
    
    def _calc_x(self) -> int:
        """计算初始X位置（右侧）"""
        try:
            screen_width = self.winfo_screenwidth()
            return screen_width - self._window_width - 20
        except:
            return 800
    
    def _calc_y(self) -> int:
        """计算初始Y位置"""
        try:
            screen_height = self.winfo_screenheight()
            return screen_height - self._window_height - 80
        except:
            return 400
    
    def _build_ui(self):
        """构建UI"""
        # 主容器
        self._container = tk.Frame(self, bg='#2b2b2b')
        self._container.pack(fill=tk.BOTH, expand=True)
        
        # === 标题栏（可拖拽） ===
        self._title_bar = tk.Frame(self._container, bg='#1e1e1e', height=28)
        self._title_bar.pack(fill=tk.X)
        self._title_bar.pack_propagate(False)
        
        # 标题文字
        self._title_label = tk.Label(
            self._title_bar, text='📡 收发日志', 
            bg='#1e1e1e', fg='#cccccc', font=('Helvetica', 10, 'bold'),
            anchor=tk.W
        )
        self._title_label.pack(side=tk.LEFT, padx=(8, 0))
        
        # 统计信息
        self._stats_label = tk.Label(
            self._title_bar, text='TX:0 RX:0', 
            bg='#1e1e1e', fg='#888888', font=('Helvetica', 8),
            anchor=tk.W
        )
        self._stats_label.pack(side=tk.LEFT, padx=(12, 0))
        
        # 标题栏按钮
        btn_frame = tk.Frame(self._title_bar, bg='#1e1e1e')
        btn_frame.pack(side=tk.RIGHT, padx=(0, 4))
        
        # 模式切换按钮
        self._mode_btn = tk.Label(
            btn_frame, text='📊', bg='#1e1e1e', fg='#888888',
            font=('Helvetica', 10), cursor='hand2'
        )
        self._mode_btn.pack(side=tk.LEFT, padx=(0, 2))
        self._mode_btn.bind('<Button-1>', lambda e: self._toggle_display_mode())
        self._create_tooltip(self._mode_btn, '切换显示模式 (Ctrl+M)')
        
        # 清空按钮
        clear_btn = tk.Label(
            btn_frame, text='🗑', bg='#1e1e1e', fg='#888888',
            font=('Helvetica', 10), cursor='hand2'
        )
        clear_btn.pack(side=tk.LEFT, padx=(0, 2))
        clear_btn.bind('<Button-1>', lambda e: self._clear_logs())
        self._create_tooltip(clear_btn, '清空日志 (Ctrl+L)')
        
        # 关闭按钮
        close_btn = tk.Label(
            btn_frame, text='✕', bg='#1e1e1e', fg='#888888',
            font=('Helvetica', 10, 'bold'), cursor='hand2'
        )
        close_btn.pack(side=tk.LEFT, padx=(2, 0))
        close_btn.bind('<Button-1>', lambda e: self._on_close())
        self._create_tooltip(close_btn, '关闭 (Esc)')
        
        # 绑定拖拽事件到标题栏
        for widget in (self._title_bar, self._title_label, self._stats_label):
            widget.bind('<Button-1>', self._on_drag_start)
            widget.bind('<B1-Motion>', self._on_drag_motion)
            widget.bind('<ButtonRelease-1>', self._on_drag_end)
        
        # === 过滤工具栏 ===
        self._filter_bar = tk.Frame(self._container, bg='#333333', height=24)
        self._filter_bar.pack(fill=tk.X)
        self._filter_bar.pack_propagate(False)
        
        # 过滤按钮
        self._filter_btns = {}
        for level, label, color in [
            ('all', '全部', '#cccccc'),
            ('info', '信息', '#4ec9b0'),
            ('warning', '警告', '#ce9178'),
            ('error', '错误', '#f44747'),
        ]:
            btn = tk.Label(
                self._filter_bar, text=label, bg='#333333', fg=color,
                font=('Helvetica', 8), cursor='hand2', padx=6
            )
            btn.pack(side=tk.LEFT, padx=(2, 0))
            btn.bind('<Button-1>', lambda e, l=level: self._set_filter(l))
            self._filter_btns[level] = btn
        
        # 高亮当前过滤
        self._highlight_filter()
        
        # 搜索框
        tk.Label(self._filter_bar, text='🔍', bg='#333333', fg='#888888',
                 font=('Helvetica', 8)).pack(side=tk.RIGHT, padx=(0, 2))
        self._search_var = tk.StringVar()
        self._search_var.trace('w', lambda *a: self._refresh_display())
        search_entry = tk.Entry(
            self._filter_bar, textvariable=self._search_var,
            bg='#3c3c3c', fg='#cccccc', insertbackground='#cccccc',
            relief=tk.FLAT, font=('Helvetica', 8), width=12
        )
        search_entry.pack(side=tk.RIGHT, padx=(0, 4), pady=2)
        search_entry.bind('<FocusIn>', lambda e: search_entry.configure(bg='#4c4c4c'))
        search_entry.bind('<FocusOut>', lambda e: search_entry.configure(bg='#3c3c3c'))
        
        # === 日志显示区域 ===
        self._log_frame = tk.Frame(self._container, bg='#2b2b2b')
        self._log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Canvas和Scrollbar用于滚动
        self._canvas = tk.Canvas(self._log_frame, bg='#2b2b2b', 
                                 highlightthickness=0, bd=0)
        self._scrollbar = tk.Scrollbar(self._log_frame, orient=tk.VERTICAL,
                                       command=self._canvas.yview)
        self._scrollable_frame = tk.Frame(self._canvas, bg='#2b2b2b')
        
        self._scrollable_frame.bind('<Configure>',
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox('all')))
        
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._scrollable_frame, anchor=tk.NW, 
            tags='inner_frame'
        )
        
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        
        # 绑定Canvas大小变化
        self._canvas.bind('<Configure>', self._on_canvas_configure)
        
        # 鼠标滚轮滚动
        self._canvas.bind('<Enter>', self._bind_mousewheel)
        self._canvas.bind('<Leave>', self._unbind_mousewheel)
        
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # === 底部状态栏 ===
        self._status_bar = tk.Frame(self._container, bg='#1e1e1e', height=22)
        self._status_bar.pack(fill=tk.X)
        self._status_bar.pack_propagate(False)
        
        self._status_label = tk.Label(
            self._status_bar, text='就绪 | 共 0 条', 
            bg='#1e1e1e', fg='#888888', font=('Helvetica', 8),
            anchor=tk.W
        )
        self._status_label.pack(side=tk.LEFT, padx=(8, 0))
        
        # 自动滚动开关
        self._auto_scroll_var = tk.BooleanVar(value=True)
        self._auto_scroll_btn = tk.Label(
            self._status_bar, text='📌 自动滚动', bg='#1e1e1e', fg='#4ec9b0',
            font=('Helvetica', 8), cursor='hand2'
        )
        self._auto_scroll_btn.pack(side=tk.RIGHT, padx=(0, 8))
        self._auto_scroll_btn.bind('<Button-1>', self._toggle_auto_scroll)
        
        # 绑定窗口大小调整
        self._setup_resize_handles()
    
    def _setup_resize_handles(self):
        """设置调整大小的手柄"""
        # 右下角调整手柄
        self._resize_handle = tk.Frame(self._container, bg='#555555', 
                                       width=10, height=10, cursor='bottom_right_corner')
        self._resize_handle.place(relx=1.0, rely=1.0, anchor=tk.SE)
        
        self._resize_handle.bind('<Button-1>', self._on_resize_start)
        self._resize_handle.bind('<B1-Motion>', self._on_resize_motion)
        self._resize_handle.bind('<ButtonRelease-1>', self._on_resize_end)
        
        # 底部边缘
        self._bottom_edge = tk.Frame(self._container, bg='#444444', 
                                     height=4, cursor='sb_v_double_arrow')
        self._bottom_edge.place(relx=0, rely=1.0, anchor=tk.SW, relwidth=1)
        
        self._bottom_edge.bind('<Button-1>', lambda e: self._on_resize_start(e, 's'))
        self._bottom_edge.bind('<B1-Motion>', self._on_resize_motion)
        self._bottom_edge.bind('<ButtonRelease-1>', self._on_resize_end)
        
        # 右侧边缘
        self._right_edge = tk.Frame(self._container, bg='#444444', 
                                    width=4, cursor='sb_h_double_arrow')
        self._right_edge.place(relx=1.0, rely=0, anchor=tk.NE, relheight=1)
        
        self._right_edge.bind('<Button-1>', lambda e: self._on_resize_start(e, 'e'))
        self._right_edge.bind('<B1-Motion>', self._on_resize_motion)
        self._right_edge.bind('<ButtonRelease-1>', self._on_resize_end)
    
    def _create_tooltip(self, widget, text: str):
        """创建工具提示"""
        tooltip = None
        
        def show(event):
            nonlocal tooltip
            if tooltip:
                return
            x = event.x_root + 10
            y = event.y_root + 10
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f'+{x}+{y}')
            label = tk.Label(tooltip, text=text, bg='#ffffcc', fg='#333333',
                            font=('Helvetica', 8), padx=4, pady=2)
            label.pack()
        
        def hide(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None
        
        widget.bind('<Enter>', show)
        widget.bind('<Leave>', hide)
    
    def _on_canvas_configure(self, event):
        """Canvas大小变化时调整内部框架宽度"""
        self._canvas.itemconfig(self._canvas_window, width=event.width)
    
    def _bind_mousewheel(self, event):
        """绑定鼠标滚轮"""
        self._canvas.bind_all('<MouseWheel>', self._on_mousewheel)
    
    def _unbind_mousewheel(self, event):
        """解绑鼠标滚轮"""
        self._canvas.unbind_all('<MouseWheel>')
    
    def _on_mousewheel(self, event):
        """鼠标滚轮滚动"""
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
    
    def _highlight_filter(self):
        """高亮当前过滤按钮"""
        for level, btn in self._filter_btns.items():
            if level == self._filter_level:
                btn.configure(bg='#555555', font=('Helvetica', 8, 'bold'))
            else:
                btn.configure(bg='#333333', font=('Helvetica', 8))
    
    def _set_filter(self, level: str):
        """设置日志级别过滤"""
        self._filter_level = level
        self._highlight_filter()
        self._refresh_display()
    
    def _toggle_filter(self):
        """切换过滤（快捷键）"""
        levels = ['all', 'info', 'warning', 'error']
        idx = levels.index(self._filter_level) if self._filter_level in levels else 0
        self._set_filter(levels[(idx + 1) % len(levels)])
    
    def _toggle_display_mode(self):
        """切换显示模式"""
        if self._display_mode == 'detail':
            self._display_mode = 'summary'
            self._mode_btn.configure(text='📋')
        else:
            self._display_mode = 'detail'
            self._mode_btn.configure(text='📊')
        self._refresh_display()
    
    def _toggle_auto_scroll(self, event=None):
        """切换自动滚动"""
        self._auto_scroll_var.set(not self._auto_scroll_var.get())
        if self._auto_scroll_var.get():
            self._auto_scroll_btn.configure(fg='#4ec9b0', text='📌 自动滚动')
        else:
            self._auto_scroll_btn.configure(fg='#888888', text='📌 暂停滚动')
    
    def _clear_logs(self):
        """清空日志"""
        with FloatingLogPanel._shared_lock:
            FloatingLogPanel._shared_logs.clear()
            FloatingLogPanel._shared_summary['tx_count'] = 0
            FloatingLogPanel._shared_summary['rx_count'] = 0
            FloatingLogPanel._shared_summary['tx_bytes'] = 0
            FloatingLogPanel._shared_summary['rx_bytes'] = 0
        self._refresh_display()
    
    # === 拖拽方法 ===
    
    def _on_drag_start(self, event):
        """拖拽开始"""
        self._is_dragging = True
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        self._drag_start_win_x = self.winfo_x()
        self._drag_start_win_y = self.winfo_y()
    
    def _on_drag_motion(self, event):
        """拖拽移动"""
        if not self._is_dragging:
            return
        dx = event.x_root - self._drag_start_x
        dy = event.y_root - self._drag_start_y
        new_x = self._drag_start_win_x + dx
        new_y = self._drag_start_win_y + dy
        self.geometry(f'+{new_x}+{new_y}')
    
    def _on_drag_end(self, event):
        """拖拽结束 - 执行边缘吸附"""
        self._is_dragging = False
        self._snap_to_edge()
    
    def _snap_to_edge(self):
        """边缘吸附"""
        try:
            x = self.winfo_x()
            y = self.winfo_y()
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            
            # 左边缘吸附
            if x < self._snap_margin:
                x = 0
            # 右边缘吸附
            elif x + self._window_width > screen_width - self._snap_margin:
                x = screen_width - self._window_width
            # 上边缘吸附
            if y < self._snap_margin:
                y = 0
            # 下边缘吸附
            elif y + self._window_height > screen_height - self._snap_margin:
                y = screen_height - self._window_height
            
            self.geometry(f'+{x}+{y}')
        except:
            pass
    
    # === 调整大小方法 ===
    
    def _on_resize_start(self, event, mode='se'):
        """调整大小开始"""
        self._resize_mode = mode
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root
        self._resize_start_w = self._window_width
        self._resize_start_h = self._window_height
    
    def _on_resize_motion(self, event):
        """调整大小移动"""
        if not self._resize_mode:
            return
        
