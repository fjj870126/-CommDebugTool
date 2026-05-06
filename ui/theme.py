"""集中式主题系统 - 统一管理颜色、字体、间距，支持暗色/亮色双主题"""

DARK = 'dark'
LIGHT = 'light'


class Spacing:
    """间距规范常量，统一全项目内边距"""
    XS = 2   # 紧凑内间距
    SM = 4   # 相关控件间
    MD = 8   # 面板内边距、段落间
    LG = 12  # 段落间距
    XL = 16  # 外间距


class Theme:
    """主题定义类，包含所有 UI 颜色和字体配置"""

    def __init__(self, name: str = DARK):
        self._name = name
        self._colors = _DARK_COLORS.copy()
        self._fonts = _DEFAULT_FONTS.copy()
        if name == LIGHT:
            self._colors.update(_LIGHT_COLORS)

    @property
    def name(self) -> str:
        return self._name

    def color(self, key: str) -> str:
        return self._colors.get(key, _DARK_COLORS.get(key, '#000000'))

    def font(self, key: str) -> tuple:
        return self._fonts.get(key, ('Courier New', 10))

    def configure_text_widget(self, text_widget, font_key: str = 'monospace'):
        """快速配置 Text widget 的主题样式"""
        text_widget.configure(
            bg=self.color('bg'),
            fg=self.color('fg'),
            insertbackground=self.color('cursor'),
            selectbackground=self.color('selection'),
            font=self.font(font_key),
        )

    def configure_tags(self, text_widget):
        """配置 Text widget 的标签（tx/rx/info/warning/error/time/search）"""
        text_widget.tag_configure('tx', foreground=self.color('tx'))
        text_widget.tag_configure('rx', foreground=self.color('rx'))
        text_widget.tag_configure('info', foreground=self.color('info'))
        text_widget.tag_configure('warning', foreground=self.color('warning'))
        text_widget.tag_configure('error', foreground=self.color('error'))
        text_widget.tag_configure('time', foreground=self.color('time'))

        highlight_bg = self.color('search_highlight_bg')
        highlight_fg = self.color('search_highlight_fg')
        current_bg = self.color('search_current_bg')
        current_fg = self.color('search_current_fg')
        text_widget.tag_configure('search_highlight',
                                  background=highlight_bg, foreground=highlight_fg)
        text_widget.tag_configure('search_current',
                                  background=current_bg, foreground=current_fg)

    def configure_float_window(self, text_widget, font_key: str = 'monospace'):
        """配置 FloatWindow 文本区域的主题样式（可能与主 Text 不同）"""
        text_widget.configure(
            bg=self.color('text_bg'),
            fg=self.color('text_fg'),
            insertbackground=self.color('cursor'),
            selectbackground=self.color('selection'),
            font=self.font(font_key),
        )

    def configure_canvas(self, canvas):
        """设置 Canvas 背景色为主题色"""
        canvas.configure(bg=self.color('bg'))


# ===== 暗色主题颜色 =====
_DARK_COLORS = {
    # 基础
    'bg': '#1e1e1e',
    'fg': '#d4d4d4',
    'cursor': 'white',
    'selection': '#264f78',

    # 日志标签
    'tx': '#4fc1ff',
    'rx': '#6a9955',
    'info': '#ce9178',
    'time': '#808080',
    'warning': '#e5c07b',
    'error': '#e74c3c',

    # 搜索高亮
    'search_highlight_bg': '#ffff00',
    'search_highlight_fg': '#000000',
    'search_current_bg': '#ff8800',
    'search_current_fg': '#000000',

    # FloatWindow / 窗口控件
    'title_bg': '#1a1a2e',
    'title_fg': '#e0e0e0',
    'title_button_bg': '#16213e',
    'title_button_hover_bg': '#0f3460',
    'close_button_bg': '#e74c3c',
    'close_button_hover_bg': '#c0392b',
    'toolbar_bg': '#1e1e2e',
    'toolbar_fg': '#c0c0d0',
    'toolbar_label_fg': '#a0a0c0',
    'button_bg': '#2d2d4d',
    'button_hover_bg': '#3d3d5d',
    'button_fg': '#e0e0e0',

    # 文本区域（与基础 bg/fg 不同）
    'text_bg': '#12121e',
    'text_fg': '#d0d0e0',

    # 边框/分隔
    'border_color': '#2a2a4a',

    # 汇总栏
    'summary_bg': '#1a1a2e',
    'summary_fg': '#a0a0c0',

    # 强调/选中
    'accent_bg': '#0f3460',
    'accent_fg': '#ffffff',

    # 通用
    'gray': 'gray',
    'red': 'red',
    'green': 'green',
    'blue': 'blue',
    'orange': 'orange',
    'black': 'black',
    'white': 'white',

    # 语义色
    'diff_bg': '#3d1a1a',
    'diff_fg': '#ff6b6b',
    'same_fg': '#6a9955',
    'missing_fg': 'gray',
    'tooltip_bg': '#333333',
    'tooltip_fg': '#e0e0e0',

    # 波形面板
    'waveform_border': '#555555',
    'waveform_grid': '#333333',
    'waveform_grid_text': '#888888',

    # 面板背景
    'panel_bg': '#f5f5f5',

    # 快捷方式
    'shortcut_bg': '#fafafa',

    # 行号
    'line_no_bg': '#f5f5f5',
    'line_no_fg': '#666666',
}


