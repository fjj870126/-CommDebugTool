"""UDP通信模块"""

import socket
import threading


class UdpComm:
    def __init__(self):
        self.sock: socket.socket = None
        self._running = False
        self._recv_thread: threading.Thread = None
        self._on_receive = None
        self._target_addr = None  # (host, port) 发送目标
        self._local_addr = None

    @property
    def connected(self) -> bool:
        return self._running and self.sock is not None

    def open(self, local_host: str = '0.0.0.0', local_port: int = 0,
             target_host: str = '127.0.0.1', target_port: int = 8080):
        """打开UDP socket
        local_port=0 表示系统自动分配端口
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((local_host, local_port))
        self._local_addr = self.sock.getsockname()
        self._target_addr = (target_host, target_port)
        self._running = True
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()

    def close(self):
        self._running = False
        if self.sock:
            self.sock.close()
            self.sock = None

    def send(self, data: bytes, target_addr: tuple = None):
        if self.sock and self._running:
            addr = target_addr or self._target_addr
            if addr:
                self.sock.sendto(data, addr)

    def set_target(self, host: str, port: int):
        self._target_addr = (host, port)

    def set_on_receive(self, callback):
        """callback(data: bytes, addr: tuple)"""
        self._on_receive = callback

    def _recv_loop(self):
        while self._running:
            try:
                self.sock.settimeout(1.0)
                data, addr = self.sock.recvfrom(4096)
                if self._on_receive:
                    self._on_receive(data, addr)
            except socket.timeout:
                continue
            except OSError:
                break
