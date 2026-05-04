"""集中式主题系统 - 统一管理颜色、字体、间距，支持暗色/亮色双主题"""

DARK = 'dark'
LIGHT = 'light'


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
        """配置 Text widget 的标签（tx/rx/info/time/search）"""
        text_widget.tag_configure('tx', foreground=self.color('tx'))
        text_widget.tag_configure('rx', foreground=self.color('rx'))
        text_widget.tag_configure('info', foreground=self.color('info'))
        text_widget.tag_configure('time', foreground=self.color('time'))
        highlight_bg = self.color('search_highlight_bg')
        highlight_fg = self.color('search_highlight_fg')
        current_bg = self.color('search_current_bg')
        current_fg = self.color('search_current_fg')
        text_widget.tag_configure('search_highlight',
                                  background=highlight_bg, foreground=highlight_fg)
        text_widget.tag_configure('search_current',
                                  background=current_bg, foreground=current_fg)


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

    # 搜索高亮
    'search_highlight_bg': '#ffff00',
    'search_highlight_fg': '#000000',
    'search_current_bg': '#ff8800',
    'search_current_fg': '#000000',

    # 通用
    'gray': 'gray',
    'red': 'red',
    'green': 'green',
    'blue': 'blue',
    'orange': 'orange',
    'black': 'black',
    'white': 'white',
}

# ===== 亮色主题颜色 =====
_LIGHT_COLORS = {
    'bg': '#ffffff',
    'fg': '#1e1e1e',
    'cursor': 'black',
    'selection': '#add6ff',

    'tx': '#0055cc',
    'rx': '#007a33',
    'info': '#b85a00',
    'time': '#888888',

    'search_highlight_bg': '#ffdd00',
    'search_highlight_fg': '#000000',
    'search_current_bg': '#ffaa00',
    'search_current_fg': '#000000',
}

# ===== 默认字体定义 =====
_DEFAULT_FONTS = {
    'monospace': ('Courier New', 10),
    'monospace_large': ('Courier New', 11),
    'monospace_xlarge': ('Courier New', 12),
    'monospace_small': ('Courier New', 9),
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
