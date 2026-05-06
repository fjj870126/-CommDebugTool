"""通信控制面板 - 协议选择、参数配置、连接/断开
支持多协议同时连接（串口 + TCP + UDP + WebSocket 可同时在线）
采用一体化表格设计，显示所有已连接协议的详细信息
每行支持独立控制发送/接收开关"""

import tkinter as tk
from tkinter import ttk
import socket
from comm.serial_comm import SerialComm
from utils.context_menu import add_entry_context_menu, add_combobox_context_menu
from ui.tooltip import ToolTip


PROTOCOLS = ['TCP客户端', 'TCP服务端', 'UDP', '串口', 'WebSocket客户端', 'WebSocket服务端']
BAUDRATES = ['1200', '2400', '4800', '9600', '19200', '38400', '57600',
             '115200', '230400', '460800', '921600']
PARITIES = ['N', 'E', 'O']
STOPBITS = ['1', '1.5', '2']
DATABITS = ['5', '6', '7', '8']


def get_local_ips() -> list:
    """获取本机所有IP地址"""
    ips = ['127.0.0.1', '0.0.0.0']
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addr = info[4][0]
            if addr not in ips:
                ips.append(addr)
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        default_ip = s.getsockname()[0]
        s.close()
        if default_ip not in ips:
            ips.insert(2, default_ip)
    except Exception:
        pass
    return ips


