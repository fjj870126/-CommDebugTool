"""ASCII 码表 - 快速查看 ASCII 字符的 Hex/Dec/Bin 对应关系"""

import tkinter as tk
from tkinter import ttk
from ui.theme import get_theme


class AsciiTable(ttk.LabelFrame):
    """ASCII 码表"""

    def __init__(self, parent):
        super().__init__(parent, text=' ASCII 码表 ', padding=8)
        self._build_ui()

    def _build_ui(self):
        # ===== 搜索过滤 =====
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(search_frame, text='搜索:', font=('', 12)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var,
                                      font=('Courier New', 12), width=20)
        self.search_entry.pack(side=tk.LEFT, padx=(4, 8), fill=tk.X, expand=True)
        self.search_var.trace_add('write', lambda *args: self._apply_filter())

        # 显示选项
        self.show_ctrl = tk.BooleanVar(value=True)
        ttk.Checkbutton(search_frame, text='控制字符(0-31,127)', variable=self.show_ctrl,
                        command=self._apply_filter).pack(side=tk.LEFT, padx=2)
        self.show_ext = tk.BooleanVar(value=False)
        ttk.Checkbutton(search_frame, text='扩展(128-255)', variable=self.show_ext,
                        command=self._apply_filter).pack(side=tk.LEFT, padx=2)

        # ===== 表格 =====
        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('dec', 'hex', 'bin', 'char', 'desc')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                 height=20)
        self.tree.heading('dec', text='Decimal')
        self.tree.heading('hex', text='Hex')
        self.tree.heading('bin', text='Binary')
        self.tree.heading('char', text='字符')
        self.tree.heading('desc', text='描述')

        self.tree.column('dec', width=70, minwidth=60, anchor=tk.CENTER)
        self.tree.column('hex', width=50, minwidth=40, anchor=tk.CENTER)
        self.tree.column('bin', width=100, minwidth=80, anchor=tk.CENTER)
        self.tree.column('char', width=60, minwidth=40, anchor=tk.CENTER)
        self.tree.column('desc', width=220, minwidth=100, anchor=tk.W)

        # 设置字体
        style = ttk.Style()
        style.configure('Ascii.Treeview', font=('Courier New', 11), rowheight=24)
        style.configure('Ascii.Treeview.Heading', font=('', 11, 'bold'))
        self.tree.configure(style='Ascii.Treeview')

        vscroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hscroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        vscroll.grid(row=0, column=1, sticky='ns')
        hscroll.grid(row=1, column=0, sticky='ew')
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        # 双击复制字符
        self.tree.bind('<Double-1>', self._on_double_click)

        # 状态栏
        self.status_var = tk.StringVar(value='就绪')
        ttk.Label(self, textvariable=self.status_var, foreground='gray').pack(anchor=tk.W, pady=(4, 0))

        # 加载数据
        self._load_data()

    def _get_ascii_desc(self, code: int) -> str:
        """获取 ASCII 字符描述"""
        descriptions = {
            0: 'NUL (空字符)', 1: 'SOH (标题开始)', 2: 'STX (正文开始)',
            3: 'ETX (正文结束)', 4: 'EOT (传输结束)', 5: 'ENQ (询问)',
            6: 'ACK (确认)', 7: 'BEL (响铃)', 8: 'BS (退格)',
            9: 'TAB (水平制表符)', 10: 'LF (换行)', 11: 'VT (垂直制表符)',
            12: 'FF (换页)', 13: 'CR (回车)', 14: 'SO (移出)',
            15: 'SI (移入)', 16: 'DLE (数据链路转义)', 17: 'DC1 (设备控制1)',
            18: 'DC2 (设备控制2)', 19: 'DC3 (设备控制3)', 20: 'DC4 (设备控制4)',
            21: 'NAK (否定确认)', 22: 'SYN (同步空闲)', 23: 'ETB (块传输结束)',
            24: 'CAN (取消)', 25: 'EM (介质结束)', 26: 'SUB (替换)',
            27: 'ESC (转义)', 28: 'FS (文件分隔符)', 29: 'GS (组分隔符)',
            30: 'RS (记录分隔符)', 31: 'US (单元分隔符)', 32: 'SP (空格)',
            127: 'DEL (删除)',
        }
        return descriptions.get(code, '')

    def _get_char_display(self, code: int) -> str:
        """获取字符显示"""
        if code == 32:
            return '␣'
        if code == 127:
            return '⌂'
        if 0 <= code <= 31:
            return f'[{code:02X}]'
        if 128 <= code <= 255:
            return f'\\x{code:02X}'
        return chr(code)

    def _load_data(self):
        """加载 ASCII 数据"""
        self._all_data = []
        for i in range(256):
            desc = self._get_ascii_desc(i)
            char = self._get_char_display(i)
            self._all_data.append({
                'dec': i,
                'hex': f'{i:02X}',
                'bin': f'{i:08b}',
                'char': char,
                'desc': desc,
                'is_ctrl': i < 32 or i == 127,
            })
        self._apply_filter()

    def _apply_filter(self):
        """应用过滤"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        search = self.search_var.get().strip().lower()
        show_ctrl = self.show_ctrl.get()
        show_ext = self.show_ext.get()

        # 配置标签
        self.tree.tag_configure('ctrl', foreground=get_theme().color('gray'))
        self.tree.tag_configure('printable', foreground=get_theme().color('fg'))
        self.tree.tag_configure('ext', foreground=get_theme().color('blue'))
        self.tree.tag_configure('highlight', background=get_theme().color('search_highlight_bg'))

        count = 0
        for data in self._all_data:
            # 过滤控制字符
            if data['is_ctrl'] and not show_ctrl:
                continue
            # 过滤扩展字符
            if data['dec'] >= 128 and not show_ext:
                continue

            # 搜索过滤
            if search:
                if (search not in str(data['dec']) and
                    search not in data['hex'].lower() and
                    search not in data['bin'] and
                    search not in data['char'].lower() and
                    search not in data['desc'].lower()):
                    continue

            # 选择标签
            if data['is_ctrl']:
                tag = 'ctrl'
            elif data['dec'] >= 128:
                tag = 'ext'
            else:
                tag = 'printable'

            self.tree.insert('', tk.END, iid=str(data['dec']),
                             values=(data['dec'], data['hex'], data['bin'],
                                     data['char'], data['desc']),
                             tags=(tag,))
            count += 1

        self.status_var.set(f'显示 {count} 个字符 (共 256 个)')

    def _on_double_click(self, event):
        """双击复制字符"""
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        values = item['values']
        if not values:
            return

        # 复制 Hex 值
        hex_val = values[1]
        try:
            self.winfo_toplevel().clipboard_clear()
            self.winfo_toplevel().clipboard_append(hex_val)
            self.status_var.set(f'已复制 Hex: {hex_val}')
        except Exception:
            pass

    def get_settings(self) -> dict:
        return {
            'show_ctrl': self.show_ctrl.get(),
            'show_ext': self.show_ext.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        self.show_ctrl.set(settings.get('show_ctrl', True))
        self.show_ext.set(settings.get('show_ext', False))
