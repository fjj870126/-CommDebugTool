import tkinter as tk
import tkinter.font as tkfont
from ui.theme import get_theme


class ToolTip:
    def __init__(self, widget, text_func=None):
        self.widget = widget
        self.text_func = text_func
        self.tip_window = None
        self._timer = None
        widget.bind('<Enter>', self._on_enter)
        widget.bind('<Leave>', self._hide)

    def _on_enter(self, event=None):
        # 延迟 300ms 再显示，避免鼠标滑过时闪烁
        if self._timer:
            try:
                self.widget.after_cancel(self._timer)
            except Exception:
                pass
        self._event = event
        self._timer = self.widget.after(300, self._show)

    def _show(self):
        if self.tip_window:
            return
        text = self.text_func() if self.text_func else ''
        if not text:
            return
        # 用字体度量估算弹窗高度
        font = tkfont.Font(font=('', 9))
        line_h = font.metrics('linespace') + 8
        line_count = text.count('\n') + 1
        tip_h = line_count * line_h + 8

        # 弹窗在控件上方或下方居中
        widget_x = self.widget.winfo_rootx()
        widget_w = self.widget.winfo_width()
        x = widget_x + widget_w // 2 - 60
        screen_h = self.widget.winfo_screenheight()
        below_y = self.widget.winfo_rooty() + self.widget.winfo_height() + 1
        if below_y + tip_h > screen_h:
            y = self.widget.winfo_rooty() - tip_h - 1
        else:
            y = below_y

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f'+{x}+{y}')
        label = tk.Label(tw, text=text, justify=tk.LEFT,
                         background=get_theme().color('tooltip_bg'),
                         foreground=get_theme().color('tooltip_fg'),
                         relief=tk.SOLID, borderwidth=1,
                         font=('', 9), padx=6, pady=4)
        label.pack()

    def _hide(self, event=None):
        if self._timer:
            try:
                self.widget.after_cancel(self._timer)
            except Exception:
                pass
            self._timer = None
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None
