"""协议嗅探面板 - 自动识别常见协议帧头并统计"""

import tkinter as tk
from tkinter import ttk, messagebox
from collections import Counter, defaultdict
from datetime import datetime
from utils.hex_utils import bytes_to_hex_str


# 常见协议帧头特征
PROTOCOL_SIGNATURES = [
    ('Modbus RTU', [0x01, 0x03], '读保持寄存器'),
    ('Modbus RTU', [0x01, 0x06], '写单个寄存器'),
    ('Modbus RTU', [0x01, 0x10], '写多个寄存器'),
    ('Modbus RTU', [0x02, 0x03], '读保持寄存器'),
    ('Modbus RTU', [0x02, 0x06], '写单个寄存器'),
    ('Modbus TCP', [0x00, 0x00, 0x00, 0x00], 'MBAP头'),
    ('Modbus TCP', [0x00, 0x01, 0x00, 0x00], 'MBAP头'),
    ('EtherNet/IP', [0x63, 0x00], '封装头'),
    ('PROFINET', [0x80, 0x00], 'PTCP头'),
    ('CANopen', [0x00, 0x00], 'CAN标识符'),
    ('BACnet', [0x81, 0x0a], 'BACnet/IP'),
    ('MQTT', [0x10], 'CONNECT'),
    ('MQTT', [0x30], 'PUBLISH'),
    ('HTTP', [0x47, 0x45, 0x54], 'GET'),
    ('HTTP', [0x50, 0x4f, 0x53, 0x54], 'POST'),
    ('HTTP', [0x48, 0x54, 0x54, 0x50], 'HTTP/'),
]


class SnifferPanel(ttk.LabelFrame):
    """协议嗅探面板"""

    def __init__(self, parent, log_panel=None):
        super().__init__(parent, text=' 协议嗅探 ', padding=8)
        self._log_panel = log_panel
        self._sniffing = False
        self._packet_count = 0
        self._protocol_counter = Counter()
        self._unknown_counter = 0
        self._build_ui()

    def _build_ui(self):
        # 工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 4))

        self.sniff_btn = ttk.Button(toolbar, text='🔍 开始嗅探', command=self._toggle_sniff, width=12)
        self.sniff_btn.pack(side=tk.LEFT, padx=(0, 4))

        ttk.Button(toolbar, text='清空统计', command=self._clear_stats, width=8).pack(side=tk.LEFT, padx=2)

        self.packet_count_var = tk.StringVar(value='数据包: 0')
        ttk.Label(toolbar, textvariable=self.packet_count_var, foreground='gray').pack(side=tk.RIGHT)

        # 协议统计
        stats_frame = ttk.LabelFrame(self, text=' 协议统计 ', padding=4)
        stats_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('protocol', 'count', 'percent', 'sample')
        self.stats_tree = ttk.Treeview(stats_frame, columns=columns, show='headings', height=6)
        self.stats_tree.heading('protocol', text='协议')
        self.stats_tree.heading('count', text='数量')
        self.stats_tree.heading('percent', text='占比')
        self.stats_tree.heading('sample', text='样本数据')

        self.stats_tree.column('protocol', width=100, minwidth=60)
        self.stats_tree.column('count', width=60, minwidth=40, anchor=tk.CENTER)
        self.stats_tree.column('percent', width=60, minwidth=40, anchor=tk.CENTER)
        self.stats_tree.column('sample', width=200, minwidth=80)

        tree_scroll = ttk.Scrollbar(stats_frame, orient=tk.VERTICAL, command=self.stats_tree.yview)
        self.stats_tree.configure(yscrollcommand=tree_scroll.set)

        self.stats_tree.grid(row=0, column=0, sticky='nsew')
        tree_scroll.grid(row=0, column=1, sticky='ns')
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.rowconfigure(0, weight=1)

        # 实时嗅探日志
        log_frame = ttk.LabelFrame(self, text=' 嗅探日志 ', padding=4)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        self.log_text = tk.Text(log_frame, height=6, font=('Courier New', 9),
                                wrap=tk.NONE, state=tk.DISABLED)
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        self.log_text.grid(row=0, column=0, sticky='nsew')
        log_scroll.grid(row=0, column=1, sticky='ns')
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        # 配置日志标签
        self.log_text.tag_configure('known', foreground='green')
        self.log_text.tag_configure('unknown', foreground='gray')

    def _toggle_sniff(self):
        """切换嗅探状态"""
        self._sniffing = not self._sniffing
        if self._sniffing:
            self.sniff_btn.configure(text='⏹ 停止嗅探')
            self._add_log('▶ 协议嗅探已启动', 'known')
        else:
            self.sniff_btn.configure(text='🔍 开始嗅探')
            self._add_log('⏹ 协议嗅探已停止', 'unknown')

    def sniff_data(self, data: bytes):
        """嗅探一条数据"""
        if not self._sniffing or not data:
            return

        self._packet_count += 1
        self.packet_count_var.set(f'数据包: {self._packet_count}')

        # 识别协议
        protocol = self._identify_protocol(data)
        if protocol:
            self._protocol_counter[protocol] += 1
            self._add_log(f'[{datetime.now().strftime("%H:%M:%S")}] {protocol}', 'known')
        else:
            self._unknown_counter += 1
            if self._packet_count <= 10:  # 只显示前10个未知包
                hex_preview = bytes_to_hex_str(data[:8])
                self._add_log(f'[{datetime.now().strftime("%H:%M:%S")}] 未知协议: {hex_preview}...', 'unknown')

        # 更新统计
        self._refresh_stats()

    def _identify_protocol(self, data: bytes) -> str:
        """识别协议"""
        for proto_name, signature, desc in PROTOCOL_SIGNATURES:
            if len(data) >= len(signature):
                if list(data[:len(signature)]) == signature:
                    return f'{proto_name} ({desc})'
        return ''

    def _refresh_stats(self):
        """刷新统计列表"""
        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)

        total = self._packet_count
        if total == 0:
            return

        # 按数量排序
        sorted_protocols = sorted(self._protocol_counter.items(), key=lambda x: -x[1])

        for proto, count in sorted_protocols:
            percent = count / total * 100
            self.stats_tree.insert('', tk.END, values=(
                proto,
                count,
                f'{percent:.1f}%',
                ''
            ))

        # 添加未知协议
        if self._unknown_counter > 0:
            percent = self._unknown_counter / total * 100
            self.stats_tree.insert('', tk.END, values=(
                '未知协议',
                self._unknown_counter,
                f'{percent:.1f}%',
                ''
            ))

    def _clear_stats(self):
        """清空统计"""
        self._packet_count = 0
        self._protocol_counter.clear()
        self._unknown_counter = 0
        self.packet_count_var.set('数据包: 0')
        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _add_log(self, text: str, tag: str = ''):
        """添加日志"""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + '\n', tag)
        # 限制日志行数
        lines = self.log_text.get('1.0', tk.END).count('\n')
        if lines > 100:
            self.log_text.delete('1.0', '2.0')
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def get_settings(self) -> dict:
        return {
            'sniffing': self._sniffing,
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        if settings.get('sniffing'):
            self._toggle_sniff()
