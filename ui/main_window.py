"""主窗口 - 左右布局: 左侧控制面板，右侧日志"""

import os
import json
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkfont

from comm.tcp_client import TcpClient
from comm.tcp_server import TcpServer
from comm.udp_comm import UdpComm
from comm.serial_comm import SerialComm
from comm.websocket_comm import WebSocketComm
from comm.mqtt_comm import MqttComm

from ui.comm_panel import CommPanel
from ui.tooltip import ToolTip
from ui.send_panel import SendPanel
from ui.log_panel import LogPanel
from ui.heartbeat_panel import HeartbeatPanel
from ui.tools_notebook import ToolsContainer
from ui.settings_dialog import SettingsDialog
from ui.status_bus import StatusBus
from utils.context_menu import add_combobox_context_menu, add_entry_context_menu


class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        from utils.version import APP_VERSION, APP_NAME
        self.root.title(f'{APP_NAME} v{APP_VERSION}')
        
        # 设置程序图标
        try:
            from ui.icon import get_icon_path
            icon_path = get_icon_path()
            if icon_path and os.path.exists(icon_path):
                icon = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon)
        except Exception:
            pass
        
        # 窗口居中
        win_w, win_h = 1600, 900
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - win_w) // 2
        y = (screen_h - win_h) // 2
        self.root.geometry(f'{win_w}x{win_h}+{x}+{y}')
        self.root.minsize(1200, 650)

        # 通信对象
        self._tcp_client = TcpClient()
        self._tcp_clients = {}  # {host:port: TcpClient} 多实例
        self._tcp_server = TcpServer()
        self._udp = UdpComm()
        self._serial_clients = {}  # {port: SerialComm} 多实例
        self._ws = WebSocketComm()
        self._mqtt = MqttComm()
        self._current_comm = None

        # 多协议同时连接支持: 记录每个协议是否已连接
        self._connected_protocols = {}  # {proto: True/False}

        # TCP服务端: 当前选中的发送目标客户端 (None=全部)
        self._selected_client_key = None

        # 配置文件路径
        self._config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config.json')

        self._settings_dialog = SettingsDialog(self.root, main_window=self)
        self._load_settings()
        self._build_ui()
        self._apply_ttk_theme_from_settings()
        # 延迟加载配置和非关键初始化，加速窗口显示
        self.root.after_idle(self._load_config)
        self.root.after_idle(self._setup_callbacks)
        self.root.after_idle(self._setup_shortcuts)
        self.root.after_idle(lambda: StatusBus.register(self._on_status_update))
        # 菜单栏创建后延迟检查更新
        self.root.after(3000, lambda: self.root.after_idle(self._auto_check_update))

    def _build_ui(self):
        style = ttk.Style()
        ttk_theme = self._settings_dialog.get_setting('ttk_theme', 'clam')
        if ttk_theme in style.theme_names():
            style.theme_use(ttk_theme)
        else:
            for theme in ['clam', 'aqua', 'default']:
                if theme in style.theme_names():
                    style.theme_use(theme)
                    break

        # ========== 主容器: 左右分栏 ==========
        self._main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self._main_paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 0))

        # ===== 左侧: 控制面板(垂直分割: 通信设置+工具) =====
        left_outer = ttk.Frame(self._main_paned)
        self._main_paned.add(left_outer, weight=3)

        self._left_paned = ttk.PanedWindow(left_outer, orient=tk.VERTICAL)
        self._left_paned.pack(fill=tk.BOTH, expand=True)

        # --- 通信设置面板 (上部) ---
        top_frame = ttk.Frame(self._left_paned)
        self._left_paned.add(top_frame, weight=3)

        self.comm_panel = CommPanel(top_frame,
                                    on_connect=self._on_connect,
                                    on_disconnect=self._on_disconnect,
                                    on_log=lambda msg: self.log_panel.log_info(msg))
        self.comm_panel.pack(fill=tk.BOTH, expand=True)
        self.comm_panel._on_column_widths_changed = self._on_column_widths_changed

        # ===== 右侧: 日志面板 =====
        right_outer = ttk.Frame(self._main_paned)
        self._main_paned.add(right_outer, weight=6)

        max_lines = int(self._settings_dialog.get_setting('log_max_lines', 10000))
        self.log_panel = LogPanel(right_outer, max_lines=max_lines)
        self.log_panel.pack(fill=tk.BOTH, expand=True)

        # --- 工具集 (下部: 树形导航 + 隐藏标签页) ---
        from ui.tree_nav import TreeNavPanel
        from ui.tools_notebook import ToolsContainer
        self.tree_nav = TreeNavPanel(self._left_paned,
                                     on_select=self._on_tree_nav_select,
                                     on_favorites_changed=self._on_favorites_changed)
        self._left_paned.add(self.tree_nav, weight=4)

        self.tools_container = ToolsContainer(self._left_paned,
                                              on_send=self._send_data,
                                              log_panel=self.log_panel,
                                              main_window=self)
        self.tree_nav.set_tools_container(self.tools_container)

        # ========== 底部状态栏（延迟创建，让窗口先显示）==========
        self._build_status_bar()

        # 菜单栏延迟到窗口显示后创建
        self.root.after_idle(self._build_menubar)

    def _build_menubar(self):
        """创建菜单栏（延迟执行以加速窗口显示）"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='文件', menu=file_menu)
        file_menu.add_command(label='📁 保存工程', command=self._save_project, accelerator='Ctrl+S')
        file_menu.add_command(label='📂 加载工程', command=self._load_project, accelerator='Ctrl+O')
        file_menu.add_separator()
        layout_menu = tk.Menu(file_menu, tearoff=0)
        layout_menu.add_command(label='保存当前布局...', command=self._save_layout_preset)
        layout_menu.add_command(label='加载布局...', command=self._load_layout_preset)
        file_menu.add_cascade(label='布局预设', menu=layout_menu)
        file_menu.add_separator()
        file_menu.add_command(label='退出', command=self._on_close, accelerator='Ctrl+Q')

        # 工具菜单
        tool_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='工具', menu=tool_menu)
        tool_menu.add_command(label='MQTT 客户端', command=self._open_mqtt_window, accelerator='Ctrl+M')
        tool_menu.add_separator()
        tool_menu.add_command(label='全局设置...', command=self._show_settings)
        tool_menu.add_separator()
        tool_menu.add_command(label='清空日志', command=self.log_panel.clear, accelerator='Ctrl+L')

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='帮助', menu=help_menu)
        help_menu.add_command(label='检查更新', command=self._check_update)
        help_menu.add_command(label='关于', command=self._show_about)

    def _set_initial_sash(self, paned, ratio=None, vertical=False):
        """设置初始分割位置，带越界保护"""
        try:
            self.root.update_idletasks()
            total = paned.winfo_height() if vertical else paned.winfo_width()
            if total > 100:
                if ratio is not None:
                    ratio = max(0.1, min(0.9, ratio))
                else:
                    ratio = 0.38 if vertical else 0.62
                paned.sashpos(0, int(total * ratio))
        except Exception:
            pass

    def _build_status_bar(self):
        """构建底部状态栏 — 三组分区布局"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=8, pady=(1, 4))

        # ── 第1组：连接状态 + 协议列表 ──
        self._status_conn = ttk.Label(status_frame, text='● 未连接', foreground='red')
        self._status_conn.pack(side=tk.LEFT, padx=(0, 4))

        self._status_protos = ttk.Label(status_frame, text='未连接')
        self._status_protos.pack(side=tk.LEFT, padx=(0, 12))
        ToolTip(self._status_protos, self._get_protos_tooltip)

        # 分组分隔
        ttk.Separator(status_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        # ── 第2组：TX/RX 速率 ──
        self._status_tx_rate = ttk.Label(status_frame, text='TX: 0 B/s ↑')
        self._status_tx_rate.pack(side=tk.LEFT, padx=(0, 4))

        self._status_rx_rate = ttk.Label(status_frame, text='RX: 0 B/s ↓')
        self._status_rx_rate.pack(side=tk.LEFT, padx=(0, 12))

        # 分组分隔
        ttk.Separator(status_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        # ── 第3组：TX/RX 总量 + 峰值 ──
        self._status_tx_total = ttk.Label(status_frame, text='TX↑: 0')
        self._status_tx_total.pack(side=tk.LEFT, padx=(0, 4))

        self._status_rx_total = ttk.Label(status_frame, text='RX↓: 0')
        self._status_rx_total.pack(side=tk.LEFT, padx=(0, 4))

        ttk.Separator(status_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        # ── 第4组：峰值速率 + 连接时长 ──
        self._status_peak = ttk.Label(status_frame, text='峰值 TX:0 RX:0')
        self._status_peak.pack(side=tk.LEFT, padx=(0, 4))

        self._status_uptime = ttk.Label(status_frame, text='时长: 00:00:00')
        self._status_uptime.pack(side=tk.LEFT, padx=(0, 4))

        # 当前时间（右侧）
        self._status_time = ttk.Label(status_frame, text='')
        self._status_time.pack(side=tk.RIGHT, padx=(0, 8))

        self._prev_tx_total = 0
        self._prev_rx_total = 0
        self._peak_tx_rate = 0
        self._peak_rx_rate = 0
        self._connect_start_time = None
        self._status_tick()

    def _status_tick(self):
        """每秒刷新状态栏的速率和总量"""
        # 已连接协议列表
        online_protos = []
        for key, v in self._connected_protocols.items():
            if v:
                if ':' in key and not any(key.startswith(p) for p in ('TCP', 'UDP', 'WebSocket')):
                    online_protos.append('TCP服务端')
                elif key.startswith('TCP客户端 '):
                    online_protos.append('TCP客户端')
                else:
                    online_protos.append(key)
        if online_protos:
            self._status_conn.configure(text='● 已连接', foreground='green')
            self._status_protos.configure(text=' | '.join(online_protos))
        else:
            self._status_conn.configure(text='● 未连接', foreground='red')
            self._status_protos.configure(text='未连接')

        # 速率和总量：从 comm_panel 统计
        tx_total = 0
        rx_total = 0
        for info in self.comm_panel._connections.values():
            tx_total += info.get('tx', 0)
            rx_total += info.get('rx', 0)

        tx_rate = tx_total - self._prev_tx_total
        rx_rate = rx_total - self._prev_rx_total
        self._peak_tx_rate = max(self._peak_tx_rate, tx_rate)
        self._peak_rx_rate = max(self._peak_rx_rate, rx_rate)

        def fmt_bytes(n):
            if n >= 1024 * 1024:
                return f'{n / 1024 / 1024:.1f}MB'
            elif n >= 1024:
                return f'{n / 1024:.1f}KB'
            return str(n)

        self._status_tx_rate.configure(text=f'TX: {fmt_bytes(tx_rate)}/s')
        self._status_rx_rate.configure(text=f'RX: {fmt_bytes(rx_rate)}/s')
        self._status_tx_total.configure(text=f'TX↑: {fmt_bytes(tx_total)}')
        self._status_rx_total.configure(text=f'RX↓: {fmt_bytes(rx_total)}')
        self._status_peak.configure(
            text=f'峰值 TX:{fmt_bytes(self._peak_tx_rate)}/s RX:{fmt_bytes(self._peak_rx_rate)}/s')
        self._prev_tx_total = tx_total
        self._prev_rx_total = rx_total

        # 连接时长
        if online_protos and self._connect_start_time is None:
            self._connect_start_time = time.time()
        elif not online_protos:
            self._connect_start_time = None
        if self._connect_start_time:
            elapsed = int(time.time() - self._connect_start_time)
            h, rem = divmod(elapsed, 3600)
            m, s = divmod(rem, 60)
            self._status_uptime.configure(text=f'时长: {h:02d}:{m:02d}:{s:02d}')
        else:
            self._status_uptime.configure(text='时长: --:--:--')

        # 更新时间
        from datetime import datetime
        self._status_time.configure(text=datetime.now().strftime('%H:%M:%S'))

        self._status_tick_id = self.root.after(1000, self._status_tick)

    def _get_protos_tooltip(self) -> str:
        """生成协议列表 tooltip 详细内容"""
        lines = []
        for key, v in self._connected_protocols.items():
            if not v:
                continue
            if ':' in key and not any(key.startswith(p) for p in ('TCP', 'UDP', 'WebSocket')):
                conn = self.comm_panel._connections.get(key, {})
                addr = conn.get('addr', key)
                clients = list(conn.get('clients', {}).keys())
                lines.append(f'TCP服务端: {addr}')
                if clients:
                    for ck in clients:
                        lines.append(f'  └ 客户端: {ck}')
                else:
                    lines.append(f'  └ 无客户端连接')
            elif key.startswith('TCP客户端 '):
                addr = key[len('TCP客户端 '):]
                lines.append(f'TCP客户端: {addr}')
            elif key.startswith('串口 '):
                lines.append(f'串口: {key[len("串口 "):]}')
            elif key == 'UDP':
                conn = self.comm_panel._connections.get(key, {})
                lines.append(f'UDP: {conn.get("addr", "")}')
            elif key in ('WebSocket客户端', 'WebSocket服务端'):
                conn = self.comm_panel._connections.get(key, {})
                lines.append(f'{key}: {conn.get("addr", "")}')
        return '\n'.join(lines)

    def _on_status_update(self, source: str, status: str, level: str = 'info'):
        pass

    def _on_tree_nav_select(self, panel_name: str):
        pass

    def _set_status_info(self, text: str):
        pass

    def _setup_callbacks(self):
        self._tcp_client.set_on_receive(self._on_receive)
        self._tcp_client.set_on_disconnect(lambda: self._on_tcp_client_disconnect('TCP客户端'))
        self._tcp_server.set_on_receive(self._on_server_receive)
        self._tcp_server.set_on_client_connect(self._on_server_client_connect)
        self._tcp_server.set_on_client_disconnect(self._on_server_client_disconnect)
        self._udp.set_on_receive(lambda data, addr: self._on_receive(data))
        self._ws.set_on_receive(self._on_receive)
        self._ws.set_on_disconnect(self._on_comm_disconnect)
        # MQTT 回调在 tools_notebook 创建后设置
        self.root.after(100, self._setup_mqtt)

    def _setup_mqtt(self):
        """MQTT 通信对象由独立窗口管理，但需要监听连接状态"""
        self._mqtt_window = None
        self._mqtt_connected = False

    def _setup_shortcuts(self):
        """设置全局快捷键"""
        # Ctrl+T: 新增连接
        self.root.bind('<Control-t>', lambda e: self.comm_panel._do_connect())
        self.root.bind('<Command-t>', lambda e: self.comm_panel._do_connect())
        # Ctrl+Enter: 发送
        self.root.bind('<Control-Return>', lambda e: self._send_shortcut())
        self.root.bind('<Command-Return>', lambda e: self._send_shortcut())
        # Ctrl+L: 清空日志
        self.root.bind('<Control-l>', lambda e: self.log_panel.clear())
        self.root.bind('<Command-l>', lambda e: self.log_panel.clear())
        # Ctrl+F: 搜索日志
        self.root.bind('<Control-f>', lambda e: self._focus_log())
        self.root.bind('<Command-f>', lambda e: self._focus_log())
        # Ctrl+W: 断开连接
        self.root.bind('<Control-w>', lambda e: self._on_disconnect())
        self.root.bind('<Command-w>', lambda e: self._on_disconnect())
        # Ctrl+M: 打开 MQTT 窗口
        self.root.bind('<Control-m>', lambda e: self._open_mqtt_window())
        self.root.bind('<Command-m>', lambda e: self._open_mqtt_window())

        # Ctrl+1~9: 切换工具面板
        tool_map = {
            '1': '快捷发送', '2': '协议解析', '3': '协议编辑器',
            '4': '转换器', '5': '校验和', '6': '压力测试',
            '7': '脚本', '8': '告警', '9': '波形',
        }
        for key, panel_name in tool_map.items():
            self.root.bind(f'<Control-Key-{key}>',
                           lambda e, pn=panel_name: self.tools_container.switch_to_panel(pn))
            self.root.bind(f'<Command-Key-{key}>',
                           lambda e, pn=panel_name: self.tools_container.switch_to_panel(pn))

    def _send_shortcut(self):
        """快捷键发送 - 从工具集中的快捷发送面板获取数据发送"""
        if self._current_comm or any(self._connected_protocols.values()):
            self.tools_container.send_panel._do_send()

    def _focus_log(self):
        """聚焦到日志面板"""
        self.log_panel.text.focus_set()

    # ============================================================
    # 连接/断开 - 支持多协议同时连接
    # ============================================================

    def _on_connect(self, config: dict):
        """连接指定协议 - 支持多协议同时在线"""
        proto = config['protocol']
        
        try:
            if proto == 'TCP客户端':
                conn_key = f'TCP客户端 {config["host"]}:{config["port"]}'
                if conn_key in self._tcp_clients:
                    conn = self._tcp_clients[conn_key]
                    if conn.connected:
                        self.log_panel.log_info(f'TCP客户端 {conn_key} 已连接')
                        return
                new_client = TcpClient()
                new_client.set_on_receive(self._on_receive)
                new_client.set_on_disconnect(lambda k=conn_key: self._on_tcp_client_disconnect(k))
                new_client.set_on_connect_done(
                    lambda success, err, k=conn_key: self._on_tcp_connect_done(success, err, k))
                ka = config.get('keepalive', {})
                if ka.get('enabled'):
                    new_client.connect(config['host'], config['port'],
                                       keepalive_idle=int(ka['idle']),
                                       keepalive_interval=int(ka['interval']),
                                       keepalive_count=int(ka['count']))
                else:
                    new_client.connect(config['host'], config['port'])
                self._tcp_clients[conn_key] = new_client
                self._connected_protocols[conn_key] = True
                self.log_panel.log_info(
                    f'TCP客户端正在连接 {conn_key}...')
                self.comm_panel.set_connected(conn_key, True, conn_key)

            elif proto == 'TCP服务端':
                inst_key = f'{config["host"]}:{config["port"]}'
                if inst_key in self._tcp_server.get_instance_keys():
                    self.log_panel.log_info(f'TCP服务端 {inst_key} 已启动')
                    return
                self._tcp_server.start(config['host'], config['port'])
                self._current_comm = self._tcp_server
                self._connected_protocols[inst_key] = True
                self.log_panel.log_info(
                    f'TCP服务端已启动，监听 {inst_key}')
                self.comm_panel.set_connected(inst_key, True, inst_key)
                del inst_key

            elif proto == 'UDP':
                self._udp.open(
                    local_port=config.get('local_port', 0),
                    target_host=config['host'],
                    target_port=config['port'],
                )
                self._current_comm = self._udp
                self._connected_protocols['UDP'] = True
                addr = self._udp._local_addr
                self.log_panel.log_info(
                    f'UDP已打开，本地 {addr[0]}:{addr[1]}，'
                    f'目标 {config["host"]}:{config["port"]}')

            elif proto == '串口':
                port = config['port']
                key = f'串口 {port}'
                if key in self._serial_clients:
                    self.log_panel.log_info(f'串口 {port} 已连接')
                    return
                serial = SerialComm()
                serial.connect(
                    port=port,
                    baudrate=config['baudrate'],
                    bytesize=config['bytesize'],
                    parity=config['parity'],
                    stopbits=config['stopbits'],
                )
                serial.set_on_receive(self._on_receive)
                serial.set_on_disconnect(lambda: self._on_serial_disconnect(key))
                self._serial_clients[key] = serial
                self._current_comm = serial
                self._connected_protocols[key] = True
                self.log_panel.log_info(
                    f'串口已连接: {port} '
                    f'{config["baudrate"]},{config["bytesize"]},'
                    f'{config["parity"]},{config["stopbits"]}')

            elif proto == 'WebSocket客户端':
                current_url = None
                if self._connected_protocols.get('WebSocket客户端'):
                    conn = self.comm_panel._connections.get('WebSocket客户端', {})
                    current_url = conn.get('addr', '')
                
                new_url = f'ws://{config["host"]}:{config["port"]}'
                if current_url and current_url == new_url:
                    self.log_panel.log_info(f'WebSocket已连接到 {new_url}')
                    return
                
                if current_url:
                    self._ws.disconnect()
                    self.log_panel.log_info(f'WebSocket已断开旧连接: {current_url}')
                
                url = new_url
                self._ws.connect(url)
                self._current_comm = self._ws
                self._connected_protocols['WebSocket客户端'] = True
                self.log_panel.log_info(f'WebSocket客户端已连接到 {url}')

            elif proto == 'WebSocket服务端':
                self._ws.start_server(config['host'], config['port'])
                self._current_comm = self._ws
                self._connected_protocols['WebSocket服务端'] = True
                self.log_panel.log_info(
                    f'WebSocket服务端已启动，监听 {config["host"]}:{config["port"]}')

            # 更新通信面板的连接状态
            if proto == '串口':
                key = f'串口 {config["port"]}'
                info = f'{config["port"]} {config["baudrate"]}'
                self.comm_panel.set_connected(key, True, info)
            elif proto == 'UDP':
                info = f'{config["host"]}:{config["port"]}'
                self.comm_panel.set_connected(proto, True, info)
            elif proto in ('WebSocket客户端', 'WebSocket服务端'):
                info = f'{config["host"]}:{config["port"]}'
                self.comm_panel.set_connected(proto, True, info)

            if proto != 'TCP客户端':
                self._set_status_info(f'{proto} 已连接')

        except Exception as e:
            self.log_panel.log_info(f'连接失败: {e}')

    def _on_disconnect(self, proto: str = None):
        """断开连接 - 支持断开全部或断开指定协议"""
        if proto is None:
            self._disconnect_all()
        else:
            self._disconnect_proto(proto)

    def _disconnect_all(self):
        """断开所有协议"""
        try:
            for key, client in list(self._tcp_clients.items()):
                client.disconnect()
            for key in list(self._tcp_server.get_instance_keys()):
                self._tcp_server.stop(key)
            if self._connected_protocols.get('UDP'):
                self._udp.close()
            for key in list(self._serial_clients.keys()):
                self._serial_clients[key].disconnect()
            self._serial_clients.clear()
            if self._connected_protocols.get('WebSocket客户端'):
                self._ws.disconnect()
            if self._connected_protocols.get('WebSocket服务端'):
                self._ws.stop_server()
        except Exception:
            pass
        
        for proto in list(self._connected_protocols.keys()):
            self._connected_protocols[proto] = False
            self.comm_panel.set_connected(proto, False)
        
        self._current_comm = None
        self._set_status_info('已断开所有连接')
        self.log_panel.log_info('已断开所有连接')

    def _disconnect_proto(self, proto: str):
        """断开指定协议"""
        try:
            if ':' in proto and not any(proto.startswith(p) for p in ('TCP', 'UDP', 'WebSocket')):
                if proto in self._tcp_clients:
                    self._tcp_clients[proto].disconnect()
                    self._tcp_clients.pop(proto, None)
                else:
                    self._tcp_server.stop(proto)
                self._connected_protocols[proto] = False
                self.comm_panel.set_connected(proto, False)
                self.log_panel.log_info(f'{proto} 已断开')
            elif proto == 'UDP' and self._connected_protocols.get('UDP'):
                self._udp.close()
                self._connected_protocols['UDP'] = False
                self.log_panel.log_info('UDP已关闭')
            elif proto.startswith('串口 ') and self._connected_protocols.get(proto):
                serial = self._serial_clients.pop(proto, None)
                if serial:
                    serial.disconnect()
                self._connected_protocols[proto] = False
                self.log_panel.log_info(f'{proto} 已断开')
            elif proto == 'WebSocket客户端' and self._connected_protocols.get('WebSocket客户端'):
                self._ws.disconnect()
                self._connected_protocols['WebSocket客户端'] = False
                self.log_panel.log_info('WebSocket客户端已断开')
            elif proto == 'WebSocket服务端' and self._connected_protocols.get('WebSocket服务端'):
                self._ws.stop_server()
                self._connected_protocols['WebSocket服务端'] = False
                self.log_panel.log_info('WebSocket服务端已停止')
        except Exception as e:
            self.log_panel.log_info(f'断开 {proto} 失败: {e}')
        
        if ':' not in proto or any(proto.startswith(p) for p in ('TCP', 'UDP', 'WebSocket')):
            self.comm_panel.set_connected(proto, False)
        if not any(self._connected_protocols.values()):
            self._current_comm = None
            self._set_status_info(f'{proto} 已断开')
        else:
            self._set_status_info(f'{proto} 已断开')

    # ============================================================
    # 数据接收
    # ============================================================

    def _on_receive(self, data: bytes):
        """通用接收 (TCP客户端/UDP/串口)"""
        def _handle():
            self.log_panel.log_rx(data)
            # 更新通信面板的接收计数
            for proto in self._connected_protocols:
                if self._connected_protocols[proto] and proto not in ('TCP服务端',):
                    self.comm_panel.update_tx_rx(proto, is_tx=False)
                    break

            # 自动协议解析
            self.tools_container.parse_panel.auto_parse(data.hex())

            # 记录到数据回放
            self.tools_container.replay_panel.record_data(data, 'RX')
            # 记录到操作录制
            self.tools_container.recorder_panel.record_receive(data)
            
            # 添加到实时波形
            self.tools_container.waveform_panel.add_data(data)
            
            # 数据统计
            self.tools_container.stats_panel.record_rx(data)

            # 检查条件告警
            self.tools_container.alert_panel.check_data(data)
            
            # 协议嗅探
            self.tools_container.sniffer_panel.sniff_data(data)
            
            # 检查是否为心跳数据
            is_heartbeat = self.tools_container.heartbeat_panel.check_and_reply(data)
            if is_heartbeat:
                self.log_panel.log_info('[心跳] 已自动回复')
            # 检查批量自动回复
            if not is_heartbeat:
                self.tools_container.auto_reply_panel.check_and_reply(data)
        self.root.after(0, _handle)

    def _on_server_receive(self, data: bytes, instance_key: str, client_key: str):
        """TCP服务端接收 (带实例标识和客户端标识)"""
        def _handle():
            self.log_panel.log_rx(data, source=f'{instance_key}/{client_key}')
            self.comm_panel.update_tx_rx(instance_key, is_tx=False, client_key=client_key)

            # 自动协议解析
            self.tools_container.parse_panel.auto_parse(data.hex())

            # 记录到数据回放
            self.tools_container.replay_panel.record_data(data, 'RX')

            # 检查条件告警
            self.tools_container.alert_panel.check_data(data)
            
            # 检查是否为心跳数据
            is_heartbeat = self.tools_container.heartbeat_panel.check_and_reply(data)
            if is_heartbeat:
                self.log_panel.log_info(f'[心跳] 已自动回复 -> {client_key}')
            # 检查批量自动回复
            if not is_heartbeat:
                self.tools_container.auto_reply_panel.check_and_reply(data)
        self.root.after(0, _handle)

    def _on_tcp_client_disconnect(self, client_key: str):
        """TCP客户端断开回调（多实例支持）"""
        def _handle():
            self._connected_protocols[client_key] = False
            self.comm_panel.set_connected(client_key, False)
            self.log_panel.log_info(f'TCP客户端 {client_key} 连接已断开')
            if not any(self._connected_protocols.values()):
                self._current_comm = None
        self.root.after(0, _handle)

    def _on_tcp_connect_done(self, success: bool, error: str, conn_key: str):
        """TCP客户端连接完成回调（后台线程调用）"""
        def _handle():
            if success:
                self.log_panel.log_info(f'TCP客户端已连接到 {conn_key}')
            else:
                self._connected_protocols[conn_key] = False
                self.comm_panel.set_connected(conn_key, False)
                self.log_panel.log_info(f'TCP客户端 {conn_key} 连接失败: {error}')
                if not any(self._connected_protocols.values()):
                    self._current_comm = None
        self.root.after(0, _handle)

    def _on_comm_disconnect(self, proto: str = None):
        """串口/WebSocket 断开"""
        def _handle():
            if proto:
                self._connected_protocols[proto] = False
                self.comm_panel.set_connected(proto, False)
                self.log_panel.log_info(f'{proto} 连接已断开')
            else:
                for p in ['WebSocket客户端']:
                    if self._connected_protocols.get(p):
                        self._connected_protocols[p] = False
                        self.comm_panel.set_connected(p, False)
                        self.log_panel.log_info(f'{p} 连接已断开')
                        break
            if not any(self._connected_protocols.values()):
                self._current_comm = None
                self._set_status_info('所有连接已断开')
            else:
                self._set_status_info(f'{proto} 连接已断开')
        self.root.after(0, _handle)

    def _on_serial_disconnect(self, key: str):
        def _handle():
            self._connected_protocols[key] = False
            self._serial_clients.pop(key, None)
            self.comm_panel.set_connected(key, False)
            self.log_panel.log_info(f'{key} 连接已断开')
            if not any(self._connected_protocols.values()):
                self._current_comm = None
                self._set_status_info('所有连接已断开')
        self.root.after(0, _handle)

    # ============================================================
    # TCP服务端: 多客户端管理
    # ============================================================

    def _on_server_client_connect(self, instance_key: str, client_key: str, addr: tuple):
        def _handle():
            self.log_panel.log_info(f'客户端已连接: {instance_key}/{client_key}')
            self.comm_panel.set_client_connected(instance_key, client_key, True)
        self.root.after(0, _handle)

    def _on_server_client_disconnect(self, instance_key: str, client_key: str):
        def _handle():
            self.log_panel.log_info(f'客户端已断开: {instance_key}/{client_key}，等待新连接...')
            self.comm_panel.set_client_connected(instance_key, client_key, False)
        self.root.after(0, _handle)

    # ============================================================
    # 发送数据
    # ============================================================

    def _send_data(self, data: bytes, **kwargs):
        """用户主动发送 - 只发送到开启了发送开关的目标"""
        if not self._current_comm and not any(self._connected_protocols.values()):
            messagebox.showwarning('提示', '请先连接')
            return
        
        # 获取开启了发送开关的目标
        targets = self.comm_panel.get_send_targets()
        if not targets:
            messagebox.showwarning('提示', '没有开启发送的连接，请在连接详情中勾选"发送"')
            return
        
        sent_any = False
        errors = []
        
        for proto, client_key in targets:
            try:
                if proto in self._tcp_clients:
                    self._tcp_clients[proto].send(data)
                    self.log_panel.log_tx(data, source=f'TCP客户端({proto})')
                    sent_any = True
                elif ':' in proto and self._connected_protocols.get(proto):
                    self._tcp_server.send(data, client_key=client_key, instance_key=proto)
                    target = client_key or '全部'
                    self.log_panel.log_tx(data, source=f'TCP服务端({target})')
                    sent_any = True
                elif proto == 'UDP':
                    self._udp.send(data)
                    self.log_panel.log_tx(data, source='UDP')
                    sent_any = True
                elif proto.startswith('串口 '):
                    serial = self._serial_clients.get(proto)
                    if serial:
                        serial.send(data)
                        self.log_panel.log_tx(data, source=proto)
                        sent_any = True
                elif proto in ('WebSocket客户端', 'WebSocket服务端'):
                    self._ws.send(data)
                    self.log_panel.log_tx(data, source='WebSocket')
                    sent_any = True
            except Exception as e:
                errors.append(f'{proto}: {e}')
        
        if sent_any:
            self.tools_container.replay_panel.record_data(data, 'TX')
            self.tools_container.recorder_panel.record_send(data)

            # 更新通信面板的发送计数
            for proto in self._connected_protocols:
                if self._connected_protocols[proto]:
                    self.comm_panel.update_tx_rx(proto, is_tx=True)
        
        if errors:
            error_msg = '; '.join(errors)
            self.log_panel.log_info(f'部分发送失败: {error_msg}')
            if not sent_any:
                messagebox.showerror('发送失败', error_msg)

    def _send_data_silent(self, data: bytes) -> bool:
        """静默发送 - 不弹窗，只发送到开启了发送开关的目标（供压力测试/脚本使用）"""
        if not any(self._connected_protocols.values()):
            return False
        if not data:
            return True
        
        targets = self.comm_panel.get_send_targets()
        if not targets:
            return False
        
        sent_any = False
        for proto, client_key in targets:
            try:
                if proto in self._tcp_clients:
                    self._tcp_clients[proto].send(data)
                    sent_any = True
                elif ':' in proto and self._connected_protocols.get(proto):
                    self._tcp_server.send(data, client_key=client_key, instance_key=proto)
                    sent_any = True
                elif proto == 'UDP':
                    self._udp.send(data)
                    sent_any = True
                elif proto.startswith('串口 '):
                    serial = self._serial_clients.get(proto)
                    if serial:
                        serial.send(data)
                        sent_any = True
                elif proto in ('WebSocket客户端', 'WebSocket服务端'):
                    self._ws.send(data)
                    sent_any = True
            except Exception:
                pass

        if sent_any:
            self.log_panel.log_tx(data)
            self.tools_container.replay_panel.record_data(data, 'TX')
            return True
        return False

    # ============================================================
    # 配置保存/加载
    # ============================================================

    def _save_config(self):
        """保存配置到 config.json"""
        try:
            sash_ratio = None
            try:
                total_width = self._main_paned.winfo_width()
                if total_width > 0:
                    sash_pos = self._main_paned.sashpos(0)
                    sash_ratio = max(0.1, min(0.9, sash_pos / total_width))
            except Exception:
                pass

            left_sash_ratio = None
            try:
                total_height = self._left_paned.winfo_height()
                if total_height > 0:
                    sash_pos = self._left_paned.sashpos(0)
                    left_sash_ratio = max(0.1, min(0.9, sash_pos / total_height))
            except Exception:
                pass

            # 获取 MQTT 窗口配置（含 sash_ratio）
            mqtt_settings = None
            try:
                if self._mqtt_window is not None and self._mqtt_window.winfo_exists():
                    mqtt_settings = self._mqtt_window.get_settings()
            except Exception:
                pass

            config = {
                'comm': self.comm_panel.get_settings(),
                'tools': self.tools_container.get_settings(),
                'connections': self.comm_panel.get_connections_save_data(),
                'shortcuts': self.tools_container.get_send_panel().get_shortcuts_data(),
                'settings': self._settings_dialog.get_all_settings() if hasattr(self, '_settings_dialog') else {},
                'favorites': self.tree_nav.get_favorites(),
                'window': {
                    'width': self.root.winfo_width(),
                    'height': self.root.winfo_height(),
                },
                'sash_ratio': sash_ratio,
                'left_sash_ratio': left_sash_ratio,
                'mqtt': mqtt_settings,
                'update': self._get_update_config(),
            }
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.log_panel.log_info('配置已保存')
            self._set_status_info('配置已保存')
        except Exception as e:
            self.log_panel.log_info(f'保存配置失败: {e}')
            self._set_status_info('保存配置失败')

    def _get_update_config(self) -> dict:
        """从 config.json 读取现有 update 配置（保留 ignored_versions）"""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                return existing.get('update', {'ignored_versions': []})
        except Exception:
            pass
        return {'ignored_versions': []}

    def _save_project(self):
        """保存工程文件"""
        from utils.version import APP_VERSION
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            title='保存工程',
            defaultextension='.cdt',
            filetypes=[('通信调试工程文件', '*.cdt'), ('所有文件', '*.*')])
        if not file_path:
            return
        try:
            sash_ratio = None
            try:
                total_width = self._main_paned.winfo_width()
                if total_width > 0:
                    sash_pos = self._main_paned.sashpos(0)
                    sash_ratio = max(0.1, min(0.9, sash_pos / total_width))
            except Exception:
                pass
            left_sash_ratio = None
            try:
                total_height = self._left_paned.winfo_height()
                if total_height > 0:
                    sash_pos = self._left_paned.sashpos(0)
                    left_sash_ratio = max(0.1, min(0.9, sash_pos / total_height))
            except Exception:
                pass

            project = {
                'version': f'v{APP_VERSION}',
                'comm': self.comm_panel.get_settings(),
                'connections': self.comm_panel.get_connections_save_data(),
                'tools': self.tools_container.get_settings(),
                'shortcuts': self.tools_container.get_send_panel().get_shortcuts_data(),
                'settings': self._settings_dialog.get_all_settings() if hasattr(self, '_settings_dialog') else {},
                'favorites': self.tree_nav.get_favorites(),
                'window': {
                    'width': self.root.winfo_width(),
                    'height': self.root.winfo_height(),
                },
                'sash_ratio': sash_ratio,
                'left_sash_ratio': left_sash_ratio,
                'current_panel': self.tools_container._current_panel_name,
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(project, f, ensure_ascii=False, indent=2)
            self.log_panel.log_info(f'工程已保存: {os.path.basename(file_path)}')
        except Exception as e:
            messagebox.showerror('保存失败', str(e))

    def _load_project(self):
        """加载工程文件"""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title='加载工程',
            filetypes=[('通信调试工程文件', '*.cdt'), ('所有文件', '*.*')])
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                project = json.load(f)
        except Exception as e:
            messagebox.showerror('加载失败', f'文件读取失败: {e}')
            return

        try:
            # 清空当前数据
            self.comm_panel._connections.clear()
            self.tools_container._panels.clear()
            self._connected_protocols.clear()

            # 加载通信设置
            comm_settings = project.get('comm', {})
            if comm_settings:
                self.comm_panel.load_settings(comm_settings)

            # 加载连接记录
            connections = project.get('connections', [])
            if connections:
                self.comm_panel.load_connections_save_data(connections)

            # 加载工具设置
            tools = project.get('tools', {})
            if tools:
                self.tools_container.load_settings(tools)

            # 加载快捷键
            shortcuts = project.get('shortcuts', [])
            if shortcuts:
                self.tools_container.get_send_panel().load_shortcuts_data(shortcuts)

            # 加载设置
            settings = project.get('settings', {})
            if settings:
                self._settings_dialog = SettingsDialog(self.root, settings=settings)
                self.apply_settings(settings)

            # 恢复窗口大小
            win = project.get('window', {})
            if win.get('width') and win.get('height'):
                self.root.geometry(f'{win["width"]}x{win["height"]}')

            # 恢复分割比例
            sash_ratio = project.get('sash_ratio')
            if sash_ratio is not None:
                self.root.after(300, lambda sr=sash_ratio: self._set_initial_sash(self._main_paned, sr))
                self.root.after(800, lambda sr=sash_ratio: self._set_initial_sash(self._main_paned, sr))
            left_sash_ratio = project.get('left_sash_ratio')
            if left_sash_ratio is not None:
                self.root.after(300, lambda sr=left_sash_ratio: self._set_initial_sash(self._left_paned, sr, vertical=True))
                self.root.after(800, lambda sr=left_sash_ratio: self._set_initial_sash(self._left_paned, sr, vertical=True))

            # 恢复收藏
            favorites = project.get('favorites', [])
            if favorites:
                self.tree_nav.set_favorites(favorites)

            # 恢复选中的面板
            current_panel = project.get('current_panel')
            if current_panel:
                self.root.after(300, lambda: self.tools_container.switch_to_panel(current_panel))

            self.log_panel.log_info(f'工程已加载: {os.path.basename(file_path)}')
        except Exception as e:
            messagebox.showerror('加载失败', f'工程数据加载失败: {e}')

    def _on_favorites_changed(self, favorites):
        """收藏列表变更时自动保存"""
        self._save_config()

    _col_save_timer = None

    def _on_column_widths_changed(self, widths):
        """连接表格列宽变更时延迟保存（防抖 1 秒）"""
        # 直接将新列宽设置到 tree（tree 已有最新值，这里用回调确认）
        if self._col_save_timer:
            try:
                self.root.after_cancel(self._col_save_timer)
            except Exception:
                pass
        self._col_save_timer = self.root.after(1000, self._save_config)

    def _save_layout_preset(self):
        """保存当前布局为预设"""
        from tkinter import simpledialog
        name = simpledialog.askstring('保存布局预设', '请输入布局名称：', parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        try:
            sash_ratio = None
            total_width = self._main_paned.winfo_width()
            if total_width > 0:
                sash_pos = self._main_paned.sashpos(0)
                sash_ratio = max(0.1, min(0.9, sash_pos / total_width))
            left_sash_ratio = None
            total_height = self._left_paned.winfo_height()
            if total_height > 0:
                sash_pos = self._left_paned.sashpos(0)
                left_sash_ratio = max(0.1, min(0.9, sash_pos / total_height))
            layout = {
                'window': {
                    'width': self.root.winfo_width(),
                    'height': self.root.winfo_height(),
                },
                'sash_ratio': sash_ratio,
                'left_sash_ratio': left_sash_ratio,
                'current_panel': self.tools_container._current_panel_name,
            }
            config = self._load_config_data()
            layouts = config.get('layouts', {})
            layouts[name] = layout
            config['layouts'] = layouts
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.log_panel.log_info(f'布局预设已保存: {name}')
        except Exception as e:
            self.log_panel.log_info(f'保存布局预设失败: {e}')

    def _load_layout_preset(self):
        """加载已保存的布局预设"""
        config = self._load_config_data()
        layouts = config.get('layouts', {})
        if not layouts:
            self.log_panel.log_info('没有已保存的布局预设')
            return
        # 弹出选择对话框
        from tkinter import simpledialog
        keys = list(layouts.keys())
        dialog = tk.Toplevel(self.root)
        dialog.title('加载布局预设')
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        pw, ph = self.root.winfo_width(), self.root.winfo_height()
        px, py = self.root.winfo_rootx(), self.root.winfo_rooty()
        w, h = 300, min(400, len(keys) * 40 + 80)
        dialog.geometry(f'{w}x{h}+{px + (pw - w)//2}+{py + (ph - h)//2}')
        ttk.Label(dialog, text='选择布局预设：', font=('', 9, 'bold')).pack(pady=(10, 4))
        listbox = tk.Listbox(dialog, height=min(8, len(keys)))
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        for k in keys:
            listbox.insert(tk.END, k)
        listbox.selection_set(0)

        def do_load():
            sel = listbox.curselection()
            if not sel:
                return
            name = keys[sel[0]]
            layout = layouts[name]
            win = layout.get('window', {})
            if win.get('width') and win.get('height'):
                self.root.geometry(f'{win["width"]}x{win["height"]}')
            sash_ratio = layout.get('sash_ratio')
            if sash_ratio is not None:
                self.root.after(200, lambda sr=sash_ratio: self._set_initial_sash(self._main_paned, sr))
            left_sash_ratio = layout.get('left_sash_ratio')
            if left_sash_ratio is not None:
                self.root.after(200, lambda sr=left_sash_ratio: self._set_initial_sash(self._left_paned, sr, vertical=True))
            panel = layout.get('current_panel')
            if panel:
                self.root.after(300, lambda: self.tools_container.switch_to_panel(panel))
            self.log_panel.log_info(f'已加载布局预设: {name}')
            dialog.destroy()

        def do_delete():
            sel = listbox.curselection()
            if not sel:
                return
            name = keys[sel[0]]
            del layouts[name]
            config['layouts'] = layouts
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            listbox.delete(sel[0])
            self.log_panel.log_info(f'布局预设已删除: {name}')

        btn_f = ttk.Frame(dialog)
        btn_f.pack(fill=tk.X, padx=10, pady=(4, 10))
        ttk.Button(btn_f, text='加载', command=do_load).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_f, text='删除', command=do_delete).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_f, text='取消', command=dialog.destroy).pack(side=tk.RIGHT)

    def _apply_ttk_theme_from_settings(self):
        ttk_theme = self._settings_dialog.get_setting('ttk_theme', 'clam')
        try:
            style = ttk.Style()
            if ttk_theme in style.theme_names():
                style.theme_use(ttk_theme)
        except Exception:
            pass

    def _load_settings(self):
        """从 config.json 仅加载设置（在 UI 构建前调用）"""
        if not os.path.exists(self._config_path):
            return
        with open(self._config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        if not config:
            return
        saved_settings = config.get('settings', {})
        if saved_settings:
            self._settings_dialog = SettingsDialog(self.root, main_window=self, settings=saved_settings)

    def _load_config(self):
        """从 config.json 加载配置"""
        try:
            if not os.path.exists(self._config_path):
                self.apply_settings(self._settings_dialog.get_all_settings())
                return
            with open(self._config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if not config:
                self.apply_settings(self._settings_dialog.get_all_settings())
                return
            self.comm_panel.load_settings(config.get('comm'))
            self.comm_panel.load_connections_save_data(config.get('connections'))
            self.tools_container.load_settings(config.get('tools'))
            self.tools_container.get_send_panel().load_shortcuts_data(config.get('shortcuts'))
            self.apply_settings(self._settings_dialog.get_all_settings())
            win = config.get('window', {})
            w = win.get('width', 1600)
            h = win.get('height', 900)
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            x = (screen_w - w) // 2
            y = (screen_h - h) // 2
            self.root.geometry(f'{w}x{h}+{x}+{y}')
            
            sash_ratio = config.get('sash_ratio')
            if sash_ratio is not None:
                self.root.after(300, lambda sr=sash_ratio: self._set_initial_sash(self._main_paned, sr))
                self.root.after(800, lambda sr=sash_ratio: self._set_initial_sash(self._main_paned, sr))
            else:
                self.root.after(300, lambda: self._set_initial_sash(self._main_paned))

            left_sash_ratio = config.get('left_sash_ratio')
            if left_sash_ratio is not None:
                self.root.after(300, lambda sr=left_sash_ratio: self._set_initial_sash(self._left_paned, sr, vertical=True))
                self.root.after(800, lambda sr=left_sash_ratio: self._set_initial_sash(self._left_paned, sr, vertical=True))
            else:
                self.root.after(300, lambda: self._set_initial_sash(self._left_paned, vertical=True))
            
            # 恢复收藏
            favorites = config.get('favorites', [])
            if favorites:
                self.tree_nav.set_favorites(favorites)

            # 保存 MQTT 配置，供后续打开 MQTT 窗口时使用
            self._mqtt_config = config.get('mqtt')
        except Exception as e:
            self.log_panel.log_info(f'加载配置失败: {e}')

    def _on_close(self):
        """关闭窗口"""
        self._save_config()
        self._disconnect_all()
        try:
            self.root.after_cancel(self._status_tick_id)
        except Exception:
            pass
        self.root.destroy()

    def _open_mqtt_window(self):
        """打开 MQTT 独立窗口"""
        from ui.mqtt_window import MqttWindow
        if self._mqtt_window is not None and self._mqtt_window.winfo_exists():
            self._mqtt_window.lift()
            return
        self._mqtt_window = MqttWindow(self.root, on_send=self._send_data, log_panel=self.log_panel)
        self._mqtt_window.protocol('WM_DELETE_WINDOW', self._on_mqtt_window_close)
        # 加载保存的 MQTT 配置（含 sash_ratio）
        if hasattr(self, '_mqtt_config') and self._mqtt_config:
            self._mqtt_window.load_settings(self._mqtt_config)

    def _on_mqtt_window_close(self):
        """MQTT 窗口关闭"""
        self._mqtt_connected = False
        self._mqtt_window.destroy()
        self._mqtt_window = None

    def _show_settings(self):
        """显示全局设置对话框"""
        settings = self._settings_dialog.get_all_settings() if hasattr(self, '_settings_dialog') else {}

        def on_save(saved_settings):
            self._settings_dialog = SettingsDialog(self.root, settings=saved_settings)
            self._save_config()

        dialog = SettingsDialog(self.root, main_window=self, settings=settings, on_save=on_save)
        dialog.show()

    def run(self):
        """运行主循环"""
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)
        self.root.mainloop()

    def apply_settings(self, settings: dict):
        from ui.theme import set_theme
        ui_theme = settings.get('ui_theme', 'dark')
        set_theme(ui_theme)
        ttk_theme = settings.get('ttk_theme', 'clam')
        try:
            style = ttk.Style()
            style.theme_use(ttk_theme)
        except Exception:
            pass
        max_lines = int(settings.get('log_max_lines', 10000))
        self.log_panel.set_max_lines(max_lines)
        self.log_panel.log_info(f'界面={ttk_theme}, 编辑器主题={ui_theme}, 字体={settings.get("font_family")} {settings.get("font_size")}, 日志行数={max_lines}')

    def _show_about(self):
        """显示关于对话框"""
        from utils.version import APP_VERSION, APP_NAME
        messagebox.showinfo(
            '关于',
            f'{APP_NAME} v{APP_VERSION}\n\n'
            '支持 TCP 客户端/服务端、UDP、串口、WebSocket、MQTT 等协议\n'
            '集成数据转换、校验和计算、压力测试、脚本自动化等工具'
        )

    def _check_update(self):
        """检查更新（手动触发）"""
        from utils.updater import check_and_show
        config = self._load_config_data()
        update_config = config.get('update', {}) if config else {}
        check_and_show(self.root, update_config)

    def _auto_check_update(self):
        """启动时自动检查更新（静默，有新版本才弹窗）"""
        from utils.updater import check_silent
        config = self._load_config_data()
        update_config = config.get('update', {}) if config else {}
        check_silent(self.root, update_config)

    def _load_config_data(self) -> dict:
        """读取 config.json 原始数据"""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
