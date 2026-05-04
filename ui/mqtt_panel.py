"""MQTT 控制面板 - 连接管理、发布消息、订阅主题"""

import tkinter as tk
from tkinter import ttk
import threading
from utils.context_menu import add_entry_context_menu, add_combobox_context_menu
from utils.hex_utils import bytes_to_hex_str, hex_str_to_bytes


class MqttPanel(ttk.LabelFrame):
    """MQTT 客户端面板 - 连接 Broker、发布消息、订阅主题"""

    def __init__(self, parent, on_send=None, log_panel=None):
        super().__init__(parent, text=' MQTT 客户端 ', padding=4)
        self._mqtt = None
        self._on_send = on_send
        self._log_panel = log_panel
        self._connected = False
        self._messages = []  # [(time, topic, qos, payload_hex, payload_text)]
        # 消息列表引用（由 MqttWindow 设置）
        self._msg_tree = None
        self._msg_count_label = None
        self._stats_label = None
        self._filter_topic_var = None
        self._filter_content_var = None
        # 默认值（可直接测试：连接公共 Broker 并订阅/发布）
        self._defaults = {
            'host': 'broker.emqx.io',
            'port': '1883',
            'client_id': '',
            'username': '',
            'password': '',
            'use_tls': False,
            'will_topic': '',
            'will_payload': '',
            'will_qos': 0,
            'will_retain': False,
            'auto_reconnect': True,
            'reconnect_delay': 5,
            'max_reconnect_retries': 0,
            'pub_topic': 'test/topic',
            'pub_qos': 0,
            'pub_retain': False,
            'pub_mode': 'text',
            'pub_payload': 'Hello MQTT',
            'sub_topic': 'test/#',
            'sub_qos': 0,
        }
        self._build_ui()

    def set_mqtt(self, mqtt_comm):
        """设置 MQTT 通信对象"""
        self._mqtt = mqtt_comm
        if self._mqtt:
            self._mqtt.set_on_receive(self._on_message)
            self._mqtt.set_on_connect(self._on_connected)
            self._mqtt.set_on_disconnect(self._on_disconnected)

    def set_msg_tree(self, msg_tree, msg_count_label, stats_label,
                     filter_topic_var, filter_content_var):
        """设置消息列表引用（由 MqttWindow 调用）"""
        self._msg_tree = msg_tree
        self._msg_count_label = msg_count_label
        self._stats_label = stats_label
        self._filter_topic_var = filter_topic_var
        self._filter_content_var = filter_content_var

    def _build_ui(self):
        # 使用 Notebook 组织各个功能区域
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        # 创建各个标签页
        self._build_conn_tab()
        self._build_pub_tab()
        self._build_sub_tab()
        self._build_forward_tab()
        self._build_script_tab()
        self._build_diag_tab()

        # 初始状态
        self._update_ui_state()

    def _build_conn_tab(self):
        """连接配置标签页"""
        tab = ttk.Frame(self._notebook, padding=6)
        self._notebook.add(tab, text=' 连接配置 ')

        # 状态栏
        status_frame = ttk.Frame(tab)
        status_frame.pack(fill=tk.X, pady=(0, 6))

        # 状态指示灯
        self._status_canvas = tk.Canvas(status_frame, width=16, height=16, highlightthickness=0)
        self._status_canvas.pack(side=tk.LEFT, padx=(0, 4))
        self._status_dot = self._status_canvas.create_oval(2, 2, 14, 14, fill='gray', outline='')

        self._conn_btn = ttk.Button(status_frame, text='连接', command=self._toggle_connect, width=10)
        self._conn_btn.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(status_frame, text='恢复默认', command=self._reset_defaults, width=10).pack(side=tk.LEFT)

        # 连接配置
        cfg_frame = ttk.LabelFrame(tab, text=' Broker 配置 ', padding=6)
        cfg_frame.pack(fill=tk.X, pady=(0, 6))

        # Broker 地址
        row1 = ttk.Frame(cfg_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text='Broker:', width=10).pack(side=tk.LEFT)
        self._host_var = tk.StringVar(value='broker.emqx.io')
        host_entry = ttk.Entry(row1, textvariable=self._host_var)
        host_entry.pack(side=tk.LEFT, padx=(4, 8), fill=tk.X, expand=True)
        add_entry_context_menu(host_entry)

        ttk.Label(row1, text='端口:').pack(side=tk.LEFT)
        self._port_var = tk.StringVar(value='1883')
        port_entry = ttk.Entry(row1, textvariable=self._port_var, width=6)
        port_entry.pack(side=tk.LEFT, padx=(4, 8))
        add_entry_context_menu(port_entry)

        self._tls_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row1, text='TLS', variable=self._tls_var).pack(side=tk.LEFT)

        # 认证信息
        row2 = ttk.Frame(cfg_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text='Client ID:', width=10).pack(side=tk.LEFT)
        self._client_id_var = tk.StringVar(value='')
        client_id_entry = ttk.Entry(row2, textvariable=self._client_id_var)
        client_id_entry.pack(side=tk.LEFT, padx=(4, 8), fill=tk.X, expand=True)
        add_entry_context_menu(client_id_entry)

        ttk.Label(row2, text='用户名:').pack(side=tk.LEFT)
        self._username_var = tk.StringVar(value='')
        username_entry = ttk.Entry(row2, textvariable=self._username_var)
        username_entry.pack(side=tk.LEFT, padx=(4, 4), fill=tk.X, expand=True)
        add_entry_context_menu(username_entry)

        ttk.Label(row2, text='密码:').pack(side=tk.LEFT)
        self._password_var = tk.StringVar(value='')
        pwd_entry = ttk.Entry(row2, textvariable=self._password_var, show='*')
        pwd_entry.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)
        add_entry_context_menu(pwd_entry)

        # 连接模式 + 自动重连
        row3 = ttk.Frame(cfg_frame)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text='连接模式:', width=10).pack(side=tk.LEFT)
        self._conn_mode_var = tk.StringVar(value='TCP')
        conn_mode_cb = ttk.Combobox(row3, textvariable=self._conn_mode_var,
                                    values=['TCP', 'WebSocket'], state='readonly', width=10)
        conn_mode_cb.pack(side=tk.LEFT, padx=(4, 8))
        add_combobox_context_menu(conn_mode_cb)

        self._auto_reconnect_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row3, text='自动重连', variable=self._auto_reconnect_var).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(row3, text='间隔(秒):').pack(side=tk.LEFT)
        self._reconnect_delay_var = tk.StringVar(value='5')
        delay_entry = ttk.Entry(row3, textvariable=self._reconnect_delay_var, width=5)
        delay_entry.pack(side=tk.LEFT, padx=(4, 8))
        add_entry_context_menu(delay_entry)

        ttk.Label(row3, text='最大重试:').pack(side=tk.LEFT)
        self._max_reconnect_var = tk.StringVar(value='0')
        max_entry = ttk.Entry(row3, textvariable=self._max_reconnect_var, width=5)
        max_entry.pack(side=tk.LEFT, padx=(4, 0))
        add_entry_context_menu(max_entry)
        ttk.Label(row3, text='(0=无限)').pack(side=tk.LEFT, padx=(4, 0))

        # TLS 证书配置
        cert_frame = ttk.LabelFrame(tab, text=' TLS 证书 ', padding=6)
        cert_frame.pack(fill=tk.X, pady=(0, 6))

        row4 = ttk.Frame(cert_frame)
        row4.pack(fill=tk.X, pady=2)
        ttk.Label(row4, text='CA 证书:', width=10).pack(side=tk.LEFT)
        self._ca_cert_var = tk.StringVar(value='')
        ca_cert_entry = ttk.Entry(row4, textvariable=self._ca_cert_var)
        ca_cert_entry.pack(side=tk.LEFT, padx=(4, 4), fill=tk.X, expand=True)
        add_entry_context_menu(ca_cert_entry)
        ttk.Button(row4, text='浏览', command=lambda: self._browse_file(self._ca_cert_var), width=6).pack(side=tk.LEFT)

        row5 = ttk.Frame(cert_frame)
        row5.pack(fill=tk.X, pady=2)
        ttk.Label(row5, text='客户端证书:', width=10).pack(side=tk.LEFT)
        self._client_cert_var = tk.StringVar(value='')
        client_cert_entry = ttk.Entry(row5, textvariable=self._client_cert_var)
        client_cert_entry.pack(side=tk.LEFT, padx=(4, 4), fill=tk.X, expand=True)
        add_entry_context_menu(client_cert_entry)
        ttk.Button(row5, text='浏览', command=lambda: self._browse_file(self._client_cert_var), width=6).pack(side=tk.LEFT)

        row6 = ttk.Frame(cert_frame)
        row6.pack(fill=tk.X, pady=2)
        ttk.Label(row6, text='客户端密钥:', width=10).pack(side=tk.LEFT)
        self._client_key_var = tk.StringVar(value='')
        client_key_entry = ttk.Entry(row6, textvariable=self._client_key_var)
        client_key_entry.pack(side=tk.LEFT, padx=(4, 4), fill=tk.X, expand=True)
        add_entry_context_menu(client_key_entry)
        ttk.Button(row6, text='浏览', command=lambda: self._browse_file(self._client_key_var), width=6).pack(side=tk.LEFT)

        # 遗嘱消息
        will_frame = ttk.LabelFrame(tab, text=' 遗嘱消息 ', padding=6)
        will_frame.pack(fill=tk.X, pady=(0, 6))

        row7 = ttk.Frame(will_frame)
        row7.pack(fill=tk.X, pady=2)
        ttk.Label(row7, text='遗嘱主题:', width=10).pack(side=tk.LEFT)
        self._will_topic_var = tk.StringVar(value='')
        will_topic_entry = ttk.Entry(row7, textvariable=self._will_topic_var)
        will_topic_entry.pack(side=tk.LEFT, padx=(4, 8), fill=tk.X, expand=True)
        add_entry_context_menu(will_topic_entry)

        ttk.Label(row7, text='QoS:').pack(side=tk.LEFT)
        self._will_qos_var = tk.IntVar(value=0)
        will_qos_cb = ttk.Combobox(row7, textvariable=self._will_qos_var,
                                   values=[0, 1, 2], state='readonly', width=4)
        will_qos_cb.pack(side=tk.LEFT, padx=(4, 4))
        add_combobox_context_menu(will_qos_cb)

        self._will_retain_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row7, text='保留', variable=self._will_retain_var).pack(side=tk.LEFT, padx=(4, 0))

        row8 = ttk.Frame(will_frame)
        row8.pack(fill=tk.X, pady=2)
        ttk.Label(row8, text='遗嘱消息:', width=10).pack(side=tk.LEFT)
        self._will_payload_var = tk.StringVar(value='')
        will_payload_entry = ttk.Entry(row8, textvariable=self._will_payload_var)
        will_payload_entry.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)
        add_entry_context_menu(will_payload_entry)

    def _build_pub_tab(self):
        """发布消息标签页"""
        tab = ttk.Frame(self._notebook, padding=6)
        self._notebook.add(tab, text=' 发布消息 ')

        # 发布配置
        pub_frame = ttk.LabelFrame(tab, text=' 发布配置 ', padding=6)
        pub_frame.pack(fill=tk.X, pady=(0, 6))

        row1 = ttk.Frame(pub_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text='主题:', width=8).pack(side=tk.LEFT)
        self._pub_topic_var = tk.StringVar(value='test/topic')
        pub_topic_entry = ttk.Entry(row1, textvariable=self._pub_topic_var)
        pub_topic_entry.pack(side=tk.LEFT, padx=(4, 8), fill=tk.X, expand=True)
        add_entry_context_menu(pub_topic_entry)

        ttk.Label(row1, text='QoS:').pack(side=tk.LEFT)
        self._pub_qos_var = tk.IntVar(value=0)
        pub_qos_cb = ttk.Combobox(row1, textvariable=self._pub_qos_var,
                                  values=[0, 1, 2], state='readonly', width=4)
        pub_qos_cb.pack(side=tk.LEFT, padx=(4, 8))
        add_combobox_context_menu(pub_qos_cb)

        self._pub_retain_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row1, text='保留', variable=self._pub_retain_var).pack(side=tk.LEFT, padx=(0, 8))

        self._pub_btn = ttk.Button(row1, text='发布', command=self._publish, width=8)
        self._pub_btn.pack(side=tk.LEFT)

        # 消息内容
        row2 = ttk.Frame(pub_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text='内容:', width=8).pack(side=tk.LEFT)
        self._pub_mode = tk.StringVar(value='text')
        ttk.Radiobutton(row2, text='文本', variable=self._pub_mode,
                        value='text').pack(side=tk.LEFT, padx=(0, 4))
        ttk.Radiobutton(row2, text='HEX', variable=self._pub_mode,
                        value='hex').pack(side=tk.LEFT, padx=(0, 8))

        self._pub_payload_var = tk.StringVar(value='Hello MQTT')
        pub_payload_entry = ttk.Entry(row2, textvariable=self._pub_payload_var)
        pub_payload_entry.pack(side=tk.LEFT, padx=(0, 4), fill=tk.X, expand=True)
        add_entry_context_menu(pub_payload_entry)

        # 定时发布
        timer_frame = ttk.LabelFrame(tab, text=' 定时发布 ', padding=6)
        timer_frame.pack(fill=tk.X, pady=(0, 6))

        timer_row = ttk.Frame(timer_frame)
        timer_row.pack(fill=tk.X, pady=2)
        ttk.Label(timer_row, text='间隔(秒):', width=10).pack(side=tk.LEFT)
        self._timer_interval_var = tk.StringVar(value='5')
        timer_interval_entry = ttk.Entry(timer_row, textvariable=self._timer_interval_var, width=6)
        timer_interval_entry.pack(side=tk.LEFT, padx=(4, 8))
        add_entry_context_menu(timer_interval_entry)

        ttk.Label(timer_row, text='重复次数:').pack(side=tk.LEFT)
        self._timer_count_var = tk.StringVar(value='0')
        timer_count_entry = ttk.Entry(timer_row, textvariable=self._timer_count_var, width=6)
        timer_count_entry.pack(side=tk.LEFT, padx=(4, 8))
        add_entry_context_menu(timer_count_entry)
        ttk.Label(timer_row, text='(0=无限)').pack(side=tk.LEFT, padx=(0, 8))

        self._timer_btn = ttk.Button(timer_row, text='开始定时', command=self._toggle_timer, width=10)
        self._timer_btn.pack(side=tk.LEFT)
        self._timer_running = False
        self._timer_count = 0
        self._timer_job = None

    def _build_sub_tab(self):
        """订阅管理标签页"""
        tab = ttk.Frame(self._notebook, padding=6)
        self._notebook.add(tab, text=' 订阅管理 ')

        # 订阅配置
        sub_frame = ttk.LabelFrame(tab, text=' 订阅配置 ', padding=6)
        sub_frame.pack(fill=tk.X, pady=(0, 6))

        sub_row1 = ttk.Frame(sub_frame)
        sub_row1.pack(fill=tk.X, pady=2)
        ttk.Label(sub_row1, text='订阅主题:', width=10).pack(side=tk.LEFT)
        self._sub_topic_var = tk.StringVar(value='test/#')
        sub_topic_entry = ttk.Entry(sub_row1, textvariable=self._sub_topic_var)
        sub_topic_entry.pack(side=tk.LEFT, padx=(4, 8), fill=tk.X, expand=True)
        add_entry_context_menu(sub_topic_entry)

        ttk.Label(sub_row1, text='QoS:').pack(side=tk.LEFT)
        self._sub_qos_var = tk.IntVar(value=0)
        sub_qos_cb = ttk.Combobox(sub_row1, textvariable=self._sub_qos_var,
                                  values=[0, 1, 2], state='readonly', width=4)
        sub_qos_cb.pack(side=tk.LEFT, padx=(4, 8))
        add_combobox_context_menu(sub_qos_cb)

        self._sub_btn = ttk.Button(sub_row1, text='订阅', command=self._subscribe, width=8)
        self._sub_btn.pack(side=tk.LEFT, padx=(0, 4))
        self._unsub_btn = ttk.Button(sub_row1, text='取消订阅', command=self._unsubscribe, width=8)
        self._unsub_btn.pack(side=tk.LEFT)

        # 已订阅主题列表
        sub_list_frame = ttk.LabelFrame(tab, text=' 已订阅主题 ', padding=6)
        sub_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self._sub_tree = ttk.Treeview(sub_list_frame, columns=('qos',), show='tree',
                                      selectmode='browse', height=6)
        self._sub_tree.heading('#0', text='主题')
        self._sub_tree.column('#0', width=300, minwidth=150)
        self._sub_tree.column('qos', width=60, minwidth=40, anchor=tk.CENTER)
        self._sub_tree.heading('qos', text='QoS')
        self._sub_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sub_scroll = ttk.Scrollbar(sub_list_frame, orient=tk.VERTICAL, command=self._sub_tree.yview)
        sub_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._sub_tree.configure(yscrollcommand=sub_scroll.set)

    def _build_forward_tab(self):
        """消息转发标签页"""
        tab = ttk.Frame(self._notebook, padding=6)
        self._notebook.add(tab, text=' 消息转发 ')

        fwd_frame = ttk.LabelFrame(tab, text=' 转发配置 ', padding=6)
        fwd_frame.pack(fill=tk.X, pady=(0, 6))

        fwd_row1 = ttk.Frame(fwd_frame)
        fwd_row1.pack(fill=tk.X, pady=2)
        self._fwd_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(fwd_row1, text='启用转发', variable=self._fwd_enabled_var).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(fwd_row1, text='转发到:').pack(side=tk.LEFT)
        self._fwd_target_var = tk.StringVar(value='串口')
        fwd_target_cb = ttk.Combobox(fwd_row1, textvariable=self._fwd_target_var,
                                     values=['串口', 'TCP客户端', 'TCP服务器', 'UDP'], state='readonly', width=12)
        fwd_target_cb.pack(side=tk.LEFT, padx=(4, 8))
        add_combobox_context_menu(fwd_target_cb)

        fwd_row2 = ttk.Frame(fwd_frame)
        fwd_row2.pack(fill=tk.X, pady=2)
        ttk.Label(fwd_row2, text='主题过滤:').pack(side=tk.LEFT)
        self._fwd_topic_filter_var = tk.StringVar(value='')
        fwd_topic_entry = ttk.Entry(fwd_row2, textvariable=self._fwd_topic_filter_var)
        fwd_topic_entry.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)
        add_entry_context_menu(fwd_topic_entry)
        ttk.Label(fwd_row2, text='(留空=全部转发)').pack(side=tk.LEFT, padx=(4, 0))

    def _build_script_tab(self):
        """脚本触发标签页"""
        tab = ttk.Frame(self._notebook, padding=6)
        self._notebook.add(tab, text=' 脚本触发 ')

        script_frame = ttk.LabelFrame(tab, text=' 脚本配置 ', padding=6)
        script_frame.pack(fill=tk.X, pady=(0, 6))

        script_row1 = ttk.Frame(script_frame)
        script_row1.pack(fill=tk.X, pady=2)
        self._script_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(script_row1, text='启用脚本', variable=self._script_enabled_var).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(script_row1, text='触发主题:').pack(side=tk.LEFT)
        self._script_topic_var = tk.StringVar(value='')
        script_topic_entry = ttk.Entry(script_row1, textvariable=self._script_topic_var)
        script_topic_entry.pack(side=tk.LEFT, padx=(4, 8), fill=tk.X, expand=True)
        add_entry_context_menu(script_topic_entry)

        script_row2 = ttk.Frame(script_frame)
        script_row2.pack(fill=tk.X, pady=2)
        ttk.Label(script_row2, text='动作类型:').pack(side=tk.LEFT)
        self._script_action_var = tk.StringVar(value='执行命令')
        script_action_cb = ttk.Combobox(script_row2, textvariable=self._script_action_var,
                                        values=['执行命令', '写文件', 'HTTP请求'], state='readonly', width=12)
        script_action_cb.pack(side=tk.LEFT, padx=(4, 8))
        add_combobox_context_menu(script_action_cb)

        ttk.Label(script_row2, text='参数:').pack(side=tk.LEFT)
        self._script_param_var = tk.StringVar(value='')
        script_param_entry = ttk.Entry(script_row2, textvariable=self._script_param_var)
        script_param_entry.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)
        add_entry_context_menu(script_param_entry)

    def _build_diag_tab(self):
        """诊断工具标签页"""
        tab = ttk.Frame(self._notebook, padding=6)
        self._notebook.add(tab, text=' 诊断工具 ')

        # Broker 信息
        broker_frame = ttk.LabelFrame(tab, text=' Broker 信息 ', padding=6)
        broker_frame.pack(fill=tk.X, pady=(0, 6))

        broker_row = ttk.Frame(broker_frame)
        broker_row.pack(fill=tk.X, pady=2)
        ttk.Button(broker_row, text='获取 Broker 信息', command=self._get_broker_info, width=16).pack(side=tk.LEFT, padx=(0, 8))
        self._broker_info_var = tk.StringVar(value='')
        ttk.Label(broker_row, textvariable=self._broker_info_var, font=('', 9)).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Ping/Pong 延迟测试
        ping_frame = ttk.LabelFrame(tab, text=' Ping 延迟测试 ', padding=6)
        ping_frame.pack(fill=tk.X, pady=(0, 6))

        ping_row = ttk.Frame(ping_frame)
        ping_row.pack(fill=tk.X, pady=2)
        ttk.Label(ping_row, text='Ping 主题:').pack(side=tk.LEFT)
        self._ping_topic_var = tk.StringVar(value='ping/test')
        ping_topic_entry = ttk.Entry(ping_row, textvariable=self._ping_topic_var, width=20)
        ping_topic_entry.pack(side=tk.LEFT, padx=(4, 8))
        add_entry_context_menu(ping_topic_entry)

        ttk.Button(ping_row, text='开始 Ping', command=self._toggle_ping, width=10).pack(side=tk.LEFT, padx=(0, 8))
        self._ping_label = ttk.Label(ping_row, text='延迟: -- ms', font=('', 9))
        self._ping_label.pack(side=tk.LEFT)
        self._ping_running = False
        self._ping_times = []

        # 协议抓包
        capture_frame = ttk.LabelFrame(tab, text=' 协议抓包 ', padding=6)
        capture_frame.pack(fill=tk.X, pady=(0, 6))

        capture_row = ttk.Frame(capture_frame)
        capture_row.pack(fill=tk.X, pady=2)
        self._capture_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(capture_row, text='启用协议抓包', variable=self._capture_var).pack(side=tk.LEFT, padx=(0, 8))
        self._capture_label = ttk.Label(capture_row, text='显示 MQTT 报文类型', font=('', 9))
        self._capture_label.pack(side=tk.LEFT)

    def _browse_file(self, var):
        """浏览选择文件"""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title='选择证书文件',
            filetypes=[('所有文件', '*.*'), ('PEM 文件', '*.pem'), ('CRT 文件', '*.crt'), ('KEY 文件', '*.key')]
        )
        if path:
            var.set(path)

    def _set_status_color(self, color):
        """设置状态指示灯颜色"""
        self._status_canvas.itemconfig(self._status_dot, fill=color)

    def _update_ui_state(self):
        """根据连接状态更新 UI"""
        state = 'normal' if self._connected else 'disabled'
        self._pub_btn.configure(state=state)
        self._sub_btn.configure(state=state)
        self._unsub_btn.configure(state=state)
        self._conn_btn.configure(text='断开' if self._connected else '连接', state='normal')
        self._set_status_color('#00cc00' if self._connected else '#cccccc')

    def _reset_defaults(self):
        """恢复默认测试参数"""
        defaults = self._defaults
        self._host_var.set(defaults['host'])
        self._port_var.set(str(defaults['port']))
        self._client_id_var.set(defaults['client_id'])
        self._username_var.set(defaults['username'])
        self._password_var.set(defaults['password'])
        self._tls_var.set(defaults['use_tls'])
        self._auto_reconnect_var.set(defaults['auto_reconnect'])
        self._reconnect_delay_var.set(str(defaults['reconnect_delay']))
        self._max_reconnect_var.set(str(defaults['max_reconnect_retries']))
        self._will_topic_var.set(defaults['will_topic'])
        self._will_payload_var.set(defaults['will_payload'])
        self._will_qos_var.set(defaults['will_qos'])
        self._will_retain_var.set(defaults['will_retain'])
        self._pub_topic_var.set(defaults['pub_topic'])
        self._pub_qos_var.set(defaults['pub_qos'])
        self._pub_retain_var.set(defaults['pub_retain'])
        self._pub_mode.set(defaults['pub_mode'])
        self._pub_payload_var.set(defaults['pub_payload'])
        self._sub_topic_var.set(defaults['sub_topic'])
        self._sub_qos_var.set(defaults['sub_qos'])
        if self._log_panel:
            self._log_panel.log_info('[MQTT] 已恢复默认测试参数')

    def _toggle_connect(self):
        """连接/断开切换"""
        if self._connected:
            self._do_disconnect()
        else:
            self._do_connect()

    def _do_connect(self):
        """执行连接"""
        if not self._mqtt:
            if self._log_panel:
                self._log_panel.log_info('[MQTT] MQTT 通信模块未初始化')
            return

        host = self._host_var.get().strip()
        if not host:
            if self._log_panel:
                self._log_panel.log_info('[MQTT] 请输入 Broker 地址')
            return

        try:
            port = int(self._port_var.get().strip())
        except ValueError:
            port = 1883

        client_id = self._client_id_var.get().strip()
        username = self._username_var.get().strip()
        password = self._password_var.get().strip()
        use_tls = self._tls_var.get()
        will_topic = self._will_topic_var.get().strip()
        will_payload = self._will_payload_var.get().strip()
        will_qos = self._will_qos_var.get()
        will_retain = self._will_retain_var.get()
        auto_reconnect = self._auto_reconnect_var.get()

        try:
            reconnect_delay = int(self._reconnect_delay_var.get().strip())
        except ValueError:
            reconnect_delay = 5

        try:
            max_reconnect = int(self._max_reconnect_var.get().strip())
        except ValueError:
            max_reconnect = 0

        # 证书
        ca_cert = self._ca_cert_var.get().strip()
        client_cert = self._client_cert_var.get().strip()
        client_key = self._client_key_var.get().strip()

        try:
            self._mqtt.connect(
                host=host, port=port,
                client_id=client_id,
                username=username, password=password,
                use_tls=use_tls,
                ca_cert=ca_cert, client_cert=client_cert, client_key=client_key,
                will_topic=will_topic, will_payload=will_payload,
                will_qos=will_qos, will_retain=will_retain,
                auto_reconnect=auto_reconnect,
                reconnect_delay=reconnect_delay,
                max_reconnect_retries=max_reconnect,
            )
            self._set_status_color('#ffcc00')  # 黄色=连接中
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] 正在连接 {host}:{port}...')
        except Exception as e:
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] 连接失败: {e}')

    def _do_disconnect(self):
        """执行断开"""
        if self._mqtt:
            self._mqtt.disconnect()
        self._connected = False
        self._update_ui_state()
        if self._log_panel:
            self._log_panel.log_info('[MQTT] 已断开连接')

    def _on_connected(self):
        """连接成功回调（从后台线程调用，通过 after() 调度到主线程）"""
        try:
            self.winfo_toplevel().after(0, self._on_connected_ui)
        except Exception:
            pass

    def _on_connected_ui(self):
        """在 UI 线程中处理连接成功"""
        self._connected = True
        self._update_ui_state()
        if self._log_panel:
            host = self._host_var.get()
            port = self._port_var.get()
            self._log_panel.log_info(f'[MQTT] 已连接到 {host}:{port}')

    def _on_disconnected(self, reason=''):
        """断开回调（从后台线程调用，通过 after() 调度到主线程）"""
        try:
            self.winfo_toplevel().after(0, self._on_disconnected_ui, reason)
        except Exception:
            pass

    def _on_disconnected_ui(self, reason=''):
        """在 UI 线程中处理断开"""
        self._connected = False
        self._update_ui_state()
        if self._log_panel:
            self._log_panel.log_info(f'[MQTT] 连接已断开: {reason}')

    def _on_message(self, data: bytes, topic: str):
        """收到 MQTT 消息（从后台线程调用，通过 after() 调度到主线程）"""
        try:
            self.winfo_toplevel().after(0, self._on_message_ui, data, topic)
        except Exception:
            pass

    def _on_message_ui(self, data: bytes, topic: str):
        """在 UI 线程中更新消息列表"""
        import time
        now = time.strftime('%H:%M:%S')
        payload_hex = bytes_to_hex_str(data)
        try:
            payload_text = data.decode('utf-8', errors='replace')
        except Exception:
            payload_text = repr(data)

        # 获取 QoS（从订阅记录中获取）
        qos = self._sub_qos_var.get()

        self._messages.append((now, topic, qos, payload_hex, payload_text))

        # 如果消息列表尚未初始化，只记录到日志
        if self._msg_tree is None:
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] 收到 [{topic}]: {payload_hex}')
            return

        # 检查是否有过滤条件
        topic_filter = self._filter_topic_var.get().strip().lower()
        content_filter = self._filter_content_var.get().strip().lower()
        has_filter = bool(topic_filter or content_filter)

        try:
            if has_filter:
                # 有过滤条件时，重新应用过滤
                self._apply_filter()
            else:
                # 无过滤条件时，直接插入
                self._msg_tree.insert('', 0, values=(now, topic, qos, payload_hex, payload_text))
                self._msg_count_label.configure(text=f'共 {len(self._messages)} 条消息')

            # 更新统计
            self._update_stats()
        except Exception as e:
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] 消息列表更新异常: {e}')

        # 记录到日志
        if self._log_panel:
            self._log_panel.log_info(f'[MQTT] 收到 [{topic}]: {payload_hex}')

        # ===== 消息转发 =====
        if self._fwd_enabled_var.get():
            fwd_topic_filter = self._fwd_topic_filter_var.get().strip()
            if not fwd_topic_filter or fwd_topic_filter in topic:
                if self._on_send:
                    self._on_send(data)

        # ===== 脚本触发 =====
        if self._script_enabled_var.get():
            script_topic = self._script_topic_var.get().strip()
            if script_topic and script_topic in topic:
                action = self._script_action_var.get()
                param = self._script_param_var.get().strip()
                if param:
                    import subprocess
                    try:
                        if action == '执行命令':
                            subprocess.Popen(param, shell=True)
                            if self._log_panel:
                                self._log_panel.log_info(f'[MQTT] 脚本触发: 执行命令 "{param}"')
                        elif action == '写文件':
                            with open(param, 'a', encoding='utf-8') as f:
                                f.write(f'[{now}] [{topic}] {payload_hex}\n')
                            if self._log_panel:
                                self._log_panel.log_info(f'[MQTT] 脚本触发: 写入文件 "{param}"')
                        elif action == 'HTTP请求':
                            import urllib.request
                            import json
                            req_data = json.dumps({
                                'time': now,
                                'topic': topic,
                                'payload_hex': payload_hex,
                                'payload_text': payload_text,
                            }).encode('utf-8')
                            req = urllib.request.Request(param, data=req_data,
                                                         headers={'Content-Type': 'application/json'})
                            threading.Thread(target=lambda: urllib.request.urlopen(req, timeout=5),
                                             daemon=True).start()
                            if self._log_panel:
                                self._log_panel.log_info(f'[MQTT] 脚本触发: HTTP请求 "{param}"')
                    except Exception as e:
                        if self._log_panel:
                            self._log_panel.log_info(f'[MQTT] 脚本触发失败: {e}')

    def _toggle_timer(self):
        """启动/停止定时发布"""
        if self._timer_running:
            # 停止定时
            self._timer_running = False
            self._timer_btn.configure(text='开始定时')
            if self._timer_job:
                try:
                    self.after_cancel(self._timer_job)
                except Exception:
                    pass
                self._timer_job = None
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] 定时发布已停止（共发布 {self._timer_count} 次）')
        else:
            # 启动定时
            if not self._connected:
                if self._log_panel:
                    self._log_panel.log_info('[MQTT] 请先连接 Broker')
                return
            try:
                interval = int(self._timer_interval_var.get().strip())
                if interval < 1:
                    raise ValueError
            except ValueError:
                if self._log_panel:
                    self._log_panel.log_info('[MQTT] 定时间隔必须 >= 1 秒')
                return
            try:
                max_count = int(self._timer_count_var.get().strip())
                if max_count < 0:
                    raise ValueError
            except ValueError:
                max_count = 0
            self._timer_running = True
            self._timer_count = 0
            self._timer_max_count = max_count
            self._timer_btn.configure(text='停止定时')
            if self._log_panel:
                limit = '无限' if max_count == 0 else str(max_count)
                self._log_panel.log_info(f'[MQTT] 定时发布已启动（间隔 {interval} 秒，{limit} 次）')
            self._do_timer_publish()

    def _do_timer_publish(self):
        """执行一次定时发布"""
        if not self._timer_running or not self._connected:
            self._timer_running = False
            self._timer_btn.configure(text='开始定时')
            return

        # 检查是否达到最大次数
        if self._timer_max_count > 0 and self._timer_count >= self._timer_max_count:
            self._timer_running = False
            self._timer_btn.configure(text='开始定时')
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] 定时发布完成（共发布 {self._timer_count} 次）')
            return

        # 发布消息
        self._timer_count += 1
        topic = self._pub_topic_var.get().strip()
        qos = self._pub_qos_var.get()
        retain = self._pub_retain_var.get()
        payload_str = self._pub_payload_var.get()

        if self._pub_mode.get() == 'hex':
            try:
                payload = hex_str_to_bytes(payload_str)
            except Exception:
                payload = payload_str.encode('utf-8')
        else:
            payload = payload_str.encode('utf-8')

        if self._mqtt:
            try:
                self._mqtt.publish(topic, payload, qos=qos, retain=retain)
                if self._log_panel:
                    hex_str = bytes_to_hex_str(payload)
                    self._log_panel.log_info(f'[MQTT] 定时发布 [第{self._timer_count}次] [{topic}]: {hex_str}')
            except Exception:
                pass

        # 安排下一次
        try:
            interval = int(self._timer_interval_var.get().strip()) * 1000
        except ValueError:
            interval = 5000
        self._timer_job = self.after(interval, self._do_timer_publish)

    def _publish(self):
        """发布消息"""
        if not self._mqtt:
            if self._log_panel:
                self._log_panel.log_info('[MQTT] MQTT 模块未初始化')
            return

        topic = self._pub_topic_var.get().strip()
        if not topic:
            if self._log_panel:
                self._log_panel.log_info('[MQTT] 请输入发布主题')
            return

        qos = self._pub_qos_var.get()
        retain = self._pub_retain_var.get()
        payload_str = self._pub_payload_var.get()

        # 根据模式转换 payload
        if self._pub_mode.get() == 'hex':
            try:
                payload = hex_str_to_bytes(payload_str)
            except Exception as e:
                if self._log_panel:
                    self._log_panel.log_info(f'[MQTT] HEX 格式错误: {e}')
                return
        else:
            payload = payload_str.encode('utf-8')

        try:
            success = self._mqtt.publish(topic, payload, qos=qos, retain=retain)
            if success:
                if self._log_panel:
                    hex_str = bytes_to_hex_str(payload)
                    self._log_panel.log_info(f'[MQTT] 已发布 [{topic}]: {hex_str}')
            else:
                if self._log_panel:
                    self._log_panel.log_info('[MQTT] 发布失败')
        except Exception as e:
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] 发布失败: {e}')

    def _subscribe(self):
        """订阅主题"""
        if not self._mqtt:
            if self._log_panel:
                self._log_panel.log_info('[MQTT] MQTT 模块未初始化')
            return

        topic = self._sub_topic_var.get().strip()
        if not topic:
            if self._log_panel:
                self._log_panel.log_info('[MQTT] 请输入订阅主题')
            return

        qos = self._sub_qos_var.get()

        try:
            success = self._mqtt.subscribe(topic, qos=qos)
            if success:
                self._refresh_sub_list()
                if self._log_panel:
                    self._log_panel.log_info(f'[MQTT] 已订阅: {topic} (QoS {qos})')
            else:
                if self._log_panel:
                    self._log_panel.log_info(f'[MQTT] 订阅失败: {topic}')
        except Exception as e:
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] 订阅失败: {e}')

    def _unsubscribe(self):
        """取消订阅"""
        if not self._mqtt:
            return

        sel = self._sub_tree.selection()
        if not sel:
            if self._log_panel:
                self._log_panel.log_info('[MQTT] 请先在已订阅列表中选择要取消的主题')
            return

        # 获取选中的主题（从树节点中提取）
        item = self._sub_tree.item(sel[0])
        topic = item['text']
        # 如果是叶子节点，获取完整主题路径
        parent = self._sub_tree.parent(sel[0])
        while parent:
            parent_text = self._sub_tree.item(parent)['text']
            topic = parent_text + '/' + topic
            parent = self._sub_tree.parent(parent)

        try:
            success = self._mqtt.unsubscribe(topic)
            if success:
                self._refresh_sub_list()
                if self._log_panel:
                    self._log_panel.log_info(f'[MQTT] 已取消订阅: {topic}')
            else:
                if self._log_panel:
                    self._log_panel.log_info('[MQTT] 取消订阅失败')
        except Exception as e:
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] 取消订阅失败: {e}')

    def _refresh_sub_list(self):
        """刷新已订阅主题列表（树形结构）"""
        # 清除所有节点
        for item in self._sub_tree.get_children():
            self._sub_tree.delete(item)

        if not self._mqtt:
            return

        subs = self._mqtt.subscriptions
        for topic, qos in subs.items():
            # 按 '/' 分割主题，构建树形结构
            parts = topic.split('/')
            parent = ''
            current_parent_iid = ''
            for i, part in enumerate(parts):
                if not part:
                    continue
                # 查找是否已存在该节点
                found = False
                for child in self._sub_tree.get_children(current_parent_iid):
                    if self._sub_tree.item(child)['text'] == part:
                        current_parent_iid = child
                        found = True
                        break
                if not found:
                    # 创建新节点
                    if i == len(parts) - 1:
                        # 最后一个部分（叶子节点），显示 QoS
                        node_id = self._sub_tree.insert(current_parent_iid, tk.END,
                                                        text=part, values=(f'QoS {qos}',))
                    else:
                        node_id = self._sub_tree.insert(current_parent_iid, tk.END,
                                                        text=part, values=('',))
                    current_parent_iid = node_id
                parent = parent + '/' + part if parent else part

    def _get_filtered_messages(self):
        """获取过滤后的消息列表"""
        topic_filter = self._filter_topic_var.get().strip().lower()
        content_filter = self._filter_content_var.get().strip().lower()
        if not topic_filter and not content_filter:
            return self._messages
        result = []
        for msg in self._messages:
            time_str, topic, qos, payload_hex, payload_text = msg
            if topic_filter and topic_filter not in topic.lower():
                continue
            if content_filter:
                if content_filter not in payload_hex.lower() and content_filter not in payload_text.lower():
                    continue
            result.append(msg)
        return result

    def apply_filter(self):
        """应用过滤条件（公有方法，供外部调用）"""
        self._apply_filter()

    def _apply_filter(self):
        """应用过滤条件"""
        if self._msg_tree is None:
            return
        # 清除当前显示
        for item in self._msg_tree.get_children():
            self._msg_tree.delete(item)
        # 重新插入过滤后的消息
        filtered = self._get_filtered_messages()
        for msg in reversed(filtered):
            self._msg_tree.insert('', tk.END, values=msg)
        # 更新计数
        total = len(self._messages)
        shown = len(filtered)
        self._msg_count_label.configure(text=f'共 {total} 条 (显示 {shown} 条)')

    def clear_filter(self):
        """清除过滤条件（公有方法，供外部调用）"""
        self._clear_filter()

    def _clear_filter(self):
        """清除过滤条件"""
        self._filter_topic_var.set('')
        self._filter_content_var.set('')

    def _update_stats(self):
        """更新消息统计"""
        if not self._messages:
            self._stats_label.configure(text='')
            return
        # 统计各主题消息数
        topic_counts = {}
        for msg in self._messages:
            topic = msg[1]
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        # 取前 3 个主题
        top_topics = sorted(topic_counts.items(), key=lambda x: -x[1])[:3]
        stats_text = ' | '.join(f'{t}: {c}条' for t, c in top_topics)
        self._stats_label.configure(text=stats_text)

    def export_csv(self):
        """导出为 CSV 文件（公有方法，供外部调用）"""
        self._export_csv()

    def _export_csv(self):
        """导出为 CSV 文件"""
        import csv
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension='.csv',
            filetypes=[('CSV 文件', '*.csv'), ('所有文件', '*.*')],
            title='导出消息为 CSV'
        )
        if not path:
            return
        try:
            filtered = self._get_filtered_messages()
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['时间', '主题', 'QoS', '数据(Hex)', '数据(文本)'])
                for msg in filtered:
                    writer.writerow(msg)
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] 已导出 {len(filtered)} 条消息到 {path}')
        except Exception as e:
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] 导出失败: {e}')

    def export_txt(self):
        """导出为 TXT 文件（公有方法，供外部调用）"""
        self._export_txt()

    def _export_txt(self):
        """导出为 TXT 文件"""
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension='.txt',
            filetypes=[('文本文件', '*.txt'), ('所有文件', '*.*')],
            title='导出消息为 TXT'
        )
        if not path:
            return
        try:
            filtered = self._get_filtered_messages()
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f'MQTT 消息导出 ({len(filtered)} 条)\n')
                f.write('=' * 80 + '\n')
                for msg in filtered:
                    time_str, topic, qos, payload_hex, payload_text = msg
                    f.write(f'时间: {time_str}\n')
                    f.write(f'主题: {topic}\n')
                    f.write(f'QoS: {qos}\n')
                    f.write(f'Hex: {payload_hex}\n')
                    f.write(f'文本: {payload_text}\n')
                    f.write('-' * 40 + '\n')
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] 已导出 {len(filtered)} 条消息到 {path}')
        except Exception as e:
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] 导出失败: {e}')

    def export_json(self):
        """导出为 JSON 文件（公有方法，供外部调用）"""
        self._export_json()

    def _export_json(self):
        """导出为 JSON 文件"""
        import json
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension='.json',
            filetypes=[('JSON 文件', '*.json'), ('所有文件', '*.*')],
            title='导出消息为 JSON'
        )
        if not path:
            return
        try:
            filtered = self._get_filtered_messages()
            data = []
            for msg in filtered:
                data.append({
                    'time': msg[0],
                    'topic': msg[1],
                    'qos': msg[2],
                    'payload_hex': msg[3],
                    'payload_text': msg[4],
                })
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] 已导出 {len(filtered)} 条消息到 {path}')
        except Exception as e:
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] 导出失败: {e}')

    def clear_messages(self):
        """清除消息列表（公有方法，供外部调用）"""
        self._clear_messages()

    def _clear_messages(self):
        """清除消息列表"""
        self._messages.clear()
        if self._msg_tree is not None:
            for item in self._msg_tree.get_children():
                self._msg_tree.delete(item)
        if self._msg_count_label is not None:
            self._msg_count_label.configure(text='共 0 条消息')
        if self._stats_label is not None:
            self._stats_label.configure(text='')

    def _get_broker_info(self):
        """获取 Broker 信息（通过 $SYS 主题）"""
        if not self._connected or not self._mqtt:
            if self._log_panel:
                self._log_panel.log_info('[MQTT] 请先连接 Broker')
            return

        # 订阅 $SYS 相关主题
        sys_topics = [
            '$SYS/broker/version',
            '$SYS/broker/uptime',
            '$SYS/broker/clients/total',
            '$SYS/broker/clients/connected',
            '$SYS/broker/messages/received',
            '$SYS/broker/messages/sent',
            '$SYS/broker/bytes/received',
            '$SYS/broker/bytes/sent',
        ]
        for t in sys_topics:
            self._mqtt.subscribe(t, qos=0)

        self._broker_info_var.set('正在获取 Broker 信息...')
        self._sys_info = {}
        self._sys_topic_count = 0
        self._sys_expected = len(sys_topics)

        if self._log_panel:
            self._log_panel.log_info('[MQTT] 正在获取 Broker 信息...')

        # 设置一个临时接收回调来捕获 $SYS 消息
        self._orig_on_receive = self._mqtt._on_receive
        self._mqtt.set_on_receive(self._on_sys_message)

        # 5 秒后超时
        self.after(5000, self._finish_get_broker_info)

    def _on_sys_message(self, data: bytes, topic: str):
        """处理 $SYS 消息"""
        if not topic.startswith('$SYS/'):
            # 不是 $SYS 消息，交给原来的回调
            if self._orig_on_receive:
                self._orig_on_receive(data, topic)
            return

        try:
            value = data.decode('utf-8', errors='replace')
        except Exception:
            value = repr(data)

        self._sys_info[topic] = value
        self._sys_topic_count += 1

        # 更新显示
        info_lines = []
        for t, v in self._sys_info.items():
            name = t.replace('$SYS/broker/', '').replace('/', ' ')
            info_lines.append(f'{name}: {v}')
        self._broker_info_var.set(' | '.join(info_lines))

    def _finish_get_broker_info(self):
        """完成获取 Broker 信息"""
        # 恢复原来的接收回调
        if self._orig_on_receive:
            self._mqtt.set_on_receive(self._orig_on_receive)
            self._orig_on_receive = None

        if self._sys_info:
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] Broker 信息获取完成（{len(self._sys_info)} 项）')
        else:
            self._broker_info_var.set('未获取到 Broker 信息（Broker 可能不支持 $SYS）')
            if self._log_panel:
                self._log_panel.log_info('[MQTT] Broker 不支持 $SYS 主题')

    def _toggle_ping(self):
        """启动/停止 Ping 延迟测试"""
        if self._ping_running:
            self._ping_running = False
            if self._ping_times:
                avg = sum(self._ping_times) / len(self._ping_times)
                self._ping_label.configure(
                    text=f'延迟: min={min(self._ping_times):.1f} max={max(self._ping_times):.1f} avg={avg:.1f} ms ({len(self._ping_times)}次)')
            else:
                self._ping_label.configure(text='延迟: -- ms')
            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] Ping 测试已停止')
        else:
            if not self._connected or not self._mqtt:
                if self._log_panel:
                    self._log_panel.log_info('[MQTT] 请先连接 Broker')
                return

            topic = self._ping_topic_var.get().strip()
            if not topic:
                if self._log_panel:
                    self._log_panel.log_info('[MQTT] 请输入 Ping 主题')
                return

            self._ping_running = True
            self._ping_times = []
            self._ping_label.configure(text='延迟: 测试中...')

            # 订阅 Ping 主题
            self._mqtt.subscribe(topic, qos=0)

            # 保存原始回调并设置 Ping 回调
            self._orig_on_receive_ping = self._mqtt._on_receive
            self._mqtt.set_on_receive(self._on_ping_message)

            # 发送第一个 Ping
            self._do_ping()

            if self._log_panel:
                self._log_panel.log_info(f'[MQTT] Ping 测试已启动（主题: {topic}）')

    def _do_ping(self):
        """发送一个 Ping 消息"""
        if not self._ping_running or not self._connected:
            self._ping_running = False
            return

        import time
        self._ping_send_time = time.time()
        topic = self._ping_topic_var.get().strip()
        payload = str(self._ping_send_time).encode('utf-8')
        self._mqtt.publish(topic, payload, qos=0)

        # 1 秒后检查是否超时
        self.after(1000, self._check_ping_timeout)

    def _on_ping_message(self, data: bytes, topic: str):
        """处理 Ping 回复"""
        import time
        # 计算延迟
        try:
            send_time = float(data.decode('utf-8'))
            delay = (time.time() - send_time) * 1000  # 转换为毫秒
            self._ping_times.append(delay)
            # 只保留最近 100 次
            if len(self._ping_times) > 100:
                self._ping_times = self._ping_times[-100:]

            avg = sum(self._ping_times) / len(self._ping_times)
            self._ping_label.configure(
                text=f'延迟: {delay:.1f} ms (avg={avg:.1f} ms, {len(self._ping_times)}次)')

            # 继续下一次 Ping
            self.after(1000, self._do_ping)
        except Exception:
            pass

    def _check_ping_timeout(self):
        """检查 Ping 是否超时"""
        if not self._ping_running:
            return
        # 如果 1 秒内没有收到回复，发送下一个
        self._do_ping()

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
        if self._log_panel:
            self._log_panel.log_info(f'[MQTT] 消息详情:\n{detail}')

    def get_settings(self) -> dict:
        settings = {
            'host': self._host_var.get(),
            'port': self._port_var.get(),
            'client_id': self._client_id_var.get(),
            'username': self._username_var.get(),
            'password': self._password_var.get(),
            'use_tls': self._tls_var.get(),
            'auto_reconnect': self._auto_reconnect_var.get(),
            'reconnect_delay': self._reconnect_delay_var.get(),
            'max_reconnect_retries': self._max_reconnect_var.get(),
            'will_topic': self._will_topic_var.get(),
            'will_payload': self._will_payload_var.get(),
            'will_qos': self._will_qos_var.get(),
            'will_retain': self._will_retain_var.get(),
            'pub_topic': self._pub_topic_var.get(),
            'pub_qos': self._pub_qos_var.get(),
            'pub_retain': self._pub_retain_var.get(),
            'pub_mode': self._pub_mode.get(),
            'pub_payload': self._pub_payload_var.get(),
            'sub_topic': self._sub_topic_var.get(),
            'sub_qos': self._sub_qos_var.get(),
        }
        # 保存订阅列表（用于持久化）
        if self._mqtt:
            settings['saved_subscriptions'] = dict(self._mqtt.subscriptions)
        return settings

    def load_settings(self, settings: dict):
        if not settings:
            settings = self._defaults
        if 'host' in settings:
            self._host_var.set(settings['host'])
        if 'port' in settings:
            self._port_var.set(str(settings['port']))
        if 'client_id' in settings:
            self._client_id_var.set(settings['client_id'])
        if 'username' in settings:
            self._username_var.set(settings['username'])
        if 'password' in settings:
            self._password_var.set(settings['password'])
        if 'use_tls' in settings:
            self._tls_var.set(settings['use_tls'])
        if 'auto_reconnect' in settings:
            self._auto_reconnect_var.set(settings['auto_reconnect'])
        if 'reconnect_delay' in settings:
            self._reconnect_delay_var.set(str(settings['reconnect_delay']))
        if 'max_reconnect_retries' in settings:
            self._max_reconnect_var.set(str(settings['max_reconnect_retries']))
        if 'will_topic' in settings:
            self._will_topic_var.set(settings['will_topic'])
        if 'will_payload' in settings:
            self._will_payload_var.set(settings['will_payload'])
        if 'will_qos' in settings:
            self._will_qos_var.set(settings['will_qos'])
        if 'will_retain' in settings:
            self._will_retain_var.set(settings['will_retain'])
        if 'pub_topic' in settings:
            self._pub_topic_var.set(settings['pub_topic'])
        if 'pub_qos' in settings:
            self._pub_qos_var.set(settings['pub_qos'])
        if 'pub_retain' in settings:
            self._pub_retain_var.set(settings['pub_retain'])
        if 'pub_mode' in settings:
            self._pub_mode.set(settings['pub_mode'])
        if 'pub_payload' in settings:
            self._pub_payload_var.set(settings['pub_payload'])
        if 'sub_topic' in settings:
            self._sub_topic_var.set(settings['sub_topic'])
        if 'sub_qos' in settings:
            self._sub_qos_var.set(settings['sub_qos'])

        # 恢复订阅列表
        saved_subs = settings.get('saved_subscriptions', {})
        if saved_subs and self._mqtt:
            for topic, qos in saved_subs.items():
                self._mqtt.subscribe(topic, qos=qos)
            self._refresh_sub_list()
