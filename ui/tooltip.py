import tkinter as tk


class ToolTip:
    def __init__(self, widget, text_func=None):
        self.widget = widget
        self.text_func = text_func
        self.tip_window = None
        widget.bind('<Enter>', self._show)
        widget.bind('<Leave>', self._hide)

    def _show(self, event=None):
        if self.tip_window:
            return
        text = self.text_func() if self.text_func else ''
        if not text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f'+{x}+{y}')
        label = tk.Label(tw, text=text, justify=tk.LEFT,
                         background='#ffffe0', foreground='black',
                         relief=tk.SOLID, borderwidth=1,
                         font=('', 9), padx=6, pady=4)
        label.pack()

    def _hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None
