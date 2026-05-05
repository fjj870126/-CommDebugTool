"""工具集容器 - 树形导航驱动的面板容器，直接管理面板 pack，无 Notebook"""

import tkinter as tk
from tkinter import ttk
from ui.converter_panel import ConverterPanel
from ui.replay_panel import ReplayPanel
from ui.alert_panel import AlertPanel
from ui.waveform_panel import WaveformPanel
from ui.stats_panel import StatsPanel
from ui.stress_test_panel import StressTestPanel
from ui.file_send_panel import FileSendPanel
from ui.script_panel import ScriptPanel
from ui.checksum_panel import ChecksumPanel
from ui.export_panel import ExportPanel
from ui.heartbeat_panel import HeartbeatPanel
from ui.send_panel import SendPanel
from ui.compare_panel import ComparePanel
from ui.sniffer_panel import SnifferPanel
from ui.annotation_panel import AnnotationPanel
from ui.scheduler_panel import SchedulerPanel
from ui.tunnel_panel import TunnelPanel
from ui.formatter_panel import FormatterPanel
from ui.recorder_panel import RecorderPanel
from ui.protocol_editor import ProtocolEditor
from ui.parse_panel import ParsePanel
from ui.base64_panel import Base64Panel
from ui.regex_tester import RegexTester
from ui.timestamp_panel import TimestampPanel
from ui.random_generator import RandomGenerator
from ui.ascii_table import AsciiTable
from ui.encoding_panel import EncodingPanel
from ui.bitwise_panel import BitwisePanel
from ui.auto_reply_panel import AutoReplyPanel
from ui.json_viewer import JsonViewer


