"""树形导航面板 - 替代 Notebook 标签页，左侧树形导航 + 右侧内容区"""

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont


class TreeNavPanel(ttk.Frame):
    """树形导航面板：左侧紧凑导航树，右侧为工具面板容器"""

    NAV_STRUCTURE = [
        ('📤 发送', [
            '快捷发送', '文件发送', '协议解析', '协议编辑器',
        ]),
        ('🔧 数据处理', [
            '转换器', '校验和', '格式化', '编码', 'Base64',
        ]),
        ('🧪 测试', [
            '压力测试', '脚本', '定时任务', '录制', '随机数据',
        ]),
        ('📊 监控', [
            '告警', '波形', '统计', '嗅探', '回放', '对比',
        ]),
        ('🛠 辅助工具', [
            '正则', '时间戳', 'ASCII', '位操作', '备注', '导出',
        ]),
        ('🌐 网络', [
            '隧道', '心跳', '自动回复',
        ]),
    ]

    PANEL_KEY_MAP = {}
    for _parent, children in NAV_STRUCTURE:
        for child in children:
            PANEL_KEY_MAP[child] = child

    PANEL_DESCS = {
        '快捷发送': '选择编码与模式 | 查看长度统计 | Ctrl+Enter 快速发送 | 支持历史与快捷指令',
        '文件发送': '选择文件并按格式发送 | 支持循环发送和定时发送',
        '协议解析': '根据字段定义解析 HEX 数据 | 支持多种数据类型',
        '协议编辑器': '编辑和管理自定义协议模板 | 组包、发送、导入导出',
        '转换器': 'HEX/ASCII/十进制/二进制/字节互转',
        '校验和': '计算累加和、CRC8/16/32、异或校验等',
        '格式化': '格式化 JSON/XML 数据 | 支持缩进和压缩',
        '编码': 'URL 编码/解码、HTML 转义、Unicode 转义',
        'Base64': 'Base64 编解码 | 支持文件和字符串模式',
        '压力测试': '指定频率和次数发送数据 | 测试设备吞吐量',
        '脚本': 'Python 脚本自动化发送和数据处理',
        '定时任务': '定时周期发送数据 | 支持单次和重复任务',
        '录制': '录制操作步骤并导出为脚本 | 支持回放',
        '随机数据': '生成随机 HEX/ASCII 数据 | 可指定长度和数量',
        '告警': '设置数据匹配规则 | 匹配时触发弹窗或日志告警',
        '波形': '实时显示数据收发波形图',
        '统计': '统计收发数据量、频率、速率等指标',
        '嗅探': '自动识别常见协议类型 | 分析协议特征',
        '回放': '导出和导入收发记录 | 回放历史数据',
        '对比': '对比两段 HEX/ASCII 数据差异',
        '正则': '测试正则表达式匹配 | 实时高亮匹配结果',
        '时间戳': '时间戳与日期时间互转 | 支持多种格式',
        'ASCII': 'ASCII 码表查询 | 十六进制与字符对照',
        '位操作': '位与、位或、位移、取反等位运算',
        '备注': '添加和管理备注信息 | 支持多条记录',
        '隧道': 'TCP 端口转发 | 支持本地和远程转发',
        '心跳': '定时发送心跳包 | 自动检测断线重连',
        '自动回复': '根据接收数据自动回复 | 支持多条规则',
        '导出': '导出日志到文件 | TXT/CSV/HTML 格式',
    }

    def __init__(self, parent, on_select=None):
        super().__init__(parent)
        self._on_select = on_select

        # ========== 顶部说明区域 ==========
        desc_frame = ttk.Frame(self)
        desc_frame.pack(fill=tk.X, pady=(0, 2))

        ttk.Label(
            desc_frame,
            text='工具栏',
            font=tkfont.nametofont('TkCaptionFont'),
            foreground='#3a3a3a',
        ).pack(side=tk.LEFT)

        self._desc_label = ttk.Label(
            desc_frame,
            text='',
            font=('', 9),
            foreground='#333333',
        )
        self._desc_label.pack(side=tk.LEFT, padx=(8, 0))

        # 水平分割：导航树 | 内容区
        self._paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self._paned.pack(fill=tk.BOTH, expand=True)

        # 左侧：导航树（固定较窄宽度）
        nav_frame = ttk.Frame(self._paned, width=150)
        self._paned.add(nav_frame, weight=0)

        self._tree = ttk.Treeview(nav_frame, show='tree', height=10, selectmode='browse')
        # 设置列宽，允许适当拉伸
        self._tree.column('#0', width=130, minwidth=100, stretch=True)
        tree_scroll = ttk.Scrollbar(nav_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=tree_scroll.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._build_tree()
        self._tree.bind('<<TreeviewSelect>>', self._on_tree_select)

        # 右侧：工具面板容器（由外部创建并设置）
        self._content_frame = ttk.Frame(self._paned)
        self._paned.add(self._content_frame, weight=6)
        # 禁止几何传播，固定内容区高度，避免面板切换时高度变化
        self._content_frame.pack_propagate(False)

        self._tools_container = None

    def set_tools_container(self, container):
        self._tools_container = container
        container.pack(in_=self._content_frame, fill=tk.BOTH, expand=True)

    def _build_tree(self):
        for parent_name, children in self.NAV_STRUCTURE:
            parent_id = self._tree.insert('', tk.END, text=parent_name, open=True)
            for child_name in children:
                self._tree.insert(parent_id, tk.END, text=child_name, open=False)

    def _on_tree_select(self, event):
        sel = self._tree.selection()
        if not sel:
            return
        item = sel[0]
        text = self._tree.item(item, 'text')
        parent = self._tree.parent(item)
        if not parent:
            return
        if self._on_select:
            panel_key = self.PANEL_KEY_MAP.get(text, text)
            self._on_select(panel_key)
            if self._tools_container:
                self._tools_container.switch_to_panel(panel_key)
            desc = self.PANEL_DESCS.get(text, '')
            self._desc_label.configure(text=f'📝 {desc}' if desc else '')
