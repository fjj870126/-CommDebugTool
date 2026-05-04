"""MQTT 独立窗口"""

import tkinter as tk
from tkinter import ttk
from comm.mqtt_comm import MqttComm
from ui.mqtt_panel import MqttPanel


class MqttWindow(tk.Toplevel):
    """MQTT 客户端独立窗口"""

    def __init__(self, parent, log_panel=None, on_send=None):
        super().__init__(parent)
        self.title('MQTT 客户端')
        self.minsize(1000, 500)
        self.withdraw()

        # 创建 MQTT 通信对象
        self._mqtt = MqttComm()

        # ===== 使用 PanedWindow 左右分割 =====
        self._main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self._main_paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 左侧：控制面板（连接配置、发布、订阅、转发等）- 占 50%
        left_frame = ttk.Frame(self._main_paned)
        self._main_paned.add(left_frame, weight=50)

        # 右侧：消息列表 - 占 50%
        right_frame = ttk.Frame(self._main_paned)
        self._main_paned.add(right_frame, weight=50)

        # 创建 MQTT 面板（左侧控制区）
        self._panel = MqttPanel(left_frame, on_send=on_send, log_panel=log_panel)
        self._panel.set_mqtt(self._mqtt)
        self._panel.pack(fill=tk.BOTH, expand=True)

        # 创建消息列表面板（右侧）
        self._build_message_panel(right_frame)

        # 延迟设置默认分割位置（左侧约50%），等待窗口布局完成
        self.after(100, lambda: self._set_initial_sash(self._main_paned))

        # 居中后显示
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        w, h = 1400, 800
        self.geometry(f'{w}x{h}+{px + (pw - w) // 2}+{py + (ph - h) // 2}')
        self.deiconify()

        # 关闭窗口时断开连接
        self.protocol('WM_DELETE_WINDOW', self._on_close)

        # 窗口关闭标志
        self._closed = False

    def _set_initial_sash(self, paned, ratio=None):
        """设置初始分割位置（左侧约50%，或使用指定比例）"""
        try:
            self.update_idletasks()
            total_width = paned.winfo_width()
            if total_width > 100:
                if ratio is not None and 0 < ratio < 1:
                    paned.sashpos(0, int(total_width * ratio))
                else:
                    paned.sashpos(0, int(total_width * 0.50))
        except Exception:
            pass

    def _build_message_panel(self, parent):
        """构建右侧消息列表面板"""
        # ===== 消息列表 =====
        msg_frame = ttk.LabelFrame(parent, text=' 消息列表 ', padding=6)
        msg_frame.pack(fill=tk.BOTH, expand=True)

        # 过滤栏
        filter_frame = ttk.Frame(msg_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(filter_frame, text='主题过滤:').pack(side=tk.LEFT)
        self._filter_topic_var = tk.StringVar(value='')
        self._filter_topic_var.trace_add('write', lambda *_: self._panel.apply_filter())
        filter_topic_entry = ttk.Entry(filter_frame, textvariable=self._filter_topic_var, width=18)
        filter_topic_entry.pack(side=tk.LEFT, padx=(4, 8))

        ttk.Label(filter_frame, text='内容过滤:').pack(side=tk.LEFT)
        self._filter_content_var = tk.StringVar(value='')
        self._filter_content_var.trace_add('write', lambda *_: self._panel.apply_filter())
        filter_content_entry = ttk.Entry(filter_frame, textvariable=self._filter_content_var, width=18)
        filter_content_entry.pack(side=tk.LEFT, padx=(4, 8))

        ttk.Button(filter_frame, text='清除过滤', command=self._clear_filter, width=8).pack(side=tk.LEFT, padx=(0, 4))

        # 消息统计
        self._stats_label = ttk.Label(filter_frame, text='', font=('', 9))
        self._stats_label.pack(side=tk.RIGHT, padx=(4, 0))

        # 工具栏
        msg_toolbar = ttk.Frame(msg_frame)
        msg_toolbar.pack(fill=tk.X, pady=(0, 4))
        self._msg_count_label = ttk.Label(msg_toolbar, text='共 0 条消息', font=('', 9))
        self._msg_count_label.pack(side=tk.LEFT)
        ttk.Button(msg_toolbar, text='导出CSV', command=self._panel.export_csv, width=8).pack(side=tk.RIGHT, padx=(2, 0))
        ttk.Button(msg_toolbar, text='导出TXT', command=self._panel.export_txt, width=8).pack(side=tk.RIGHT, padx=(2, 0))
        ttk.Button(msg_toolbar, text='导出JSON', command=self._panel.export_json, width=8).pack(side=tk.RIGHT, padx=(2, 0))
        ttk.Button(msg_toolbar, text='清除', command=self._clear_messages, width=6).pack(side=tk.RIGHT, padx=(2, 0))

        # 消息表格
        msg_table_frame = ttk.Frame(msg_frame)
        msg_table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('time', 'topic', 'qos', 'payload_hex', 'payload_text')
        self._msg_tree = ttk.Treeview(msg_table_frame, columns=columns, show='headings',
                                      selectmode='browse', height=8)
        self._msg_tree.heading('time', text='时间')
        self._msg_tree.heading('topic', text='主题')
        self._msg_tree.heading('qos', text='QoS')
        self._msg_tree.heading('payload_hex', text='数据(Hex)')
        self._msg_tree.heading('payload_text', text='数据(文本)')

        self._msg_tree.column('time', width=80, minwidth=60, anchor=tk.CENTER)
        self._msg_tree.column('topic', width=150, minwidth=80)
        self._msg_tree.column('qos', width=40, minwidth=30, anchor=tk.CENTER)
        self._msg_tree.column('payload_hex', width=200, minwidth=80)
        self._msg_tree.column('payload_text', width=200, minwidth=80)

        msg_vscroll = ttk.Scrollbar(msg_table_frame, orient=tk.VERTICAL, command=self._msg_tree.yview)
        msg_hscroll = ttk.Scrollbar(msg_table_frame, orient=tk.HORIZONTAL, command=self._msg_tree.xview)
        self._msg_tree.configure(yscrollcommand=msg_vscroll.set, xscrollcommand=msg_hscroll.set)

        self._msg_tree.grid(row=0, column=0, sticky='nsew')
        msg_vscroll.grid(row=0, column=1, sticky='ns')
        msg_hscroll.grid(row=1, column=0, sticky='ew')
        msg_table_frame.rowconfigure(0, weight=1)
        msg_table_frame.columnconfigure(0, weight=1)

        # 双击消息显示详情
        self._msg_tree.bind('<Double-1>', self._on_msg_double_click)

        # 将消息树引用传递给 panel
        self._panel.set_msg_tree(self._msg_tree, self._msg_count_label, self._stats_label,
                                 self._filter_topic_var, self._filter_content_var)

    def _clear_filter(self):
        """清除过滤条件"""
        self._filter_topic_var.set('')
        self._filter_content_var.set('')

    def _clear_messages(self):
        """清除消息列表"""
        self._panel.clear_messages()

    def _on_msg_double_click(self, event):
        """双击消息显示详情"""
        sel = self._msg_tree.selection()
        if not sel:
            return
        item = self._msg_tree.item(sel[0])
        values = item['values']
        if len(values) < 5:
            return

        detail = (
            f'时间: {values[0]}\n'
            f'主题: {values[1]}\n'
            f'QoS: {values[2]}\n'
            f'Hex: {values[3]}\n'
            f'文本: {values[4]}'
        )
        if self._panel._log_panel:
            self._panel._log_panel.log_info(f'[MQTT] 消息详情:\n{detail}')

    @property
    def closed(self) -> bool:
        return self._closed

    def load_settings(self, settings: dict):
        """加载配置"""
        if self._panel:
            self._panel.load_settings(settings)
        # 恢复 PanedWindow 分割比例（延迟执行，等待窗口布局完成）
        sash_ratio = settings.get('sash_ratio') if settings else None
        if sash_ratio is not None and 0 < sash_ratio < 1:
            self.after(200, lambda: self._set_initial_sash(self._main_paned, sash_ratio))
        else:
            # 没有保存的比例时，使用默认比例（左侧约50%）
            self.after(200, lambda: self._set_initial_sash(self._main_paned))

    def get_settings(self) -> dict:
        """获取配置"""
        settings = {}
        if self._panel:
            settings = self._panel.get_settings()
        # 保存 PanedWindow 分割比例
        try:
            total_width = self._main_paned.winfo_width()
            if total_width > 0:
                sash_pos = self._main_paned.sashpos(0)
                settings['sash_ratio'] = sash_pos / total_width
        except Exception:
            pass
        return settings

    def _on_close(self):
        """关闭窗口"""
        self._closed = True
        if self._mqtt:
            self._mqtt.disconnect()
        self.destroy()