class ToolsContainer(ttk.Frame):
    """工具集容器 - 懒加载+grid重叠布局，切换仅改变z-order"""

    PANEL_MAP = {
        '快捷发送': 'send_panel',
        '文件发送': 'file_send_panel',
        '协议解析': 'parse_panel',
        '协议编辑器': 'protocol_editor',
        '转换器': 'converter_panel',
        '校验和': 'checksum_panel',
        '格式化': 'formatter_panel',
        '编码': 'encoding_panel',
        'Base64': 'base64_panel',
        '压力测试': 'stress_test_panel',
        '脚本': 'script_panel',
        '定时任务': 'scheduler_panel',
        '录制': 'recorder_panel',
        '随机数据': 'random_generator',
        '告警': 'alert_panel',
        '波形': 'waveform_panel',
        '统计': 'stats_panel',
        '嗅探': 'sniffer_panel',
        '回放': 'replay_panel',
        '对比': 'compare_panel',
        '正则': 'regex_tester',
        '时间戳': 'timestamp_panel',
        'ASCII': 'ascii_table',
        '位操作': 'bitwise_panel',
        '备注': 'annotation_panel',
        'JSON查看器': 'json_viewer',
        '隧道': 'tunnel_panel',
        '心跳': 'heartbeat_panel',
        '导出': 'export_panel',
        '自动回复': 'auto_reply_panel',
    }

    def __init__(self, parent, on_send=None, log_panel=None, main_window=None):
        super().__init__(parent)
        self._current_panel = None
        self._current_panel_name = None
        self._on_send_silent = getattr(main_window, '_send_data_silent', None) if main_window else None
        self._on_send = on_send
        self._log_panel = log_panel
        self._main_window = main_window
        
        # 配置 grid：单单元格，所有面板重叠于此
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # 延迟加载：面板工厂映射
        self._panel_factories = {
            'send_panel': lambda: SendPanel(self, on_send=on_send),
            'file_send_panel': lambda: FileSendPanel(self, on_send=on_send),
            'parse_panel': lambda: ParsePanel(self, on_send=on_send, log_panel=log_panel),
            'protocol_editor': lambda: ProtocolEditor(self, on_send=on_send, log_panel=log_panel, parse_panel=self._get_or_create('parse_panel')),
            'converter_panel': lambda: ConverterPanel(self),
            'checksum_panel': lambda: ChecksumPanel(self),
            'formatter_panel': lambda: FormatterPanel(self, log_panel=log_panel),
            'encoding_panel': lambda: EncodingPanel(self),
            'base64_panel': lambda: Base64Panel(self),
            'stress_test_panel': lambda: StressTestPanel(self, on_send=on_send),
            'script_panel': lambda: ScriptPanel(self, on_send=on_send, log_panel=log_panel),
            'scheduler_panel': lambda: SchedulerPanel(self, on_send=on_send, log_panel=log_panel),
            'recorder_panel': lambda: RecorderPanel(self, on_send=on_send, log_panel=log_panel),
            'random_generator': lambda: RandomGenerator(self, on_send=on_send),
            'alert_panel': lambda: AlertPanel(self, log_panel=log_panel),
            'waveform_panel': lambda: WaveformPanel(self),
            'stats_panel': lambda: StatsPanel(self),
            'sniffer_panel': lambda: SnifferPanel(self, log_panel=log_panel),
            'replay_panel': lambda: ReplayPanel(self, on_send=on_send, log_panel=log_panel),
            'compare_panel': lambda: ComparePanel(self),
            'regex_tester': lambda: RegexTester(self),
            'timestamp_panel': lambda: TimestampPanel(self),
            'ascii_table': lambda: AsciiTable(self),
            'bitwise_panel': lambda: BitwisePanel(self),
            'annotation_panel': lambda: AnnotationPanel(self, log_panel=log_panel),
            'json_viewer': lambda: JsonViewer(self, log_panel=log_panel),
            'tunnel_panel': lambda: TunnelPanel(self, log_panel=log_panel),
            'heartbeat_panel': lambda: HeartbeatPanel(self, on_send=on_send),
            'export_panel': lambda: ExportPanel(self, log_panel=log_panel),
            'auto_reply_panel': lambda: AutoReplyPanel(self, on_send=on_send, log_panel=log_panel),
        }
        
        # 已创建的面板缓存
        self._panels = {}
        
        # 初始显示"快捷发送"面板
        self.after(0, lambda: self.switch_to_panel('快捷发送'))

    def get_send_panel(self):
        return self._get_or_create('send_panel')

    def _get_or_create(self, attr_name: str):
        """获取或创建面板（懒加载）"""
        if attr_name not in self._panels:
            factory = self._panel_factories.get(attr_name)
            if factory:
                panel = factory()
                # 设置静默发送回调
                if hasattr(panel, '_on_send_silent'):
                    panel._on_send_silent = self._on_send_silent
                if attr_name == 'stress_test_panel':
                    panel._on_send_silent = self._on_send_silent
                elif attr_name == 'script_panel':
                    panel._on_send_silent = self._on_send_silent
                
                # 使用 grid 放置到重叠位置，之后只通过 tkraise 切换
                panel.grid(row=0, column=0, sticky='nsew')
                panel.lower()  # 初始置于底层
                self._panels[attr_name] = panel
        return self._panels.get(attr_name)

    def __getattr__(self, name: str):
        """属性访问自动触发懒加载"""
        # 支持 known 面板别名
        if name in self._panel_factories:
            return self._get_or_create(name)
        # 允许访问已创建的面板缓存
        if name in self._panels:
            return self._panels[name]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def switch_to_panel(self, panel_name: str) -> bool:
        attr_name = self.PANEL_MAP.get(panel_name)
        if not attr_name:
            return False

        panel = self._get_or_create(attr_name)
        if not panel:
            return False

        if self._current_panel is panel:
            panel.tkraise()
            return True

        if self._current_panel is not None:
            self._current_panel.lower()

        panel.tkraise()
        self._current_panel = panel
        self._current_panel_name = panel_name
        return True

    def get_settings(self) -> dict:
        settings = {}
        if self._current_panel_name:
            settings['_current_panel'] = self._current_panel_name

        send_panel = self._get_or_create('send_panel')
        if send_panel and hasattr(send_panel, 'get_settings'):
            settings['send'] = send_panel.get_settings()
        
        alert_panel = self._get_or_create('alert_panel')
        if alert_panel and hasattr(alert_panel, 'get_settings'):
            settings['alert'] = alert_panel.get_settings()

        parse_panel = self._get_or_create('parse_panel')
        if parse_panel and hasattr(parse_panel, 'get_settings'):
            settings['parse'] = parse_panel.get_settings()

        mapping = {
            'protocol_editor': 'protocol_editor',
            'replay': 'replay_panel',
            'waveform': 'waveform_panel',
            'compare': 'compare_panel',
            'sniffer': 'sniffer_panel',
            'annotation': 'annotation_panel',
            'scheduler': 'scheduler_panel',
            'tunnel': 'tunnel_panel',
            'stress_test': 'stress_test_panel',
            'script': 'script_panel',
            'export': 'export_panel',
            'stats': 'stats_panel',
            'formatter': 'formatter_panel',
            'recorder': 'recorder_panel',
            'heartbeat': 'heartbeat_panel',
        }
        for key, attr in mapping.items():
            panel = self._panels.get(attr)
            if panel and hasattr(panel, 'get_settings'):
                settings[key] = panel.get_settings()
        return settings

    def load_settings(self, settings: dict):
        if not settings:
            return
        
        # 发送面板需要预创建以加载历史记录
        send_settings = settings.get('send')
        if send_settings:
            send_panel = self._get_or_create('send_panel')
            if send_panel and hasattr(send_panel, 'load_settings'):
                send_panel.load_settings(send_settings)

        # 协议解析面板需要预创建以加载协议列表
        parse_settings = settings.get('parse')
        if parse_settings:
            parse_panel = self._get_or_create('parse_panel')
            if parse_panel and hasattr(parse_panel, 'load_settings'):
                parse_panel.load_settings(parse_settings)

        # 恢复上次选中的面板
        last_panel = settings.get('_current_panel')
        if last_panel:
            self.after(0, lambda: self.switch_to_panel(last_panel))

        # 告警面板需要预创建以加载规则
        alert_settings = settings.get('alert')
        if alert_settings:
            alert_panel = self._get_or_create('alert_panel')
            if alert_panel and hasattr(alert_panel, 'load_settings'):
                alert_panel.load_settings(alert_settings)

        mapping = {
            'protocol_editor': 'protocol_editor',
            'replay': 'replay_panel',
            'waveform': 'waveform_panel',
            'compare': 'compare_panel',
            'sniffer': 'sniffer_panel',
            'annotation': 'annotation_panel',
            'scheduler': 'scheduler_panel',
            'tunnel': 'tunnel_panel',
            'stress_test': 'stress_test_panel',
            'script': 'script_panel',
            'export': 'export_panel',
            'stats': 'stats_panel',
            'formatter': 'formatter_panel',
            'recorder': 'recorder_panel',
            'heartbeat': 'heartbeat_panel',
        }
        for key, attr in mapping.items():
            panel = self._panels.get(attr)
            if panel and hasattr(panel, 'load_settings'):
                panel.load_settings(settings.get(key))
