"""收发日志浮动功能 - 支持多窗口独立浮动、实时数据同步、可拖拽吸附、自适应缩放、日志级别过滤"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkfont
from datetime import datetime
from utils.hex_utils import bytes_to_hex_str, bytes_to_ascii_str, bytes_to_hex_ascii
from ui.theme import get_theme


DISPLAY_HEX = 'Hex'
DISPLAY_ASCII = 'ASCII'
DISPLAY_MIX = 'Hex+ASCII'

FILTER_ALL = '全部'
FILTER_TX = '仅TX'
FILTER_RX = '仅RX'

# 日志级别
LOG_LEVEL_INFO = 'info'
LOG_LEVEL_WARNING = 'warning'
LOG_LEVEL_ERROR = 'error'

# 日志级别过滤选项
LEVEL_FILTER_ALL = '所有级别'
LEVEL_FILTER_INFO = '信息'
LEVEL_FILTER_WARNING = '警告'
LEVEL_FILTER_ERROR = '错误'

LEVEL_FILTER_OPTIONS = [LEVEL_FILTER_ALL, LEVEL_FILTER_INFO, LEVEL_FILTER_WARNING, LEVEL_FILTER_ERROR]

# 日志级别到标签的映射
LEVEL_TAG_MAP = {
    LOG_LEVEL_INFO: 'info',
    LOG_LEVEL_WARNING: 'warning',
    LOG_LEVEL_ERROR: 'error',
}

# 日志级别到显示名称的映射
LEVEL_DISPLAY_MAP = {
    LOG_LEVEL_INFO: '信息',
    LOG_LEVEL_WARNING: '警告',
    LOG_LEVEL_ERROR: '错误',
}


class LogEntry:
    """单条日志条目 - 轻量级数据结构，优化内存占用"""
    __slots__ = ('timestamp', 'text', 'tag', 'level', 'direction')

    def __init__(self, timestamp: str, text: str, tag: str, level: str = LOG_LEVEL_INFO, direction: str = ''):
        self.timestamp = timestamp
        self.text = text
        self.tag = tag
        self.level = level
        self.direction = direction  # 'tx', 'rx', ''


class FloatWindow:
    """独立浮动窗口 - 支持拖拽、边缘吸附、自适应缩放，与主界面主题风格一致"""

    SNAP_DISTANCE = 20  # 边缘吸附距离（像素）
    MIN_WIDTH = 300
    MIN_HEIGHT = 200
    DEFAULT_WIDTH = 600
    DEFAULT_HEIGHT = 400

    # 颜色通过主题系统获取，不再硬编码

    def __init__(self, log_panel, window_id: int):
        self._log_panel = log_panel
        self._window_id = window_id
        self._window = None
        self._text_widget = None
        self._scrollbar = None
        self._summary_label = None
        self._level_filter_var = tk.StringVar(value=LEVEL_FILTER_ALL)
        self._display_mode_var = tk.StringVar(value=DISPLAY_MIX)
        self._auto_scroll_var = tk.BooleanVar(value=True)
        self._is_dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_win_x = 0
        self._drag_win_y = 0
        self._snap_edges = {'left': False, 'right': False, 'top': False, 'bottom': False}
        self._summary_mode = False  # False=详细列表, True=汇总统计
        self._build_window()

    def _make_title_btn(self, parent, text, command, bg, hover_bg=None, width=2):
        """创建统一样式的标题栏按钮"""
        theme = get_theme()
        btn = tk.Button(
            parent, text=text, font=theme.font('ui_label_bold'),
            bg=bg, fg=theme.color('title_fg'), relief=tk.FLAT,
            width=width, cursor='hand2',
            activebackground=hover_bg or bg,
            activeforeground=theme.color('accent_fg'),
            bd=0, highlightthickness=0,
            command=command,
        )
        if hover_bg:
            btn.bind('<Enter>', lambda e: btn.configure(bg=hover_bg))
            btn.bind('<Leave>', lambda e: btn.configure(bg=bg))
        return btn

    def _build_window(self):
        """构建浮动窗口 - 使用主题系统"""
        theme = get_theme()
        self._window = tk.Toplevel(self._log_panel._root)
        self._window.title(f'收发日志 #{self._window_id}')
        self._window.geometry(f'{self.DEFAULT_WIDTH}x{self.DEFAULT_HEIGHT}')
        self._window.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)

        self._window.overrideredirect(True)

        # ===== 外层边框容器 =====
        outer_frame = tk.Frame(self._window, bg=theme.color('border_color'), bd=1, relief=tk.SOLID)
        outer_frame.pack(fill=tk.BOTH, expand=True)

        # ===== 主容器 =====
        main_frame = tk.Frame(outer_frame, bg=theme.color('toolbar_bg'))
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ===== 自定义标题栏 =====
        title_bar = tk.Frame(main_frame, bg=theme.color('title_bg'), height=32, cursor='fleur')
        title_bar.pack(fill=tk.X)
        title_bar.pack_propagate(False)

        icon_label = tk.Label(
            title_bar, text='📋',
            bg=theme.color('title_bg'), fg=theme.color('title_fg'),
            font=theme.font('ui_title'),
        )
        icon_label.pack(side=tk.LEFT, padx=(10, 4))

        title_label = tk.Label(
            title_bar, text=f'收发日志 #{self._window_id}',
            bg=theme.color('title_bg'), fg=theme.color('title_fg'),
            font=theme.font('ui_bold'), anchor=tk.W,
        )
        title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_frame = tk.Frame(title_bar, bg=theme.color('title_bg'))
        btn_frame.pack(side=tk.RIGHT, padx=(0, 6))

        self._summary_btn = self._make_title_btn(
            btn_frame, '📊', self._toggle_summary_mode,
            theme.color('title_button_bg'), theme.color('title_button_hover_bg'), width=2,
        )
        self._summary_btn.pack(side=tk.LEFT, padx=(0, 3))

        min_btn = self._make_title_btn(
            btn_frame, '─', self._minimize_window,
            theme.color('title_button_bg'), theme.color('title_button_hover_bg'), width=2,
        )
        min_btn.pack(side=tk.LEFT, padx=(0, 3))

        close_btn = self._make_title_btn(
            btn_frame, '✕', self._close_window,
            theme.color('close_button_bg'), theme.color('close_button_hover_bg'), width=2,
        )
        close_btn.pack(side=tk.LEFT)

        for widget in (title_bar, icon_label, title_label):
            widget.bind('<ButtonPress-1>', self._on_drag_start)
            widget.bind('<B1-Motion>', self._on_drag_motion)
            widget.bind('<ButtonRelease-1>', self._on_drag_end)

        # ===== 分隔线 =====
        sep = tk.Frame(main_frame, bg=theme.color('border_color'), height=1)
        sep.pack(fill=tk.X)

        # ===== 工具栏 =====
        toolbar = tk.Frame(main_frame, bg=theme.color('toolbar_bg'))
        toolbar.pack(fill=tk.X, pady=(4, 2), padx=6)

        mode_label = tk.Label(
            toolbar, text='显示:', bg=theme.color('toolbar_bg'),
            fg=theme.color('toolbar_label_fg'), font=theme.font('ui_sm'),
        )
        mode_label.pack(side=tk.LEFT)

        for mode in [DISPLAY_HEX, DISPLAY_ASCII, DISPLAY_MIX]:
            rb = tk.Radiobutton(
                toolbar, text=mode, variable=self._display_mode_var,
                value=mode, command=self._on_mode_change,
                bg=theme.color('toolbar_bg'), fg=theme.color('toolbar_fg'),
                selectcolor=theme.color('accent_bg'),
                activebackground=theme.color('toolbar_bg'),
                activeforeground=theme.color('accent_fg'),
                font=theme.font('ui_sm'),
                relief=tk.FLAT, highlightthickness=0,
            )
            rb.pack(side=tk.LEFT, padx=(2, 2))

        sep1 = tk.Frame(toolbar, bg=theme.color('border_color'), width=1)
        sep1.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)

        self._auto_scroll_cb = tk.Checkbutton(
            toolbar, text='自动滚动', variable=self._auto_scroll_var,
            bg=theme.color('toolbar_bg'), fg=theme.color('toolbar_fg'),
            selectcolor=theme.color('accent_bg'),
            activebackground=theme.color('toolbar_bg'),
            activeforeground=theme.color('accent_fg'),
            font=theme.font('ui_sm'),
            relief=tk.FLAT, highlightthickness=0,
        )
        self._auto_scroll_cb.pack(side=tk.LEFT)

        sep2 = tk.Frame(toolbar, bg=theme.color('border_color'), width=1)
        sep2.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)

        level_label = tk.Label(
            toolbar, text='级别:', bg=theme.color('toolbar_bg'),
            fg=theme.color('toolbar_label_fg'), font=theme.font('ui_sm'),
        )
        level_label.pack(side=tk.LEFT)

        level_cb = ttk.Combobox(
            toolbar, textvariable=self._level_filter_var,
            values=LEVEL_FILTER_OPTIONS, state='readonly', width=8,
        )
        level_cb.pack(side=tk.LEFT, padx=(2, 4))
        level_cb.bind('<<ComboboxSelected>>', self._on_level_filter_change)

        # 右侧清空按钮
        btn_bg = theme.color('button_bg')
        btn_hover_bg = theme.color('button_hover_bg')
        clear_btn = tk.Button(
            toolbar, text='🗑 清空', command=self._clear_window,
            bg=btn_bg, fg=theme.color('button_fg'), relief=tk.FLAT,
            font=theme.font('ui_sm'), cursor='hand2',
            activebackground=btn_hover_bg, activeforeground=theme.color('accent_fg'),
            bd=0, highlightthickness=0, padx=8, pady=1,
        )
        clear_btn.pack(side=tk.RIGHT, padx=(0, 2))
        clear_btn.bind('<Enter>', lambda e, bh=btn_hover_bg: clear_btn.configure(bg=bh))
        clear_btn.bind('<Leave>', lambda e, bb=btn_bg: clear_btn.configure(bg=bb))

        # ===== 汇总统计栏 =====
        self._summary_frame = tk.Frame(main_frame, bg=theme.color('summary_bg'))
        self._summary_label = tk.Label(
            self._summary_frame, text='', bg=theme.color('summary_bg'),
            fg=theme.color('summary_fg'), font=theme.font('ui_sm'),
            anchor=tk.W, padx=8, pady=3,
        )
        self._summary_label.pack(fill=tk.X)

        # ===== 文本显示区域 =====
        text_frame = tk.Frame(main_frame, bg=theme.color('toolbar_bg'))
        text_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        self._text_widget = tk.Text(
            text_frame, wrap=tk.WORD, relief=tk.FLAT, borderwidth=0,
            padx=8, pady=6, state=tk.DISABLED,
        )
        theme.configure_float_window(self._text_widget)
        self._scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self._text_widget.yview)
        self._text_widget.configure(yscrollcommand=self._scrollbar.set)

        self._text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 配置日志标签颜色（使用主题系统）
        theme.configure_tags(self._text_widget)

        # 右键菜单
        self._context_menu = tk.Menu(self._text_widget, tearoff=0,
                                     bg=theme.color('toolbar_bg'),
                                     fg=theme.color('toolbar_fg'),
                                     activebackground=theme.color('accent_bg'),
                                     activeforeground=theme.color('accent_fg'),
                                     font=theme.font('ui_sm'))
        self._context_menu.add_command(label='复制', command=self._copy_selection)
        self._context_menu.add_command(label='全选', command=self._select_all)
        self._context_menu.add_separator()
        self._context_menu.add_command(label='清空', command=self._clear_window)
        self._text_widget.bind('<Button-2>', self._show_context_menu)
        self._text_widget.bind('<Button-3>', self._show_context_menu)

        self._text_widget.bind('<Command-c>', lambda e: self._copy_selection())
        self._text_widget.bind('<Control-c>', lambda e: self._copy_selection())

        self._window.protocol('WM_DELETE_WINDOW', self._close_window)
        self._window.bind('<Configure>', self._on_window_configure)
        self._update_summary()

    def _on_drag_start(self, event):
        """拖拽开始"""
        self._is_dragging = True
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        self._drag_win_x = self._window.winfo_x()
        self._drag_win_y = self._window.winfo_y()

    def _on_drag_motion(self, event):
        """拖拽移动"""
        if not self._is_dragging:
            return
        dx = event.x_root - self._drag_start_x
        dy = event.y_root - self._drag_start_y
        new_x = self._drag_win_x + dx
        new_y = self._drag_win_y + dy
        self._window.geometry(f'+{new_x}+{new_y}')

    def _on_drag_end(self, event):
        """拖拽结束 - 执行边缘吸附"""
        self._is_dragging = False
        self._snap_to_edge()

    def _snap_to_edge(self):
        """边缘吸附 - 靠近屏幕边缘时自动吸附"""
        try:
            screen_w = self._window.winfo_screenwidth()
            screen_h = self._window.winfo_screenheight()
            win_x = self._window.winfo_x()
            win_y = self._window.winfo_y()
            win_w = self._window.winfo_width()
            win_h = self._window.winfo_height()

            new_x, new_y = win_x, win_y
            self._snap_edges = {'left': False, 'right': False, 'top': False, 'bottom': False}

            # 左边缘吸附
            if win_x <= self.SNAP_DISTANCE:
                new_x = 0
                self._snap_edges['left'] = True
            # 右边缘吸附
            elif screen_w - (win_x + win_w) <= self.SNAP_DISTANCE:
                new_x = screen_w - win_w
                self._snap_edges['right'] = True
            # 上边缘吸附
            if win_y <= self.SNAP_DISTANCE:
                new_y = 0
                self._snap_edges['top'] = True
            # 下边缘吸附
            elif screen_h - (win_y + win_h) <= self.SNAP_DISTANCE:
                new_y = screen_h - win_h
                self._snap_edges['bottom'] = True

            if new_x != win_x or new_y != win_y:
                self._window.geometry(f'+{new_x}+{new_y}')
        except Exception:
            pass

    def _on_window_configure(self, event):
        """窗口大小变化时自适应调整"""
        if event.widget == self._window:
            # 更新汇总显示
            self._update_summary()

    def _toggle_summary_mode(self):
        """切换汇总/详细模式"""
        self._summary_mode = not self._summary_mode
        if self._summary_mode:
            self._summary_btn.configure(text='📋')
            self._summary_frame.pack(fill=tk.X, before=self._text_widget.master)
        else:
            self._summary_btn.configure(text='📊')
            self._summary_frame.pack_forget()
        self._refresh_display()

    def _minimize_window(self):
        """最小化窗口"""
        self._window.iconify()

    def _close_window(self):
        """关闭浮动窗口"""
        self._log_panel._remove_float_window(self._window_id)
        self._window.destroy()

    def _on_mode_change(self):
        """显示模式切换"""
        self._log_panel._display_mode = self._display_mode_var.get()
        self._refresh_display()

    def _on_level_filter_change(self, event=None):
        """日志级别过滤切换"""
        self._refresh_display()

    def _clear_window(self):
        """清空当前窗口显示"""
        self._text_widget.configure(state=tk.NORMAL)
        self._text_widget.delete('1.0', tk.END)
        self._text_widget.configure(state=tk.DISABLED)
        self._update_summary()

    def _show_context_menu(self, event):
        """显示右键菜单"""
        try:
            self._context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._context_menu.grab_release()

    def _copy_selection(self):
        """复制选中文本"""
        try:
            sel = self._text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            self._text_widget.clipboard_clear()
            self._text_widget.clipboard_append(sel)
        except tk.TclError:
            pass

    def _select_all(self):
        """全选"""
        self._text_widget.configure(state=tk.NORMAL)
        self._text_widget.tag_add(tk.SEL, '1.0', tk.END)
        self._text_widget.configure(state=tk.DISABLED)

    def _format_data(self, data: bytes) -> str:
        """根据显示模式格式化数据"""
        mode = self._display_mode_var.get()
        if mode == DISPLAY_HEX:
            return bytes_to_hex_str(data)
        elif mode == DISPLAY_ASCII:
            return bytes_to_ascii_str(data)
        else:
            return bytes_to_hex_ascii(data)

    def append_log(self, line_text: str, tag: str, level: str = LOG_LEVEL_INFO):
        """追加日志到窗口"""
        if not self._window or not self._window.winfo_exists():
            return

        # 检查级别过滤
        level_filter = self._level_filter_var.get()
        if level_filter != LEVEL_FILTER_ALL:
            level_map = {
                LEVEL_FILTER_INFO: LOG_LEVEL_INFO,
                LEVEL_FILTER_WARNING: LOG_LEVEL_WARNING,
                LEVEL_FILTER_ERROR: LOG_LEVEL_ERROR,
            }
            if level_map.get(level_filter) != level:
                return

        self._text_widget.configure(state=tk.NORMAL)
        self._text_widget.insert(tk.END, line_text, tag)
        self._text_widget.configure(state=tk.DISABLED)

        if self._auto_scroll_var.get():
            self._text_widget.see(tk.END)

        # 更新汇总
        self._update_summary()

    def _update_summary(self):
        """更新汇总统计"""
        if not self._summary_label or not self._summary_label.winfo_exists():
            return

        try:
            content = self._text_widget.get('1.0', tk.END) if self._text_widget else ''
            lines = [l for l in content.split('\n') if l.strip()]
            tx_count = sum(1 for l in lines if 'TX' in l)
            rx_count = sum(1 for l in lines if 'RX' in l)
            info_count = sum(1 for l in lines if '信息' in l or ('[' in l and ']' in l and 'TX' not in l and 'RX' not in l))
            total = len(lines)

            summary_text = (
                f'📊 总计: {total} 条  '
                f'📤 TX: {tx_count}  '
                f'📥 RX: {rx_count}  '
                f'ℹ️ 信息: {info_count}'
            )
            self._summary_label.configure(text=summary_text)
        except Exception:
            pass

    def _refresh_display(self):
        """刷新显示 - 重新应用过滤"""
        if not self._window or not self._window.winfo_exists():
            return
        # 从主日志面板获取数据重新显示
        self._log_panel._refresh_float_window(self._window_id)

    def is_alive(self) -> bool:
        """检查窗口是否存活"""
        try:
            return self._window is not None and self._window.winfo_exists()
        except Exception:
            return False

    def get_window(self):
        """获取窗口对象"""
        return self._window


class LogPanel(ttk.LabelFrame):
    """收发日志面板 - 支持多窗口独立浮动、实时数据同步、可拖拽吸附、自适应缩放、日志级别过滤"""

    def __init__(self, parent, max_lines: int = 10000):
        super().__init__(parent, text=' 收发日志 ', padding=8)
        self._parent_frame = parent
        self._root = parent.winfo_toplevel() if parent else None
        self._auto_scroll = True
        self._display_mode = DISPLAY_MIX
        self._max_lines = max_lines
        self._auto_save_enabled = False
        self._auto_save_file = None
        self._auto_save_dir = None
        self._search_highlight_tag = 'search_highlight'
        self._search_current_tag = 'search_current'
        self._search_matches = []
        self._search_index = -1
        self._filter_mode = FILTER_ALL
        self._level_filter = LEVEL_FILTER_ALL
        self._all_entries = []  # 存储 LogEntry 对象，优化内存
        self._line_count = 0

        # 多窗口浮动支持
        self._float_windows = {}  # {window_id: FloatWindow}
        self._next_window_id = 1

        # 内部容器，用于浮动时整体移动
        self._inner_container = ttk.Frame(self)
        self._inner_container.pack(fill=tk.BOTH, expand=True)
        self._build_ui()

    def _build_ui(self):
        # ========== 工具栏（单行精简）==========
        toolbar = ttk.Frame(self._inner_container)
        toolbar.pack(fill=tk.X, pady=(0, 2))

        ttk.Label(toolbar, text='显示:', font=tkfont.nametofont('TkCaptionFont')).pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value=DISPLAY_MIX)
        mode_cb = ttk.Combobox(toolbar, textvariable=self.mode_var,
                               values=[DISPLAY_HEX, DISPLAY_ASCII, DISPLAY_MIX],
                               state='readonly', width=10)
        mode_cb.pack(side=tk.LEFT, padx=(0, 6))
        mode_cb.bind('<<ComboboxSelected>>', self._on_mode_change)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)

        self.scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text='自动滚动', variable=self.scroll_var).pack(side=tk.LEFT)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)

        self._new_float_btn = ttk.Button(toolbar, text='➕新窗口', command=self._create_new_float_window, width=8)
        self._new_float_btn.pack(side=tk.LEFT, padx=0)

        # 齿轮菜单按钮
        self._gear_menu = tk.Menu(toolbar, tearoff=0)
        self._gear_menu.add_command(label='💾 自动保存：关', command=self._toggle_auto_save)
        self._gear_menu.add_separator()
        self._gear_menu.add_command(label='🗑 清空全部', command=self.clear)

        gear_btn = ttk.Button(toolbar, text='⚙', width=3, command=self._show_gear_menu)
        gear_btn.pack(side=tk.LEFT, padx=(2, 0))

        # ========== 搜索栏 ==========
        search_bar = ttk.Frame(self._inner_container)
        search_bar.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(search_bar, text='级别:', font=tkfont.nametofont('TkCaptionFont')).pack(side=tk.LEFT, padx=(0, 2))
        self.level_filter_var = tk.StringVar(value=LEVEL_FILTER_ALL)
        self.level_filter_cb = ttk.Combobox(
            search_bar, textvariable=self.level_filter_var,
            values=LEVEL_FILTER_OPTIONS, state='readonly', width=8,
        )
        self.level_filter_cb.pack(side=tk.LEFT, padx=(0, 4))
        self.level_filter_cb.bind('<<ComboboxSelected>>', self._on_level_filter_change)

        ttk.Label(search_bar, text='过滤:', font=tkfont.nametofont('TkCaptionFont')).pack(side=tk.LEFT, padx=(0, 2))
        self.filter_var = tk.StringVar(value=FILTER_ALL)
        self.filter_cb = ttk.Combobox(search_bar, textvariable=self.filter_var,
                                      values=[FILTER_ALL, FILTER_TX, FILTER_RX],
                                      state='readonly', width=8)
        self.filter_cb.pack(side=tk.LEFT, padx=(0, 4))
        self.filter_cb.bind('<<ComboboxSelected>>', self._on_filter_change)

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_bar, textvariable=self.search_var, width=10)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 2))
        self.search_entry.bind('<Return>', lambda e: self._search_next())
        self.search_entry.bind('<Shift-Return>', lambda e: self._search_prev())

        # 搜索模式切换
        self._search_regex = False
        self._search_case = False
        self._regex_btn = ttk.Button(search_bar, text='.*', command=self._toggle_search_regex,
                                     width=3, style='Toolbutton')
        self._regex_btn.pack(side=tk.LEFT, padx=0)
        self._case_btn = ttk.Button(search_bar, text='Aa', command=self._toggle_search_case,
                                    width=3, style='Toolbutton')
        self._case_btn.pack(side=tk.LEFT, padx=0)

        ttk.Button(search_bar, text='▲', command=self._search_prev, width=2).pack(side=tk.LEFT, padx=0)
        ttk.Button(search_bar, text='▼', command=self._search_next, width=2).pack(side=tk.LEFT, padx=0)

        self.search_count_var = tk.StringVar(value='')
        ttk.Label(search_bar, textvariable=self.search_count_var, foreground='gray',
                  font=('', 9)).pack(side=tk.LEFT, padx=(2, 0))

        ttk.Button(search_bar, text='✕', command=self._search_clear, width=2).pack(side=tk.LEFT, padx=(1, 0))

        # 汇总统计栏
        self._summary_frame = ttk.Frame(self._inner_container)
        self._summary_label = ttk.Label(self._summary_frame, text='', font=('', 9))
        self._summary_label.pack(fill=tk.X, padx=4, pady=1)

        text_frame = ttk.Frame(self._inner_container)
        text_frame.pack(fill=tk.BOTH, expand=True)

        theme = get_theme()
        self.text = tk.Text(text_frame, wrap=tk.WORD, relief=tk.FLAT, borderwidth=0,
                            padx=6, pady=4, state=tk.DISABLED)
        theme.configure_text_widget(self.text, 'monospace')
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)

        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._context_menu = tk.Menu(self.text, tearoff=0)
        self._context_menu.add_command(label='复制', command=self._copy_selection)
        self._context_menu.add_command(label='全选', command=self._select_all)
        self._context_menu.add_separator()
        self._context_menu.add_command(label='清空', command=self.clear)
        self.text.bind('<Button-2>', self._show_context_menu)
        self.text.bind('<Button-3>', self._show_context_menu)
        self.text.bind('<Control-Button-1>', self._show_context_menu)

        self.text.bind('<ButtonPress-1>', self._on_click_start)
        self.text.bind('<B1-Motion>', self._on_click_drag)
        self.text.bind('<ButtonRelease-1>', self._on_click_release)
        self.text.bind('<Command-c>', lambda e: self._copy_selection())
        self.text.bind('<Control-c>', lambda e: self._copy_selection())
        self.text.bind('<Command-f>', lambda e: self.search_entry.focus_set())
        self.text.bind('<Control-f>', lambda e: self.search_entry.focus_set())

        theme.configure_tags(self.text)

        # 初始更新汇总
        self._update_summary()

    def _create_new_float_window(self):
        """创建新的独立浮动窗口"""
        window_id = self._next_window_id
        self._next_window_id += 1
        float_win = FloatWindow(self, window_id)
        self._float_windows[window_id] = float_win

        # 同步现有数据到新窗口
        self._sync_to_float_window(window_id)

        return window_id

    def _remove_float_window(self, window_id: int):
        """移除浮动窗口"""
        self._float_windows.pop(window_id, None)

    def _sync_to_float_window(self, window_id: int):
        """同步所有日志到指定浮动窗口"""
        float_win = self._float_windows.get(window_id)
        if not float_win or not float_win.is_alive():
            return

        float_win._clear_window()

        for entry in self._all_entries:
            if self._filter_mode != FILTER_ALL:
                if self._filter_mode == FILTER_TX and entry.direction != 'tx':
                    continue
                if self._filter_mode == FILTER_RX and entry.direction != 'rx':
                    continue

            line_text = self._format_entry_text(entry)
            float_win.append_log(line_text, entry.tag, entry.level)

    def _sync_to_all_float_windows(self):
        """同步到所有浮动窗口"""
        for wid in list(self._float_windows.keys()):
            self._sync_to_float_window(wid)

    def _refresh_float_window(self, window_id: int):
        """刷新指定浮动窗口的显示"""
        self._sync_to_float_window(window_id)

    def _sync_entry_to_float_windows(self, entry: LogEntry):
        """同步单条日志到所有浮动窗口"""
        for wid, fw in list(self._float_windows.items()):
            if fw.is_alive():
                line_text = self._format_entry_text(entry)
                fw.append_log(line_text, entry.tag, entry.level)

    def _format_entry_text(self, entry: LogEntry) -> str:
        """格式化日志条目为文本"""
        return f'[{entry.timestamp}] {entry.text}\n'

    def _on_mode_change(self, event=None):
        self._display_mode = self.mode_var.get()
        for wid, fw in list(self._float_windows.items()):
            if fw.is_alive():
                fw._display_mode_var.set(self._display_mode)
                fw._refresh_display()

    def _on_level_filter_change(self, event=None):
        """主面板级别过滤变化"""
        self._level_filter = self.level_filter_var.get()
        self._apply_level_filter()

    def _apply_level_filter(self):
        """应用级别过滤到主面板"""
        self.text.configure(state=tk.NORMAL)
        self.text.delete('1.0', tk.END)
        self.text.configure(state=tk.DISABLED)

        level_filter = self.level_filter_var.get()
        for entry in self._all_entries:
            if self._filter_mode != FILTER_ALL:
                if self._filter_mode == FILTER_TX and entry.direction != 'tx':
                    continue
                if self._filter_mode == FILTER_RX and entry.direction != 'rx':
                    continue

            if level_filter != LEVEL_FILTER_ALL:
                level_map = {
                    LEVEL_FILTER_INFO: LOG_LEVEL_INFO,
                    LEVEL_FILTER_WARNING: LOG_LEVEL_WARNING,
                    LEVEL_FILTER_ERROR: LOG_LEVEL_ERROR,
                }
                if level_map.get(level_filter) != entry.level:
                    continue

            line_text = self._format_entry_text(entry)
            self._append(line_text, entry.tag)

        self._update_summary()
        self._search_clear()

    def _format_data(self, data: bytes) -> str:
        mode = self._display_mode
        if mode == DISPLAY_HEX:
            return bytes_to_hex_str(data)
        elif mode == DISPLAY_ASCII:
            return bytes_to_ascii_str(data)
        else:
            return bytes_to_hex_ascii(data)

    def log_tx(self, data: bytes, target: str = None, source: str = None, level: str = LOG_LEVEL_INFO):
        """记录发送日志"""
        now = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        text = self._format_data(data)
        # 兼容 source 参数（main_window 中传的是 source）
        label = source or target
        prefix = f'TX -> {label} >> ' if label else 'TX >> '
        line_text = f'[{now}] {prefix}{text}'

        entry = LogEntry(now, line_text, 'tx', level, 'tx')
        self._all_entries.append(entry)

        if self._level_filter != LEVEL_FILTER_ALL:
            level_map = {
                LEVEL_FILTER_INFO: LOG_LEVEL_INFO,
                LEVEL_FILTER_WARNING: LOG_LEVEL_WARNING,
                LEVEL_FILTER_ERROR: LOG_LEVEL_ERROR,
            }
            if level_map.get(self._level_filter) != level:
                self._sync_entry_to_float_windows(entry)
                return

        if self._filter_mode in (FILTER_ALL, FILTER_TX):
            self._append(f'{line_text}\n', 'tx')

        self._sync_entry_to_float_windows(entry)

    def log_rx(self, data: bytes, source: str = None, level: str = LOG_LEVEL_INFO):
        """记录接收日志"""
        now = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        text = self._format_data(data)
        prefix = f'RX <- {source} << ' if source else 'RX << '
        line_text = f'[{now}] {prefix}{text}'

        entry = LogEntry(now, line_text, 'rx', level, 'rx')
        self._all_entries.append(entry)

        if self._level_filter != LEVEL_FILTER_ALL:
            level_map = {
                LEVEL_FILTER_INFO: LOG_LEVEL_INFO,
                LEVEL_FILTER_WARNING: LOG_LEVEL_WARNING,
                LEVEL_FILTER_ERROR: LOG_LEVEL_ERROR,
            }
            if level_map.get(self._level_filter) != level:
                self._sync_entry_to_float_windows(entry)
                return

        if self._filter_mode in (FILTER_ALL, FILTER_RX):
            self._append(f'{line_text}\n', 'rx')

        self._sync_entry_to_float_windows(entry)

    def log_info(self, message: str, level: str = LOG_LEVEL_INFO):
        """记录信息日志"""
        now = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        line_text = f'[{now}] {message}'

        entry = LogEntry(now, line_text, 'info', level, '')
        self._all_entries.append(entry)

        if self._level_filter != LEVEL_FILTER_ALL:
            level_map = {
                LEVEL_FILTER_INFO: LOG_LEVEL_INFO,
                LEVEL_FILTER_WARNING: LOG_LEVEL_WARNING,
                LEVEL_FILTER_ERROR: LOG_LEVEL_ERROR,
            }
            if level_map.get(self._level_filter) != level:
                self._sync_entry_to_float_windows(entry)
                return

        if self._filter_mode == FILTER_ALL:
            self._append(f'{line_text}\n', 'info')

        self._sync_entry_to_float_windows(entry)

    def set_max_lines(self, max_lines: int):
        self._max_lines = max_lines

    def _append(self, text: str, tag: str):
        self.text.configure(state=tk.NORMAL)
        self.text.insert(tk.END, text, tag)
        self._line_count += 1
        if self._max_lines > 0 and self._line_count > self._max_lines:
            first_line_end = self.text.index('2.0')
            self.text.delete('1.0', first_line_end)
            self._line_count -= 1
        self.text.configure(state=tk.DISABLED)
        if self.scroll_var.get():
            self.text.see(tk.END)
        self._auto_save()

    def _on_filter_change(self, event=None):
        self._filter_mode = self.filter_var.get()
        self._apply_filter()

    def _apply_filter(self):
        self.text.configure(state=tk.NORMAL)
        self.text.delete('1.0', tk.END)
        self.text.configure(state=tk.DISABLED)

        filter_mode = self.filter_var.get()
        level_filter = self.level_filter_var.get()
        for entry in self._all_entries:
            if filter_mode != FILTER_ALL:
                if filter_mode == FILTER_TX and entry.direction != 'tx':
                    continue
                if filter_mode == FILTER_RX and entry.direction != 'rx':
                    continue

            if level_filter != LEVEL_FILTER_ALL:
                level_map = {
                    LEVEL_FILTER_INFO: LOG_LEVEL_INFO,
                    LEVEL_FILTER_WARNING: LOG_LEVEL_WARNING,
                    LEVEL_FILTER_ERROR: LOG_LEVEL_ERROR,
                }
                if level_map.get(level_filter) != entry.level:
                    continue

            line_text = self._format_entry_text(entry)
            self._append(line_text, entry.tag)

        self._update_summary()
        self._search_clear()

    def _update_summary(self):
        """更新汇总统计"""
        if not hasattr(self, '_summary_label') or not self._summary_label:
            return
        try:
            content = self.text.get('1.0', tk.END) if self.text else ''
            lines = [l for l in content.split('\n') if l.strip()]
            tx_count = sum(1 for l in lines if 'TX' in l)
            rx_count = sum(1 for l in lines if 'RX' in l)
            info_count = sum(1 for l in lines if '信息' in l or ('[' in l and ']' in l and 'TX' not in l and 'RX' not in l))
            total = len(lines)

            summary_text = (
                f'📊 总计: {total} 条  '
                f'📤 TX: {tx_count}  '
                f'📥 RX: {rx_count}  '
                f'ℹ️ 信息: {info_count}'
            )
            self._summary_label.configure(text=summary_text)
        except Exception:
            pass

    def _on_click_start(self, event):
        """鼠标点击开始 - 清除搜索高亮"""
        self._search_clear()

    def _on_click_drag(self, event):
        """鼠标拖拽"""
        pass

    def _on_click_release(self, event):
        """鼠标释放"""
        pass

    def _show_context_menu(self, event):
        """显示右键菜单"""
        try:
            self._context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._context_menu.grab_release()

    def _copy_selection(self):
        """复制选中文本"""
        try:
            sel = self.text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.text.clipboard_clear()
            self.text.clipboard_append(sel)
        except tk.TclError:
            pass

    def _select_all(self):
        """全选"""
        self.text.configure(state=tk.NORMAL)
        self.text.tag_add(tk.SEL, '1.0', tk.END)
        self.text.configure(state=tk.DISABLED)

    def _toggle_search_regex(self):
        """切换正则搜索模式"""
        self._search_regex = not self._search_regex
        self._regex_btn.configure(relief=tk.SUNKEN if self._search_regex else tk.RAISED)
        if self.search_var.get().strip():
            self._search_clear()
            self._search_next()

    def _toggle_search_case(self):
        """切换大小写敏感模式"""
        self._search_case = not self._search_case
        self._case_btn.configure(relief=tk.SUNKEN if self._search_case else tk.RAISED)
        if self.search_var.get().strip():
            self._search_clear()
            self._search_next()

    def _find_all_matches(self, content, keyword):
        """查找所有匹配位置，返回 [(start_index, end_index), ...]"""
        import re
        if self._search_regex:
            try:
                flags = 0 if self._search_case else re.IGNORECASE
                pattern = re.compile(keyword, flags)
                matches = []
                for m in pattern.finditer(content):
                    # content 包含全文，需要将字符偏移转为 tkinter 行.列格式
                    start_line = content[:m.start()].count('\n') + 1
                    start_col_start = m.start() - content[:m.start()].rfind('\n') - 1
                    if start_col_start < 0:
                        start_col_start = m.start()
                    start_pos = f'{start_line}.{max(0, start_col_start)}'
                    # 计算结束位置
                    end_line = content[:m.end()].count('\n') + 1
                    end_col = m.end() - content[:m.end()].rfind('\n') - 1
                    if end_col < 0:
                        end_col = m.end()
                    end_pos = f'{end_line}.{max(0, end_col)}'
                    matches.append((start_pos, end_pos))
                return matches
            except re.error:
                self.search_count_var.set('正则错误')
                return []
        else:
            matches = []
            start = '1.0'
            nocase = not self._search_case
            while True:
                pos = self.text.search(keyword, start, tk.END, nocase=nocase)
                if not pos:
                    break
                end = f'{pos}+{len(keyword)}c'
                matches.append((pos, end))
                start = end
            return matches

    def _search_next(self):
        """搜索下一个匹配"""
        keyword = self.search_var.get().strip()
        if not keyword:
            return

        self._search_clear_highlights()
        content = self.text.get('1.0', tk.END)
        self._search_matches = self._find_all_matches(content, keyword)

        if not self._search_matches:
            self.search_count_var.set('未找到')
            return

        self._search_index = (self._search_index + 1) % len(self._search_matches)
        self._highlight_search()

    def _search_prev(self):
        """搜索上一个匹配"""
        keyword = self.search_var.get().strip()
        if not keyword:
            return

        self._search_clear_highlights()
        content = self.text.get('1.0', tk.END)
        self._search_matches = self._find_all_matches(content, keyword)

        if not self._search_matches:
            self.search_count_var.set('未找到')
            return

        self._search_index = (self._search_index - 1) % len(self._search_matches)
        self._highlight_search()

    def _highlight_search(self):
        """高亮搜索结果"""
        keyword = self.search_var.get().strip()
        if not keyword or not self._search_matches:
            return

        theme = get_theme()
        self.text.configure(state=tk.NORMAL)

        for i, (pos, end) in enumerate(self._search_matches):
            if i == self._search_index:
                self.text.tag_add(self._search_current_tag, pos, end)
                self.text.tag_config(self._search_current_tag,
                                     background=theme.color('search_current_bg'),
                                     foreground=theme.color('search_current_fg'))
                self.text.see(pos)
            else:
                self.text.tag_add(self._search_highlight_tag, pos, end)
                self.text.tag_config(self._search_highlight_tag,
                                     background=theme.color('search_highlight_bg'),
                                     foreground=theme.color('search_highlight_fg'))

        self.text.configure(state=tk.DISABLED)
        self.search_count_var.set(f'{self._search_index + 1}/{len(self._search_matches)}')

    def _search_clear_highlights(self):
        """清除搜索高亮"""
        self.text.configure(state=tk.NORMAL)
        self.text.tag_remove(self._search_highlight_tag, '1.0', tk.END)
        self.text.tag_remove(self._search_current_tag, '1.0', tk.END)
        self.text.configure(state=tk.DISABLED)

    def _search_clear(self):
        """清除搜索"""
        self._search_clear_highlights()
        self._search_matches = []
        self._search_index = -1
        self.search_count_var.set('')

    def _show_gear_menu(self):
        """显示齿轮菜单"""
        try:
            self._gear_menu.tk_popup(
                self._new_float_btn.winfo_rootx(),
                self._new_float_btn.winfo_rooty() + self._new_float_btn.winfo_height())
        finally:
            self._gear_menu.grab_release()

    def _toggle_auto_save(self):
        """切换自动保存"""
        if not self._auto_save_enabled:
            dir_path = filedialog.askdirectory(title='选择自动保存目录')
            if not dir_path:
                return
            self._auto_save_dir = dir_path
            self._auto_save_file = os.path.join(dir_path, f'comm_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
            self._auto_save_enabled = True
            self._gear_menu.entryconfigure(0, label='💾 自动保存：开')
        else:
            self._auto_save_enabled = False
            self._gear_menu.entryconfigure(0, label='💾 自动保存：关')

    def _auto_save(self):
        """自动保存日志"""
        if not self._auto_save_enabled or not self._auto_save_file:
            return
        try:
            content = self.text.get('1.0', tk.END)
            with open(self._auto_save_file, 'a', encoding='utf-8') as f:
                f.write(content)
        except Exception:
            pass

    def clear(self):
        """清空所有日志"""
        self.text.configure(state=tk.NORMAL)
        self.text.delete('1.0', tk.END)
        self.text.configure(state=tk.DISABLED)
        self._all_entries.clear()
        self._line_count = 0
        self._search_clear()
        self._update_summary()

        # 同步清空所有浮动窗口
        for wid, fw in list(self._float_windows.items()):
            if fw.is_alive():
                fw._clear_window()

    def export_log(self):
        """导出日志到文件"""
        file_path = filedialog.asksaveasfilename(
            defaultextension='.txt',
            filetypes=[('文本文件', '*.txt'), ('CSV文件', '*.csv'), ('所有文件', '*.*')],
            title='导出日志',
        )
        if not file_path:
            return

        try:
            content = self.text.get('1.0', tk.END)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo('导出成功', f'日志已导出到:\n{file_path}')
        except Exception as e:
            messagebox.showerror('导出失败', f'导出日志时出错:\n{e}')

    def get_log_content(self) -> str:
        """获取当前日志内容"""
        return self.text.get('1.0', tk.END) if self.text else ''

    def get_all_entries(self) -> list:
        """获取所有日志条目"""
        return list(self._all_entries)

    def get_float_window_count(self) -> int:
        """获取浮动窗口数量"""
        return len(self._float_windows)

    def close_all_float_windows(self):
        """关闭所有浮动窗口"""
        for wid, fw in list(self._float_windows.items()):
            if fw.is_alive():
                fw.get_window().destroy()
        self._float_windows.clear()