# ===== 亮色主题颜色 =====
_LIGHT_COLORS = {
    # 基础
    'bg': '#ffffff',
    'fg': '#1e1e1e',
    'cursor': 'black',
    'selection': '#add6ff',

    # 日志标签
    'tx': '#0055cc',
    'rx': '#007a33',
    'info': '#b85a00',
    'time': '#888888',
    'warning': '#cc8800',
    'error': '#cc0000',

    # 搜索高亮
    'search_highlight_bg': '#ffdd00',
    'search_highlight_fg': '#000000',
    'search_current_bg': '#ffaa00',
    'search_current_fg': '#000000',

    # FloatWindow / 窗口控件
    'title_bg': '#e8e8e8',
    'title_fg': '#333333',
    'title_button_bg': '#d0d0d0',
    'title_button_hover_bg': '#b0b0b0',
    'close_button_bg': '#e74c3c',
    'close_button_hover_bg': '#c0392b',
    'toolbar_bg': '#f0f0f0',
    'toolbar_fg': '#444444',
    'toolbar_label_fg': '#666666',
    'button_bg': '#e0e0e0',
    'button_hover_bg': '#d0d0d0',
    'button_fg': '#333333',

    # 文本区域
    'text_bg': '#ffffff',
    'text_fg': '#1e1e1e',

    # 边框/分隔
    'border_color': '#cccccc',

    # 汇总栏
    'summary_bg': '#f5f5f5',
    'summary_fg': '#666666',

    # 强调/选中
    'accent_bg': '#0066cc',
    'accent_fg': '#ffffff',

    # 语义色
    'diff_bg': '#FFE0E0',
    'diff_fg': 'red',
    'same_fg': 'green',
    'missing_fg': 'gray',
    'tooltip_bg': '#ffffe0',
    'tooltip_fg': 'black',

    # 波形面板
    'waveform_border': '#cccccc',
    'waveform_grid': '#e0e0e0',
    'waveform_grid_text': '#888888',

    # 面板背景
    'panel_bg': '#ffffff',

    # 快捷方式
    'shortcut_bg': '#fafafa',

    # 行号
    'line_no_bg': '#f0f0f0',
    'line_no_fg': '#888888',
}


# ===== 默认字体定义 =====
_DEFAULT_FONTS = {
    # 等宽字体
    'monospace': ('Courier New', 10),
    'monospace_large': ('Courier New', 11),
    'monospace_xlarge': ('Courier New', 12),
    'monospace_small': ('Courier New', 9),

    # UI 字体
    'ui': ('', 10),
    'ui_sm': ('', 9),
    'ui_bold': ('', 10, 'bold'),
    'ui_label': ('', 9),
    'ui_label_bold': ('', 9, 'bold'),
    'ui_title': ('', 12, 'bold'),
    'ui_title_large': ('', 14, 'bold'),
}


# ===== 全局单例 =====
_current_theme = Theme(DARK)


def get_theme() -> Theme:
    return _current_theme


def set_theme(name: str):
    global _current_theme
    _current_theme = Theme(name)


def get_theme_names() -> list:
    return [DARK, LIGHT]