class CommPanel(ttk.LabelFrame):
    """通信控制面板 - 支持多协议同时连接"""

    def __init__(self, parent, on_connect=None, on_disconnect=None, on_log=None):
        super().__init__(parent, text=' 通信设置 ', padding=8)
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._on_log = on_log
        # 每个协议的连接状态: {proto: info_dict}
        # info_dict = {'addr': str, 'tx': int, 'rx': int, 'clients': {key: info}}
        self._connections = {}  # {proto: info_dict}
        # 发送/接收开关: {item_id: {'send': bool, 'recv': bool}}
        self._switches = {}
        self._tree_refresh_pending = False
        self._build_ui()

    def _build_ui(self):
        # --- 第一行: 协议选择 ---
        self.row0 = ttk.Frame(self)
        self.row0.pack(fill=tk.X, pady=(0, 1))

        ttk.Label(self.row0, text='协议:').pack(side=tk.LEFT)
        self.proto_var = tk.StringVar(value='TCP客户端')
        self.proto_cb = ttk.Combobox(self.row0, textvariable=self.proto_var,
                                     values=PROTOCOLS, state='readonly', width=14)
        self.proto_cb.pack(side=tk.LEFT, padx=(4, 8))
        self.proto_cb.bind('<<ComboboxSelected>>', self._on_protocol_change)
        add_combobox_context_menu(self.proto_cb)

        # 网络参数帧
        self.net_frame = ttk.Frame(self.row0)
        self.net_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(self.net_frame, text='IP:').pack(side=tk.LEFT)
        self.ip_var = tk.StringVar(value='127.0.0.1')
        self._local_ips = get_local_ips()
        self.ip_cb = ttk.Combobox(self.net_frame, textvariable=self.ip_var,
                                  values=self._local_ips, width=12)
        self.ip_cb.pack(side=tk.LEFT, padx=(4, 2))
        add_combobox_context_menu(self.ip_cb)

        ttk.Button(self.net_frame, text='刷新IP', width=6,
                   command=self._refresh_ips).pack(side=tk.LEFT, padx=(0, 4))

        ttk.Label(self.net_frame, text='端口:').pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value='8080')
        self.port_entry = ttk.Entry(self.net_frame, textvariable=self.port_var, width=5)
        self.port_entry.pack(side=tk.LEFT, padx=(4, 0))
        add_entry_context_menu(self.port_entry)

        # UDP 额外参数
        self.udp_frame = ttk.Frame(self.row0)
        ttk.Label(self.udp_frame, text='本地端口:').pack(side=tk.LEFT)
        self.local_port_var = tk.StringVar(value='0')
        self.local_port_entry = ttk.Entry(self.udp_frame, textvariable=self.local_port_var, width=7)
        self.local_port_entry.pack(side=tk.LEFT, padx=(4, 0))
        add_entry_context_menu(self.local_port_entry)
        ToolTip(self.local_port_entry, text_func=lambda: '0 表示系统自动分配')

        # TCP Keepalive 设置
        self.tcp_ka_frame = ttk.Frame(self.row0)
        self.ka_enable_var = tk.BooleanVar(value=False)
        self.ka_idle_var = tk.StringVar(value='60')
        self.ka_interval_var = tk.StringVar(value='10')
        self.ka_count_var = tk.StringVar(value='5')
        ttk.Checkbutton(self.tcp_ka_frame, text='Keepalive', variable=self.ka_enable_var,
                        command=self._on_ka_toggle).pack(side=tk.LEFT)
        self.ka_idle_label = ttk.Label(self.tcp_ka_frame, text='空闲(秒):')
        self.ka_idle_label.pack(side=tk.LEFT, padx=(4, 0))
        self.ka_idle_entry = ttk.Entry(self.tcp_ka_frame, textvariable=self.ka_idle_var, width=4)
        self.ka_idle_entry.pack(side=tk.LEFT, padx=(2, 0))
        self.ka_int_label = ttk.Label(self.tcp_ka_frame, text='间隔(秒):')
        self.ka_int_label.pack(side=tk.LEFT, padx=(4, 0))
        self.ka_int_entry = ttk.Entry(self.tcp_ka_frame, textvariable=self.ka_interval_var, width=4)
        self.ka_int_entry.pack(side=tk.LEFT, padx=(2, 0))
        self.ka_cnt_label = ttk.Label(self.tcp_ka_frame, text='次数:')
        self.ka_cnt_label.pack(side=tk.LEFT, padx=(4, 0))
        self.ka_cnt_entry = ttk.Entry(self.tcp_ka_frame, textvariable=self.ka_count_var, width=3)
        self.ka_cnt_entry.pack(side=tk.LEFT, padx=(2, 0))
        ToolTip(self.ka_idle_entry, text_func=lambda: '无数据后多久开始发送探测包')
        ToolTip(self.ka_int_entry, text_func=lambda: '探测包发送间隔')
        ToolTip(self.ka_cnt_entry, text_func=lambda: '连续未回复次数后断开连接')
        self._update_ka_visibility()

        # --- 参数行容器 ---
        self.param_row = ttk.Frame(self)

        # --- 串口参数 ---
        self.serial_frame = ttk.Frame(self.param_row)

        ttk.Label(self.serial_frame, text='串口:').pack(side=tk.LEFT)
        self.port_list_var = tk.StringVar()
        self.port_list_cb = ttk.Combobox(self.serial_frame, textvariable=self.port_list_var,
                                         state='readonly', width=30)
        self.port_list_cb.pack(side=tk.LEFT, padx=(4, 4))
        add_combobox_context_menu(self.port_list_cb)

        ttk.Button(self.serial_frame, text='刷新', width=4,
                   command=self._refresh_ports).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Label(self.serial_frame, text='波特率:').pack(side=tk.LEFT)
        self.baud_var = tk.StringVar(value='115200')
        self.baud_cb = ttk.Combobox(self.serial_frame, textvariable=self.baud_var,
                     values=BAUDRATES, width=8)
        self.baud_cb.pack(side=tk.LEFT, padx=(4, 8))
        add_combobox_context_menu(self.baud_cb)

        ttk.Label(self.serial_frame, text='数据位:').pack(side=tk.LEFT)
        self.databits_var = tk.StringVar(value='8')
        self.databits_cb = ttk.Combobox(self.serial_frame, textvariable=self.databits_var,
                     values=DATABITS, state='readonly', width=3)
        self.databits_cb.pack(side=tk.LEFT, padx=(4, 8))
        add_combobox_context_menu(self.databits_cb)

        ttk.Label(self.serial_frame, text='校验:').pack(side=tk.LEFT)
        self.parity_var = tk.StringVar(value='N')
        self.parity_cb = ttk.Combobox(self.serial_frame, textvariable=self.parity_var,
                     values=PARITIES, state='readonly', width=3)
        self.parity_cb.pack(side=tk.LEFT, padx=(4, 8))
        add_combobox_context_menu(self.parity_cb)

        ttk.Label(self.serial_frame, text='停止位:').pack(side=tk.LEFT)
        self.stopbits_var = tk.StringVar(value='1')
        self.stopbits_cb = ttk.Combobox(self.serial_frame, textvariable=self.stopbits_var,
                     values=STOPBITS, state='readonly', width=4)
        self.stopbits_cb.pack(side=tk.LEFT, padx=(4, 0))
        add_combobox_context_menu(self.stopbits_cb)

        # --- 连接按钮 ---
        row2 = ttk.Frame(self)
        row2.pack(fill=tk.X, pady=(1, 0))

        self.connect_btn = ttk.Button(row2, text='▶ 新增连接', command=self._do_connect, width=10)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.connect_all_btn = ttk.Button(row2, text='▶▶ 全部连接', command=self._do_connect_all,
                                          state=tk.NORMAL, width=10)
        self.connect_all_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.disconnect_all_btn = ttk.Button(row2, text='■ 全部断开', command=self._do_disconnect_all,
                                             state=tk.NORMAL, width=10)
        self.disconnect_all_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.disconnect_sel_btn = ttk.Button(row2, text='✕ 断开选中', command=self._disconnect_selected,
                                              state=tk.DISABLED, width=10)
        self.disconnect_sel_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.connect_sel_btn = ttk.Button(row2, text='↻ 连接选中', command=self._reconnect_selected,
                                           state=tk.DISABLED, width=10)
        self.connect_sel_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.clear_sel_btn = ttk.Button(row2, text='✂ 清空选中', command=self._do_clear_selected,
                                         state=tk.DISABLED, width=10)
        self.clear_sel_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.clear_btn = ttk.Button(row2, text='🗑 清空全部', command=self._do_clear_connections,
                                    state=tk.DISABLED, width=10)
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 4))

        # --- 连接详情表格 ---
        conn_detail_frame = ttk.LabelFrame(self, text=' 连接详情 ', padding=4)
        conn_detail_frame.pack(fill=tk.BOTH, expand=True, pady=(1, 0))

        # 表格 - 增加发送/接收列
        columns = ('send', 'recv', 'type', 'addr', 'status', 'tx', 'rx')
        self._conn_tree = ttk.Treeview(conn_detail_frame, columns=columns,
                                       show='tree headings', selectmode='extended',
                                       height=3)
        self._conn_tree.heading('#0', text='')
        self._conn_tree.heading('send', text='发送')
        self._conn_tree.heading('recv', text='接收')
        self._conn_tree.heading('type', text='协议')
        self._conn_tree.heading('addr', text='地址')
        self._conn_tree.heading('status', text='状态')
        self._conn_tree.heading('tx', text='TX')
        self._conn_tree.heading('rx', text='RX')

        self._conn_tree.column('#0', width=24, minwidth=24, stretch=False)
        self._conn_tree.column('send', width=40, minwidth=35, anchor=tk.CENTER, stretch=False)
        self._conn_tree.column('recv', width=40, minwidth=35, anchor=tk.CENTER, stretch=False)
        self._conn_tree.column('type', width=80, minwidth=60, anchor=tk.W, stretch=True)
        self._conn_tree.column('addr', width=120, minwidth=80, anchor=tk.W, stretch=True)
        self._conn_tree.column('status', width=90, minwidth=70, anchor=tk.CENTER)
        self._conn_tree.column('tx', width=50, minwidth=40, anchor=tk.CENTER)
        self._conn_tree.column('rx', width=50, minwidth=40, anchor=tk.CENTER)

        v_scroll = ttk.Scrollbar(conn_detail_frame, orient=tk.VERTICAL,
                                 command=self._conn_tree.yview)
        self._conn_tree.configure(yscrollcommand=v_scroll.set)

        self._conn_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 点击发送/接收列切换开关
        self._conn_tree.bind('<ButtonRelease-1>', self._on_tree_click)
        self._conn_tree.bind('<<TreeviewSelect>>', self._on_tree_select)

        # 双击断开连接
        self._conn_tree.bind('<Double-1>', self._on_tree_double_click)

        # 右键菜单
        self._conn_menu = tk.Menu(self._conn_tree, tearoff=0)
        self._conn_menu.add_command(label='断开选中', command=self._disconnect_selected)
        self._conn_tree.bind('<Button-3>', self._show_conn_menu)
        self._conn_tree.bind('<Motion>', self._on_tree_motion)

        # --- 快捷操作按钮 ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(1, 0))

        ttk.Button(btn_frame, text='☑/☐ 全部发送/取消', width=14,
                   command=self._batch_all_send).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(btn_frame, text='☑/☐ 全部接收/取消', width=14,
                   command=self._batch_all_recv).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Separator(btn_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        ttk.Button(btn_frame, text='☑/☐ 选中发送/取消', width=14,
                   command=self._batch_selected_send).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(btn_frame, text='☑/☐ 选中接收/取消', width=14,
                   command=self._batch_selected_recv).pack(side=tk.LEFT, padx=(0, 2))


        # 初始显示 + 启动时自动检测串口
        self._on_protocol_change()
        self._refresh_ports()

    def _show_conn_menu(self, event):
        try:
            item = self._conn_tree.identify_row(event.y)
            if item:
                self._conn_tree.selection_set(item)
                self._conn_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._conn_menu.grab_release()

    def _on_tree_motion(self, event):
        """鼠标移动 - 发送/接收列显示手型光标"""
        region = self._conn_tree.identify_region(event.x, event.y)
        if region == 'cell':
            column = self._conn_tree.identify_column(event.x)
            col_idx = int(column.replace('#', '')) - 1
            if col_idx in (0, 1):  # 发送/接收列
                self._conn_tree.configure(cursor='hand2')
                return
        self._conn_tree.configure(cursor='')

    def _on_tree_click(self, event):
        """点击表格 - 切换发送/接收开关，或检测列宽调整"""
        region = self._conn_tree.identify_region(event.x, event.y)
        if region == 'separator':
            self._save_column_widths()
            return
        if region != 'cell':
            return
        column = self._conn_tree.identify_column(event.x)
        item = self._conn_tree.identify_row(event.y)
        if not item:
            return

        col_idx = int(column.replace('#', '')) - 1  # 0-based
        if col_idx == 0:  # 发送列
            self._toggle_switch(item, 'send')
        elif col_idx == 1:  # 接收列
            self._toggle_switch(item, 'recv')

    # 列宽变化回调（由 main_window 设置，用于触发配置保存）
    _on_column_widths_changed = None

    def _save_column_widths(self):
        """用户拖拽列宽后保存当前列宽"""
        widths = {}
        for col in ('send', 'recv', 'type', 'addr', 'status', 'tx', 'rx'):
            try:
                widths[col] = self._conn_tree.column(col, 'width')
            except Exception:
                pass
        if self._on_column_widths_changed and hasattr(self._on_column_widths_changed, '__call__'):
            self._on_column_widths_changed(widths)

    def _toggle_switch(self, item_id: str, switch_type: str):
        """切换指定行的发送/接收开关（支持父子联动）"""
        if item_id not in self._switches:
            return
        
        # 切换当前节点
        new_state = not self._switches[item_id][switch_type]
        self._switches[item_id][switch_type] = new_state
        self._update_tree_item(item_id)
        
        # 检查是否有子节点（父节点 → 同步子节点）
        children = self._conn_tree.get_children(item_id)
        if children:
            for child_id in children:
                if child_id in self._switches:
                    self._switches[child_id][switch_type] = new_state
                    self._update_tree_item(child_id)
        else:
            # 子节点 → 检查父节点是否需要同步
            parent = self._conn_tree.parent(item_id)
            if parent and parent in self._switches:
                self._sync_parent_state(parent, switch_type)
    
    def _sync_parent_state(self, parent_id: str, switch_type: str):
        """根据所有子节点状态同步父节点开关"""
        children = self._conn_tree.get_children(parent_id)
        if not children:
            return
        
        # 检查所有子节点的状态
        all_enabled = all(
            self._switches.get(child_id, {}).get(switch_type, True)
            for child_id in children
        )
        # 设置父节点状态
        self._switches[parent_id][switch_type] = all_enabled
        self._update_tree_item(parent_id)

    def _batch_switch(self, switch_type: str, value: bool):
        """批量设置发送/接收（支持父子联动）"""
        # 先收集所有需要更新的节点（包括父子关系）
        nodes_to_update = set()
        parent_ids = set()
        
        for item_id in self._switches:
            nodes_to_update.add(item_id)
            # 如果是子节点，也标记其父节点需要检查同步
            parent = self._conn_tree.parent(item_id)
            if parent:
                parent_ids.add(parent)
        
        # 批量设置
        for item_id in nodes_to_update:
            if item_id in self._switches:
                self._switches[item_id][switch_type] = value
                self._update_tree_item(item_id)
        
        # 父节点可能需要根据子节点状态反向同步（批量操作时统一为value）
        for parent_id in parent_ids:
            if parent_id in self._switches:
                self._switches[parent_id][switch_type] = value
                self._update_tree_item(parent_id)
    
    def _batch_toggle(self, switch_type: str):
        """批量反选发送/接收"""
        # 先反选所有节点
        nodes = list(self._switches.keys())
        for item_id in nodes:
            if item_id in self._switches:
                self._switches[item_id][switch_type] = not self._switches[item_id][switch_type]
                self._update_tree_item(item_id)
        
        # 批量反选后，父节点状态应与其子节点保持一致（全部相同）
        # 检查每个父节点
        processed_parents = set()
        for item_id in self._switches:
            parent = self._conn_tree.parent(item_id)
            if parent and parent not in processed_parents:
                processed_parents.add(parent)
                self._sync_parent_state(parent, switch_type)

    def _batch_all_send(self):
        """全部发送/取消切换：有任一关闭则全部打开，全部打开则全部关闭"""
        has_off = any(not sw.get('send', True) for sw in self._switches.values())
        self._batch_switch('send', has_off)

    def _batch_all_recv(self):
        """全部接收/取消切换：有任一关闭则全部打开，全部打开则全部关闭"""
        has_off = any(not sw.get('recv', True) for sw in self._switches.values())
        self._batch_switch('recv', has_off)

    def _batch_selected_send(self):
        """选中行发送/取消切换"""
        sel = self._conn_tree.selection()
        if not sel:
            return
        has_off = any(
            not self._switches.get(item, {}).get('send', True)
            for item in sel if item in self._switches
        )
        for item in sel:
            if item in self._switches:
                old = self._switches[item]['send']
                self._switches[item]['send'] = has_off
                self._update_tree_item(item)
                if old != has_off:
                    self._sync_children(item, 'send', has_off)
                    parent = self._conn_tree.parent(item)
                    if parent and parent in self._switches:
                        self._sync_parent_state(parent, 'send')

    def _batch_selected_recv(self):
        """选中行接收/取消切换"""
        sel = self._conn_tree.selection()
        if not sel:
            return
        has_off = any(
            not self._switches.get(item, {}).get('recv', True)
            for item in sel if item in self._switches
        )
        for item in sel:
            if item in self._switches:
                old = self._switches[item]['recv']
                self._switches[item]['recv'] = has_off
                self._update_tree_item(item)
                if old != has_off:
                    self._sync_children(item, 'recv', has_off)
                    parent = self._conn_tree.parent(item)
                    if parent and parent in self._switches:
                        self._sync_parent_state(parent, 'recv')

    def _sync_children(self, item_id, switch_type, value):
        children = self._conn_tree.get_children(item_id)
        for child_id in children:
            if child_id in self._switches:
                self._switches[child_id][switch_type] = value
                self._update_tree_item(child_id)

    def _update_tree_item(self, item_id: str):
        """更新表格中某一行的显示"""
        if item_id not in self._switches:
            return
        sw = self._switches[item_id]
        send_text = '☑' if sw['send'] else '☐'
        recv_text = '☑' if sw['recv'] else '☐'
        values = list(self._conn_tree.item(item_id, 'values'))
        if len(values) >= 2:
            values[0] = send_text
            values[1] = recv_text
            self._conn_tree.item(item_id, values=tuple(values))

    def _on_tree_select(self, event=None):
        """表格选中切换时控制按钮状态"""
        sel = self._conn_tree.selection()
        has_selection = bool(sel)
        self.disconnect_sel_btn.configure(state=tk.NORMAL if has_selection else tk.DISABLED)
        self.connect_sel_btn.configure(state=tk.NORMAL if has_selection else tk.DISABLED)
        self.clear_sel_btn.configure(state=tk.NORMAL if has_selection else tk.DISABLED)

    def _on_tree_double_click(self, event):
        """双击表格行断开连接"""
        region = self._conn_tree.identify_region(event.x, event.y)
        if region not in ('cell', 'tree'):
            return
        item = self._conn_tree.identify_row(event.y)
        if not item:
            return
        self._conn_tree.selection_set(item)
        self._disconnect_selected()



    def _on_protocol_change(self, event=None):
        proto = self.proto_var.get()
        self.net_frame.pack_forget()
        self.udp_frame.pack_forget()
        self.param_row.pack_forget()
        self.serial_frame.pack_forget()
        self.tcp_ka_frame.pack_forget()

        if proto == '串口':
            self.param_row.pack(fill=tk.X, pady=(2, 0), after=self.row0)
            self.serial_frame.pack(fill=tk.X)
            self._refresh_ports()
        else:
            self.net_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, in_=self.row0)
            if proto == 'UDP':
                self.udp_frame.pack(side=tk.LEFT, in_=self.row0)
            if proto == 'TCP客户端':
                self.tcp_ka_frame.pack(side=tk.LEFT, in_=self.row0, padx=(4, 0))
        self._update_ka_visibility()

    def _on_ka_toggle(self):
        self._update_ka_visibility()

    def _update_ka_visibility(self):
        show = self.proto_var.get() == 'TCP客户端' and self.ka_enable_var.get()
        state = tk.NORMAL if show else tk.DISABLED
        for w in (self.ka_idle_label, self.ka_idle_entry,
                  self.ka_int_label, self.ka_int_entry,
                  self.ka_cnt_label, self.ka_cnt_entry):
            try:
                w.configure(state=state)
            except Exception:
                pass

    def _refresh_ips(self):
        self._local_ips = get_local_ips()
        self.ip_cb['values'] = self._local_ips

    def _refresh_ports(self):
        ports = SerialComm.list_ports()
        port_names = [f'{p[0]} - {p[1]}' for p in ports]
        self.port_list_cb['values'] = port_names
        if port_names and not self.port_list_var.get():
            self.port_list_cb.current(0)

    def _do_connect(self):
        """根据输入框参数添加一条连接记录到表格（不实际连接）"""
        config = self.get_config()
        proto = config['protocol']
        if proto == 'TCP客户端':
            key = f'TCP客户端 {config["host"]}:{config["port"]}'
            if key not in self._connections:
                self._connections[key] = {'addr': f'{config["host"]}:{config["port"]}', 'tx': 0, 'rx': 0, 'status': '已断开', 'clients': {}}
            elif self._on_log:
                self._on_log(f'[新增连接] {key} 已存在，忽略')
        elif proto == 'TCP服务端':
            key = f'{config["host"]}:{config["port"]}'
            if key not in self._connections:
                self._connections[key] = {'addr': key, 'tx': 0, 'rx': 0, 'status': '已断开', 'clients': {}}
            elif self._on_log:
                self._on_log(f'[新增连接] {key} 已存在，忽略')
        elif proto == 'UDP':
            if proto not in self._connections:
                info = f'{config["host"]}:{config["port"]}'
                self._connections[proto] = {'addr': info, 'tx': 0, 'rx': 0, 'status': '已断开', 'clients': {}}
            elif self._on_log:
                self._on_log(f'[新增连接] {proto} 已存在，忽略')
        elif proto == '串口':
            key = f'串口 {config["port"]}'
            if key not in self._connections:
                info = f'{config["port"]} {config["baudrate"]}'
                self._connections[key] = {'addr': info, 'tx': 0, 'rx': 0, 'status': '已断开', 'clients': {}}
            elif self._on_log:
                self._on_log(f'[新增连接] {key} 已存在，忽略')
        elif proto in ('WebSocket客户端', 'WebSocket服务端'):
            if proto not in self._connections:
                info = f'{config["host"]}:{config["port"]}'
                self._connections[proto] = {'addr': info, 'tx': 0, 'rx': 0, 'status': '已断开', 'clients': {}}
            elif self._on_log:
                self._on_log(f'[新增连接] {proto} 已存在，忽略')
        self._schedule_tree_refresh()


    def _get_disconnected_configs(self, items):
        """从 tree items 中收集所有已断开的连接配置"""
        configs = []
        for item in items:
            values = self._conn_tree.item(item, 'values')
            if not values or len(values) < 5:
                continue
            display = values[2]
            addr = values[3]
            config = None
            if display == 'TCP服务端':
                if ':' in addr:
                    host, port = addr.rsplit(':', 1)
                    config = {'protocol': 'TCP服务端', 'host': host, 'port': int(port)}
            elif display == 'TCP客户端':
                if ':' in addr:
                    host, port = addr.rsplit(':', 1)
                    config = {'protocol': 'TCP客户端', 'host': host, 'port': int(port)}
            elif display == 'UDP':
                if ':' in addr:
                    host, port = addr.rsplit(':', 1)
                    config = {'protocol': 'UDP', 'host': host, 'port': int(port)}
            elif display == '串口':
                parts = addr.split(' ')
                port_name = parts[0] if parts else ''
                baud = int(parts[1]) if len(parts) > 1 else 115200
                config = {'protocol': '串口', 'port': port_name, 'baudrate': baud, 'bytesize': 8, 'parity': 'N', 'stopbits': 1}
            elif display in ('WebSocket客户端', 'WebSocket服务端'):
                if ':' in addr:
                    host, port = addr.rsplit(':', 1)
                    config = {'protocol': display, 'host': host, 'port': int(port)}
            if config:
                configs.append(config)
        return configs

    def _do_connect_all(self):
        """扫描表格中所有已断开的父节点记录，逐个重连"""
        configs = self._get_disconnected_configs(self._conn_tree.get_children())
        for config in configs:
            if self._on_connect:
                self._on_connect(config)

    def _reconnect_selected(self):
        """连接选中的行（支持多选）"""
        configs = self._get_disconnected_configs([
            item for item in self._conn_tree.selection()
            if not self._conn_tree.parent(item)
        ])
        for config in configs:
            if self._on_connect:
                self._on_connect(config)

    def _do_disconnect_all(self):
        """断开所有协议"""
        if self._on_disconnect:
            self._on_disconnect()
        self.clear_btn.configure(state=tk.NORMAL)

    def _do_clear_selected(self):
        """清空选中的连接记录（支持多选，只清空父节点）"""
        keys_to_remove = set()
        for item in self._conn_tree.selection():
            if self._conn_tree.parent(item):
                continue
            values = self._conn_tree.item(item, 'values')
            if not values or len(values) < 3:
                continue
            display = values[2]
            addr = values[3] if len(values) > 3 else ''
            key = self._tree_display_to_key(display, addr)
            if key:
                keys_to_remove.add(key)
        for key in keys_to_remove:
            self._connections.pop(key, None)
        self._schedule_tree_refresh()

    def _do_clear_connections(self):
        """清空全部连接（先断开所有，再清空记录）"""
        if self._on_disconnect:
            self._on_disconnect()
        self._connections.clear()
        self._switches.clear()
        self._schedule_tree_refresh()
        self.clear_btn.configure(state=tk.DISABLED)

    def _disconnect_selected(self):
        """断开选中的连接（支持多选）"""
        for item in self._conn_tree.selection():
            parent = self._conn_tree.parent(item)
            if parent:  # 是子节点（客户端）
                p_vals = self._conn_tree.item(parent, 'values')
                p_display = p_vals[2] if len(p_vals) > 2 else ''
                p_addr = p_vals[3] if len(p_vals) > 3 else ''
                proto = self._tree_display_to_key(p_display, p_addr)
                client_key = self._conn_tree.item(item, 'values')[3]
                if self._on_disconnect:
                    self._on_disconnect(proto=proto, client_key=client_key)
            else:  # 是父节点（协议）
                values = self._conn_tree.item(item, 'values')
                if values:
                    display = values[2] if len(values) > 2 else ''
                    addr = values[3] if len(values) > 3 else ''
                    proto = self._tree_display_to_key(display, addr)
                    if self._on_disconnect:
                        self._on_disconnect(proto=proto)

    def _tree_display_to_key(self, display_proto: str, addr: str) -> str:
        """将 tree 中的显示协议名转回 _connections 的 key"""
        if display_proto == 'TCP服务端':
            return addr
        if display_proto == 'TCP客户端':
            return f'TCP客户端 {addr}'
        if display_proto == '串口':
            return f'串口 {addr}'
        return display_proto

    def set_connected(self, proto: str, connected: bool, info: str = ''):
        """设置指定协议的连接状态"""
        if connected:
            if proto not in self._connections:
                self._connections[proto] = {
                    'addr': info,
                    'tx': 0,
                    'rx': 0,
                    'status': '已连接',
                    'clients': {},
                }
            if ':' in proto and not any(proto.startswith(p) for p in ('TCP', 'UDP', 'WebSocket')):
                self._connections[proto]['status'] = '监听中'
            else:
                self._connections[proto]['status'] = '已连接'
        else:
            if proto in self._connections:
                self._connections[proto]['status'] = '已断开'
        self._schedule_tree_refresh()

    def _update_tree_values(self, item_id: str, tx_val: str, rx_val: str):
        """只更新指定行的 TX/RX 值，不重建树"""
        if not self._conn_tree.exists(item_id):
            return
        values = list(self._conn_tree.item(item_id, 'values'))
        if len(values) >= 7:
            values[5] = tx_val
            values[6] = rx_val
            self._conn_tree.item(item_id, values=tuple(values))

    def _find_tree_item_by_conn_key(self, conn_key: str) -> str:
        """根据 _connections 的 key 查找 tree 中的 item_id"""
        for item in self._conn_tree.get_children():
            values = self._conn_tree.item(item, 'values')
            if not values or len(values) < 4:
                continue
            display_proto = values[2]
            addr = values[3]
            # TCP服务端: _connections key 是 host:port, tree 中 addr 也是 host:port, display_proto 是 'TCP服务端'
            if ':' in conn_key and not any(conn_key.startswith(p) for p in ('TCP', 'UDP', 'WebSocket')):
                if display_proto == 'TCP服务端' and addr == conn_key:
                    return item
            elif conn_key.startswith('TCP客户端 '):
                if display_proto == 'TCP客户端' and addr == conn_key[len('TCP客户端 '):]:
                    return item
            else:
                if display_proto == conn_key:
                    return item
        return None

    def update_tx_rx(self, proto: str, is_tx: bool, client_key: str = None):
        """更新收发计数（不重建树，保留展开状态）"""
        conn = self._connections.get(proto)
        if not conn:
            return
        
        parent_item = None
        child_item = None
        
        # 查找对应的树节点
        parent_item = self._find_tree_item_by_conn_key(proto)
        
        if client_key and parent_item:
            for child in self._conn_tree.get_children(parent_item):
                cvals = self._conn_tree.item(child, 'values')
                if len(cvals) >= 4 and cvals[3] == client_key:
                    child_item = child
                    break
        
        if client_key:
            client = conn['clients'].get(client_key)
            if client:
                if is_tx:
                    conn['tx'] += 1
                    client['tx'] += 1
                else:
                    conn['rx'] += 1
                    client['rx'] += 1
                # 更新子节点和父节点
                if child_item:
                    self._update_tree_values(child_item, str(client['tx']), str(client['rx']))
                if parent_item:
                    self._update_tree_values(parent_item, str(conn['tx']), str(conn['rx']))
        else:
            if is_tx:
                conn['tx'] += 1
            else:
                conn['rx'] += 1
            if parent_item:
                self._update_tree_values(parent_item, str(conn['tx']), str(conn['rx']))

    def set_client_connected(self, proto: str, client_key: str, connected: bool):
        """设置TCP服务端的客户端连接状态"""
        conn = self._connections.get(proto)
        if not conn:
            return
        if connected:
            conn['clients'][client_key] = {'tx': 0, 'rx': 0}
        else:
            conn['clients'].pop(client_key, None)
        self._schedule_tree_refresh()
        for item in self._conn_tree.get_children():
            values = self._conn_tree.item(item, 'values')
            if not values:
                continue
            display_proto = values[2]
            addr = values[3] if len(values) > 3 else ''
            if display_proto == 'TCP服务端' and addr == proto:
                self._conn_tree.item(item, open=True)
                break
    
    def get_client_count(self, proto: str = None) -> int:
        """获取客户端数量
        如果指定 proto，返回该协议的客户端数；否则返回所有TCP服务端的总客户端数
        """
        if proto:
            conn = self._connections.get(proto)
            if conn:
                return len(conn.get('clients', {}))
            return 0
        # 统计所有TCP服务端的客户端总数
        total = 0
        for proto_key, info in self._connections.items():
            if '服务端' in proto_key:
                total += len(info.get('clients', {}))
        return total

    def set_status(self, proto: str, status: str):
        """设置协议状态"""
        conn = self._connections.get(proto)
        if conn:
            conn['status'] = status
            self._schedule_tree_refresh()

    def _schedule_tree_refresh(self):
        """合并短时间内多次刷新请求，延迟到空闲时执行"""
        if self._tree_refresh_pending:
            return
        self._tree_refresh_pending = True
        self.after(10, self._do_refresh_tree)

    def _do_refresh_tree(self):
        self._tree_refresh_pending = False
        self._refresh_conn_tree()

    def _refresh_conn_tree(self):
        """刷新连接详情表格（保留用户开关状态）"""
        # 保存当前展开状态
        expanded = {}
        for item in self._conn_tree.get_children():
            expanded[item] = self._conn_tree.item(item, 'open')
        
        # 保存现有开关状态：通过 (proto, client_key) 标识
        old_states = {}  # {(proto, client_key): {'send': bool, 'recv': bool}}
        for item_id, sw in self._switches.items():
            # 检查item是否存在（可能已被删除）
            if not self._conn_tree.exists(item_id):
                continue
            values = self._conn_tree.item(item_id, 'values')
            if not values:
                continue
            parent = self._conn_tree.parent(item_id)
            if parent:  # 客户端子节点
                parent_vals = self._conn_tree.item(parent, 'values')
                if len(parent_vals) >= 3:
                    proto = parent_vals[2]
                    client_key = values[3] if len(values) > 3 else ''
                    old_states[(proto, client_key)] = sw.copy()
            else:  # 协议父节点
                if len(values) >= 3:
                    proto = values[2]
                    old_states[(proto, None)] = sw.copy()

        self._conn_tree.delete(*self._conn_tree.get_children())
        self._switches.clear()

        for proto, info in self._connections.items():
            status_icon = '🟢' if '监听' in info['status'] or '已连接' in info['status'] else '🔴'
            client_count = len(info.get('clients', {}))
            status_text = f'{status_icon} {info["status"]}'
            if client_count > 0:
                status_text += f' ({client_count}客户端)'
            
            # 如果 key 是 host:port 格式（TCP服务端多实例），显示为 TCP服务端
            if proto.startswith('TCP客户端 '):
                display_proto = 'TCP客户端'
                addr = proto[len('TCP客户端 '):]
            elif proto.startswith('串口 '):
                display_proto = '串口'
                addr = proto[len('串口 '):]
            elif ':' in proto and not any(proto.startswith(p) for p in ('TCP', 'UDP', 'WebSocket')):
                display_proto = 'TCP服务端'
                addr = proto
            else:
                display_proto = proto
                addr = info.get('addr', '')
            
            # 按协议类型选择颜色标签
            connected = '监听' in info['status'] or '已连接' in info['status']
            is_connected_norm = info['status'] not in ('已断开', '未连接')
            if not connected and not is_connected_norm:
                proto_tag = 'tag_disconnected'
            else:
                base_proto = display_proto.split(' ')[0]  # "TCP客户端" → "TCP客户端"
                proto_tag = f'tag_{base_proto}'
                if proto_tag not in ('tag_TCP客户端', 'tag_TCP服务端', 'tag_串口', 'tag_UDP', 'tag_WebSocket'):
                    proto_tag = 'proto'
            item_id = self._conn_tree.insert('', tk.END,
                text='●',
                values=('☑', '☑', display_proto, addr,
                       status_text,
                       str(info['tx']), str(info['rx'])),
                tags=('proto', proto_tag))
            
            # 恢复或默认开关状态
            key = (proto, None)
            if key in old_states:
                self._switches[item_id] = old_states[key].copy()
            else:
                self._switches[item_id] = {'send': True, 'recv': True}
            # 立即更新该行的显示图标
            self._update_tree_item(item_id)

            # 如果有客户端，添加为子节点
            if info['clients']:
                for client_key, client_info in info['clients'].items():
                    child_id = self._conn_tree.insert(item_id, tk.END,
                        text='',
                        values=('☑', '☑', '  └ 客户端', client_key, '🟢 已连接',
                               str(client_info['tx']), str(client_info['rx'])),
                        tags=('client',))
                    # 恢复或默认开关状态
                    child_key = (proto, client_key)
                    if child_key in old_states:
                        self._switches[child_id] = old_states[child_key].copy()
                    else:
                        self._switches[child_id] = {'send': True, 'recv': True}
                    # 立即更新该行的显示图标
                    self._update_tree_item(child_id)

            # 恢复展开状态
            if item_id in expanded and expanded[item_id]:
                self._conn_tree.item(item_id, open=True)

        # 如果没有连接，显示提示
        if not self._connections:
            self._conn_tree.insert('', tk.END, text='',
                                   values=('', '', '(无连接)', '', '', '', ''),
                                   tags=('empty',))

        # 设置标签样式 - 所有行使用相同字体大小
        self._conn_tree.tag_configure('proto', font=('', 9))
        self._conn_tree.tag_configure('client', font=('', 9))
        self._conn_tree.tag_configure('empty', foreground='gray')
        # 按协议类型着色
        self._conn_tree.tag_configure('tag_TCP客户端', foreground='#1565C0')
        self._conn_tree.tag_configure('tag_TCP服务端', foreground='#2E7D32')
        self._conn_tree.tag_configure('tag_串口', foreground='#E65100')
        self._conn_tree.tag_configure('tag_UDP', foreground='#6A1B9A')
        self._conn_tree.tag_configure('tag_WebSocket', foreground='#00838F')
        self._conn_tree.tag_configure('tag_disconnected', foreground='#999999')
        
        # 刷新后更新清空按钮状态
        if not self._connections:
            self.clear_btn.configure(state=tk.DISABLED)
        else:
            self.clear_btn.configure(state=tk.NORMAL)

        # 动态调整表格高度（最小3行，最大8行）
        row_count = max(1, len(self._conn_tree.get_children()))
        new_height = max(3, min(8, row_count + 1))
        current_height = self._conn_tree.cget('height')
        if current_height != new_height:
            self._conn_tree.configure(height=new_height)

    def get_selected_client_key(self) -> str:
        """获取当前选中的客户端key（用于发送目标）"""
        sel = self._conn_tree.selection()
        if not sel:
            return None
        item = sel[0]
        parent = self._conn_tree.parent(item)
        if parent:  # 是客户端子节点
            return self._conn_tree.item(item, 'values')[3]  # addr列
        return None

    def get_send_targets(self) -> list:
        """获取所有开启了发送开关的连接/客户端列表
        返回: [(proto, client_key_or_None), ...]
        """
        targets = []
        parent_send = {}
        child_send = {}
        # 表格中 display_proto 到 _connections key 的映射
        display_to_key = {}
        for key in self._connections:
            if ':' in key and not any(key.startswith(p) for p in ('TCP', 'UDP', 'WebSocket')):
                display_to_key[key] = key
                display_to_key['TCP服务端'] = key
            else:
                display_to_key[key] = key
            # 建立显示名到 key 的映射
            if key.startswith('TCP客户端 '):
                display_to_key['TCP客户端'] = key
            if key.startswith('串口 '):
                display_to_key['串口'] = key

        for item_id, sw in self._switches.items():
            if not sw['send']:
                continue
            parent = self._conn_tree.parent(item_id)
            values = self._conn_tree.item(item_id, 'values')
            if parent:
                parent_display = self._conn_tree.item(parent, 'values')[2]
                conn_key = display_to_key.get(parent_display, parent_display)
                client_key = values[3]
                child_send[(conn_key, client_key)] = True
            else:
                display = values[2]
                conn_key = display_to_key.get(display, display)
                parent_send[conn_key] = True
        
        for conn_key, info in self._connections.items():
            if parent_send.get(conn_key):
                targets.append((conn_key, None))
            else:
                for client_key in info.get('clients', {}):
                    if child_send.get((conn_key, client_key)):
                        targets.append((conn_key, client_key))
        
        return targets

    def get_recv_targets(self) -> list:
        """获取所有开启了接收开关的连接/客户端列表
        返回: [(proto, client_key_or_None), ...]
        """
        targets = []
        for item_id, sw in self._switches.items():
            if not sw['recv']:
                continue
            parent = self._conn_tree.parent(item_id)
            values = self._conn_tree.item(item_id, 'values')
            if parent:  # 是客户端子节点
                proto = self._conn_tree.item(parent, 'values')[2]
                client_key = values[3]
                targets.append((proto, client_key))
            else:  # 是协议父节点
                proto = values[2]
                targets.append((proto, None))
        return targets

    def get_connected_protocols(self) -> list:
        """获取所有已连接的协议列表"""
        return list(self._connections.keys())

    def is_any_connected(self) -> bool:
        """是否有任何协议已连接"""
        return len(self._connections) > 0

    def get_config(self) -> dict:
        proto = self.proto_var.get()
        config = {'protocol': proto}
        if proto == '串口':
            port_str = self.port_list_var.get()
            config['port'] = port_str.split(' - ')[0] if ' - ' in port_str else port_str
            config['baudrate'] = int(self.baud_var.get())
            config['bytesize'] = int(self.databits_var.get())
            config['parity'] = self.parity_var.get()
            config['stopbits'] = float(self.stopbits_var.get())
        else:
            config['host'] = self.ip_var.get()
            config['port'] = int(self.port_var.get())
            if proto == 'UDP':
                config['local_port'] = int(self.local_port_var.get())
            if proto == 'TCP客户端':
                config['keepalive'] = {
                    'enabled': self.ka_enable_var.get(),
                    'idle': int(self.ka_idle_var.get()),
                    'interval': int(self.ka_interval_var.get()),
                    'count': int(self.ka_count_var.get()),
                }
        return config

    def get_settings(self) -> dict:
        """获取所有设置用于保存"""
        # 保存当前列宽
        col_widths = {}
        for col in ('send', 'recv', 'type', 'addr', 'status', 'tx', 'rx'):
            try:
                col_widths[col] = self._conn_tree.column(col, 'width')
            except Exception:
                pass
        return {
            'protocol': self.proto_var.get(),
            'ip': self.ip_var.get(),
            'port': self.port_var.get(),
            'local_port': self.local_port_var.get(),
            'serial_port': self.port_list_var.get(),
            'baudrate': self.baud_var.get(),
            'databits': self.databits_var.get(),
            'parity': self.parity_var.get(),
            'stopbits': self.stopbits_var.get(),
            'column_widths': col_widths,
        }

    def get_connections_save_data(self) -> list:
        """获取连接详情中所有协议记录的序列化数据"""
        data = []
        for key, info in self._connections.items():
            entry = {
                'key': key,
                'addr': info.get('addr', ''),
                'tx': 0,
                'rx': 0,
                'status': '已断开',
                'clients': {},
                'switches': {},
            }
            if ':' in key and not any(key.startswith(p) for p in ('TCP', 'UDP', 'WebSocket')):
                display = 'TCP服务端'
                addr = key
            elif key.startswith('TCP客户端 '):
                display = 'TCP客户端'
                addr = key[len('TCP客户端 '):]
            elif key.startswith('串口 '):
                display = '串口'
                addr = key[len('串口 '):]
            elif key == 'UDP':
                display = 'UDP'
                addr = info.get('addr', '')
            elif key in ('WebSocket客户端', 'WebSocket服务端'):
                display = key
                addr = info.get('addr', '')
            else:
                continue
            entry['config'] = self._display_to_config(display, addr, info.get('addr', ''))
            data.append(entry)
        return data

    def _display_to_config(self, display: str, addr: str, raw_addr: str) -> dict:
        """根据显示协议名和地址构造 config dict"""
        if display == 'TCP服务端':
            if ':' in addr:
                host, port = addr.rsplit(':', 1)
                return {'protocol': 'TCP服务端', 'host': host, 'port': int(port)}
        elif display == 'TCP客户端':
            if ':' in addr:
                host, port = addr.rsplit(':', 1)
                return {'protocol': 'TCP客户端', 'host': host, 'port': int(port)}
        elif display == 'UDP':
            if ':' in raw_addr:
                host, port = raw_addr.rsplit(':', 1)
                return {'protocol': 'UDP', 'host': host, 'port': int(port)}
        elif display == '串口':
            parts = raw_addr.split(' ')
            port_name = parts[0] if parts else addr
            baud = int(parts[1]) if len(parts) > 1 else 115200
            return {'protocol': '串口', 'port': port_name, 'baudrate': baud, 'bytesize': 8, 'parity': 'N', 'stopbits': 1}
        elif display in ('WebSocket客户端', 'WebSocket服务端'):
            if ':' in raw_addr:
                host, port = raw_addr.rsplit(':', 1)
                return {'protocol': display, 'host': host, 'port': int(port)}
        return {}

    def load_connections_save_data(self, data: list):
        """从序列化数据恢复连接详情记录"""
        if not data:
            return
        for entry in data:
            key = entry.get('key')
            if not key:
                continue
            # 向前兼容：旧版串口 key 是 '串口'，新版是 '串口 <port>'
            if key == '串口' and entry.get('addr'):
                parts = entry['addr'].split(' ')
                if parts:
                    key = f'串口 {parts[0]}'
            self._connections[key] = {
                'addr': entry.get('addr', ''),
                'tx': 0,
                'rx': 0,
                'status': '已断开',
                'clients': {},
            }
        self._schedule_tree_refresh()

    def load_settings(self, settings: dict):
        """从保存的设置恢复"""
        if not settings:
            return
        self.proto_var.set(settings.get('protocol', 'TCP客户端'))
        self.ip_var.set(settings.get('ip', '127.0.0.1'))
        self.port_var.set(settings.get('port', '8080'))
        self.local_port_var.set(settings.get('local_port', '0'))
        if settings.get('serial_port'):
            self.port_list_var.set(settings['serial_port'])
        self.baud_var.set(settings.get('baudrate', '115200'))
        self.databits_var.set(settings.get('databits', '8'))
        self.parity_var.set(settings.get('parity', 'N'))
        self.stopbits_var.set(settings.get('stopbits', '1'))
        self._on_protocol_change()

        # 恢复列宽
        col_widths = settings.get('column_widths', {})
        for col, width in col_widths.items():
            try:
                self._conn_tree.column(col, width=width)
            except Exception:
                pass
