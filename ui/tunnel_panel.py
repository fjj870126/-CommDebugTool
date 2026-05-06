"""数据隧道面板 - 单向转发/双向隧道，支持 TCP/UDP"""

import tkinter as tk
from tkinter import ttk, messagebox
import socket
import threading
import select
import time
from datetime import datetime
from utils.context_menu import add_entry_context_menu
from ui.status_bus import StatusBus


class TunnelPanel(ttk.LabelFrame):
    """数据隧道面板 - 支持单向转发和双向隧道"""

    def __init__(self, parent, log_panel=None):
        super().__init__(parent, text=' 数据隧道 ', padding=8)
        self._log_panel = log_panel
        self._running = False
        self._threads = []
        self._build_ui()

    def _build_ui(self):
        # 模式选择
        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(mode_frame, text='模式:').pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value='双向隧道')
        mode_cb = ttk.Combobox(mode_frame, textvariable=self.mode_var,
                               values=['双向隧道', '单向转发'],
                               state='readonly', width=12)
        mode_cb.pack(side=tk.LEFT, padx=(4, 0))
        mode_cb.bind('<<ComboboxSelected>>', self._on_mode_change)

        # 隧道配置
        config_frame = ttk.LabelFrame(self, text=' 隧道配置 ', padding=6)
        config_frame.pack(fill=tk.X, pady=(0, 4))

        # 监听端
        listen_frame = ttk.LabelFrame(config_frame, text=' 监听端 ', padding=4)
        listen_frame.pack(fill=tk.X, pady=(0, 4))

        row1 = ttk.Frame(listen_frame)
        row1.pack(fill=tk.X)

        ttk.Label(row1, text='类型:').pack(side=tk.LEFT)
        self.listen_type_var = tk.StringVar(value='TCP')
        ttk.Combobox(row1, textvariable=self.listen_type_var,
                     values=['TCP', 'UDP'], state='readonly', width=6).pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(row1, text='监听地址:').pack(side=tk.LEFT)
        self.listen_host_var = tk.StringVar(value='0.0.0.0')
        self.listen_host_entry = ttk.Entry(row1, textvariable=self.listen_host_var, width=12)
        self.listen_host_entry.pack(side=tk.LEFT, padx=(4, 0))
        add_entry_context_menu(self.listen_host_entry)

        ttk.Label(row1, text=':').pack(side=tk.LEFT)
        self.listen_port_var = tk.StringVar(value='8888')
        self.listen_port_entry = ttk.Entry(row1, textvariable=self.listen_port_var, width=6)
        self.listen_port_entry.pack(side=tk.LEFT)
        add_entry_context_menu(self.listen_port_entry)

        # 目标端
        target_frame = ttk.LabelFrame(config_frame, text=' 目标端 ', padding=4)
        target_frame.pack(fill=tk.X)

        row2 = ttk.Frame(target_frame)
        row2.pack(fill=tk.X)

        ttk.Label(row2, text='类型:').pack(side=tk.LEFT)
        self.target_type_var = tk.StringVar(value='TCP')
        ttk.Combobox(row2, textvariable=self.target_type_var,
                     values=['TCP', 'UDP'], state='readonly', width=6).pack(side=tk.LEFT, padx=(4, 12))

        ttk.Label(row2, text='目标地址:').pack(side=tk.LEFT)
        self.target_host_var = tk.StringVar(value='127.0.0.1')
        self.target_host_entry = ttk.Entry(row2, textvariable=self.target_host_var, width=12)
        self.target_host_entry.pack(side=tk.LEFT, padx=(4, 0))
        add_entry_context_menu(self.target_host_entry)

        ttk.Label(row2, text=':').pack(side=tk.LEFT)
        self.target_port_var = tk.StringVar(value='8889')
        self.target_port_entry = ttk.Entry(row2, textvariable=self.target_port_var, width=6)
        self.target_port_entry.pack(side=tk.LEFT)
        add_entry_context_menu(self.target_port_entry)

        # 单向转发过滤规则（仅在单向转发模式显示）
        self.filter_frame = ttk.LabelFrame(config_frame, text=' 过滤规则 ', padding=4)
        
        row3 = ttk.Frame(self.filter_frame)
        row3.pack(fill=tk.X)
        
        ttk.Label(row3, text='规则:').pack(side=tk.LEFT)
        self.rule_var = tk.StringVar(value='全部转发')
        ttk.Combobox(row3, textvariable=self.rule_var,
                     values=['全部转发', '仅转发TX', '仅转发RX', '自定义过滤'],
                     state='readonly', width=14).pack(side=tk.LEFT, padx=(2, 8))
        
        ttk.Label(row3, text='过滤(Hex):').pack(side=tk.LEFT)
        self.filter_var = tk.StringVar(value='')
        self.filter_entry = ttk.Entry(row3, textvariable=self.filter_var, width=15)
        self.filter_entry.pack(side=tk.LEFT, padx=(2, 0))
        add_entry_context_menu(self.filter_entry)

        # 操作按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(0, 4))

        self.start_btn = ttk.Button(btn_frame, text='▶ 启动', command=self._toggle_tunnel, width=10)
        self.start_btn.pack(side=tk.LEFT)

        ttk.Button(btn_frame, text='测试连接', command=self._test_target,
                   width=8).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Button(btn_frame, text='清空日志', command=self._clear_log,
                   width=8).pack(side=tk.LEFT, padx=(4, 8))

        # 流量统计
        self._tx_bytes = 0
        self._rx_bytes = 0
        self._traffic_label = ttk.Label(btn_frame, text='TX: 0  RX: 0', font=('', 9), foreground='gray')
        self._traffic_label.pack(side=tk.RIGHT, padx=(0, 8))

        self.status_var = tk.StringVar(value='已停止')
        ttk.Label(btn_frame, textvariable=self.status_var, foreground='gray').pack(side=tk.RIGHT, padx=(0, 8))

        # 转发日志
        log_frame = ttk.LabelFrame(self, text=' 转发日志 ', padding=4)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=10, font=('Courier New', 9),
                                wrap=tk.NONE, state=tk.DISABLED)
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        self.log_text.grid(row=0, column=0, sticky='nsew')
        log_scroll.grid(row=0, column=1, sticky='ns')
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text.tag_configure('info', foreground='blue')
        self.log_text.tag_configure('data', foreground='black')
        self.log_text.tag_configure('error', foreground='red')

    def _on_mode_change(self, event=None):
        """切换模式时显示/隐藏过滤规则"""
        if self.mode_var.get() == '单向转发':
            self.filter_frame.pack(fill=tk.X, pady=(0, 4))
        else:
            self.filter_frame.pack_forget()

    def _update_traffic(self):
        """更新流量统计显示"""
        self._traffic_label.configure(text=f'TX: {self._tx_bytes}  RX: {self._rx_bytes}')

    def _toggle_tunnel(self):
        """切换隧道状态"""
        if self._running:
            self._stop_tunnel()
        else:
            self._start_tunnel()

    def _start_tunnel(self):
        """启动隧道"""
        listen_type = self.listen_type_var.get()
        listen_host = self.listen_host_var.get().strip()
        try:
            listen_port = int(self.listen_port_var.get())
        except ValueError:
            messagebox.showerror('错误', '监听端口格式错误')
            return

        target_type = self.target_type_var.get()
        target_host = self.target_host_var.get().strip()
        try:
            target_port = int(self.target_port_var.get())
        except ValueError:
            messagebox.showerror('错误', '目标端口格式错误')
            return

        if not listen_host or not target_host:
            messagebox.showerror('错误', '请输入地址')
            return

        self._running = True
        self.start_btn.configure(text='⏹ 停止')
        self.status_var.set('运行中')
        StatusBus.send('隧道', f'{mode} {listen_type} {listen_host}:{listen_port}', 'success')

        mode = self.mode_var.get()
        self._add_log(f'▶ {mode}启动: {listen_type} {listen_host}:{listen_port} → '
                      f'{target_type} {target_host}:{target_port}', 'info')

        # 启动监听线程
        thread = threading.Thread(
            target=self._run_tunnel,
            args=(listen_type, listen_host, listen_port,
                  target_type, target_host, target_port),
            daemon=True
        )
        thread.start()
        self._threads.append(thread)

    def _run_tunnel(self, listen_type, listen_host, listen_port,
                    target_type, target_host, target_port):
        """运行隧道"""
        try:
            if listen_type == 'TCP':
                self._run_tcp_tunnel(listen_host, listen_port,
                                     target_type, target_host, target_port)
            else:
                self._run_udp_tunnel(listen_host, listen_port,
                                     target_type, target_host, target_port)
        except Exception as e:
            self._add_log_async(f'隧道错误: {e}', 'error')
            self._stop_tunnel_async()

    def _run_tcp_tunnel(self, listen_host, listen_port,
                        target_type, target_host, target_port):
        """运行TCP隧道"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((listen_host, listen_port))
        server.listen(5)
        server.settimeout(1.0)

        self._add_log_async(f'TCP隧道监听中: {listen_host}:{listen_port}', 'info')

        while self._running:
            try:
                client, addr = server.accept()
                self._add_log_async(f'新连接: {addr[0]}:{addr[1]}', 'info')

                # 为每个连接创建转发线程
                thread = threading.Thread(
                    target=self._forward_tcp,
                    args=(client, target_type, target_host, target_port),
                    daemon=True
                )
                thread.start()
                self._threads.append(thread)
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    self._add_log_async(f'接受连接错误: {e}', 'error')

        server.close()

    def _forward_tcp(self, client_sock, target_type, target_host, target_port):
        """转发TCP数据"""
        try:
            if target_type == 'TCP':
                target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                target.connect((target_host, target_port))
            else:
                target = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            client_sock.settimeout(1.0)
            target.settimeout(1.0)

            while self._running:
                r, _, _ = select.select([client_sock, target], [], [], 1.0)
                for sock in r:
                    data = sock.recv(4096)
                    if not data:
                        raise ConnectionError('连接关闭')
                    
                    # 单向转发模式：检查过滤规则
                    if self.mode_var.get() == '单向转发':
                        direction = 'TX' if sock is client_sock else 'RX'
                        if not self._check_filter(data, direction):
                            continue
                    
                    if sock is client_sock:
                        target.send(data)
                        self._tx_bytes += len(data)
                        self._add_log_async(f'→ {len(data)}字节', 'data')
                    else:
                        client_sock.send(data)
                        self._rx_bytes += len(data)
                        self._add_log_async(f'← {len(data)}字节', 'data')
                    self.start_btn.after(0, self._update_traffic)

        except Exception as e:
            self._add_log_async(f'转发结束: {e}', 'info')
        finally:
            try:
                client_sock.close()
            except Exception:
                pass
            try:
                target.close()
            except Exception:
                pass

    def _run_udp_tunnel(self, listen_host, listen_port,
                        target_type, target_host, target_port):
        """运行UDP隧道"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((listen_host, listen_port))
        sock.settimeout(1.0)

        self._add_log_async(f'UDP隧道监听中: {listen_host}:{listen_port}', 'info')

        while self._running:
            try:
                data, addr = sock.recvfrom(4096)
                
                # 单向转发模式：检查过滤规则
                if self.mode_var.get() == '单向转发':
                    if not self._check_filter(data, 'RX'):
                        continue
                
                self._add_log_async(f'收到 {len(data)}字节 来自 {addr[0]}:{addr[1]}', 'data')

                if target_type == 'TCP':
                    target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        target.connect((target_host, target_port))
                        target.send(data)
                        self._tx_bytes += len(data)
                        self._add_log_async(f'→TCP {len(data)}字节', 'data')
                    finally:
                        target.close()
                else:
                    target = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    target.sendto(data, (target_host, target_port))
                    self._tx_bytes += len(data)
                    self._add_log_async(f'→UDP {len(data)}字节', 'data')
                    target.close()
                self.start_btn.after(0, self._update_traffic)

            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    self._add_log_async(f'UDP转发错误: {e}', 'error')

        sock.close()

    def _check_filter(self, data: bytes, direction: str) -> bool:
        """检查过滤规则"""
        rule = self.rule_var.get()
        if rule == '仅转发TX' and direction != 'TX':
            return False
        if rule == '仅转发RX' and direction != 'RX':
            return False
        if rule == '自定义过滤':
            filter_hex = self.filter_var.get().strip()
            if filter_hex:
                try:
                    filter_bytes = bytes.fromhex(filter_hex.replace(' ', ''))
                    if filter_bytes not in data:
                        return False
                except Exception:
                    pass
        return True

    def _add_log_async(self, text: str, tag: str = ''):
        """异步添加日志"""
        try:
            self.log_text.after(0, lambda: self._add_log(text, tag))
        except Exception:
            pass

    def _add_log(self, text: str, tag: str = ''):
        """添加日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f'[{timestamp}] {text}\n', tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _stop_tunnel_async(self):
        """异步停止隧道"""
        try:
            self.start_btn.after(0, self._stop_tunnel)
        except Exception:
            pass

    def _stop_tunnel(self):
        """停止隧道"""
        self._running = False
        self.start_btn.configure(text='▶ 启动')
        self.status_var.set('已停止')
        self._add_log('⏹ 隧道已停止', 'info')
        StatusBus.send('隧道', '已停止', 'info')

    def _test_target(self):
        """测试目标地址是否可达"""
        target_host = self.target_host_var.get().strip()
        try:
            target_port = int(self.target_port_var.get())
        except ValueError:
            messagebox.showerror('错误', '目标端口格式错误', parent=self)
            return

        if not target_host:
            messagebox.showerror('错误', '请输入目标地址', parent=self)
            return

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((target_host, target_port))
            sock.close()
            self._add_log(f'✅ 目标 {target_host}:{target_port} 可达', 'info')
            StatusBus.send('隧道', f'目标 {target_host}:{target_port} 可达', 'success')
        except Exception as e:
            self._add_log(f'❌ 目标 {target_host}:{target_port} 不可达: {e}', 'error')
            StatusBus.send('隧道', f'目标不可达', 'warning')

    def _clear_log(self):
        """清空转发日志"""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)
        self._tx_bytes = 0
        self._rx_bytes = 0
        self._traffic_label.configure(text='TX: 0  RX: 0')

    def destroy(self):
        self._running = False
        super().destroy()

    def get_settings(self) -> dict:
        return {
            'mode': self.mode_var.get(),
            'listen_type': self.listen_type_var.get(),
            'listen_host': self.listen_host_var.get(),
            'listen_port': self.listen_port_var.get(),
            'target_type': self.target_type_var.get(),
            'target_host': self.target_host_var.get(),
            'target_port': self.target_port_var.get(),
            'rule': self.rule_var.get(),
            'filter': self.filter_var.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        if 'mode' in settings:
            self.mode_var.set(settings['mode'])
            self._on_mode_change()
        if 'listen_type' in settings:
            self.listen_type_var.set(settings['listen_type'])
        if 'listen_host' in settings:
            self.listen_host_var.set(settings['listen_host'])
        if 'listen_port' in settings:
            self.listen_port_var.set(settings['listen_port'])
        if 'target_type' in settings:
            self.target_type_var.set(settings['target_type'])
        if 'target_host' in settings:
            self.target_host_var.set(settings['target_host'])
        if 'target_port' in settings:
            self.target_port_var.set(settings['target_port'])
        if 'rule' in settings:
            self.rule_var.set(settings['rule'])
        if 'filter' in settings:
            self.filter_var.set(settings['filter'])
