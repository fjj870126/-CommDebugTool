"""TCP客户端通信模块"""

import socket
import threading
import queue


class TcpClient:
    def __init__(self):
        self.sock: socket.socket = None
        self._running = False
        self._recv_thread: threading.Thread = None
        self._recv_queue = queue.Queue()
        self._on_receive = None
        self._on_disconnect = None
        self._on_connect_done = None

    @property
    def connected(self) -> bool:
        return self._running and self.sock is not None

    def connect(self, host: str, port: int, timeout: float = 5.0):
        if self.connected:
            return
        if self.sock is not None:
            self.disconnect()
        threading.Thread(target=self._do_connect,
                         args=(host, port, timeout), daemon=True).start()

    def _do_connect(self, host: str, port: int, timeout: float):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.settimeout(None)
            self.sock = sock
            self._running = True
            self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            self._recv_thread.start()
            if self._on_connect_done:
                self._on_connect_done(True, None)
        except Exception as e:
            self._running = False
            self.sock = None
            if self._on_connect_done:
                self._on_connect_done(False, str(e))

    def set_on_connect_done(self, callback):
        """callback(success: bool, error: str)"""
        self._on_connect_done = callback

    def disconnect(self):
        self._running = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.sock.close()
            self.sock = None

    def send(self, data: bytes):
        if self.sock and self._running:
            self.sock.sendall(data)

    def set_on_receive(self, callback):
        """callback(data: bytes)"""
        self._on_receive = callback

    def set_on_disconnect(self, callback):
        """callback()"""
        self._on_disconnect = callback

    def _recv_loop(self):
        while self._running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                if self._on_receive:
                    self._on_receive(data)
            except OSError:
                break
        self._running = False
        if self._on_disconnect:
            self._on_disconnect()
