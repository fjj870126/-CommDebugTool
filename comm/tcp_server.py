"""TCP服务端通信模块 - 支持多实例（多端口监听）"""
import socket
import threading


class ClientInfo:
    """客户端信息"""
    def __init__(self, sock: socket.socket, addr: tuple):
        self.sock = sock
        self.addr = addr  # (host, port)

    @property
    def key(self) -> str:
        return f'{self.addr[0]}:{self.addr[1]}'

    def __repr__(self):
        return self.key


class ServerInstance:
    """单个服务端实例"""
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server_sock: socket.socket = None
        self.clients: dict[str, ClientInfo] = {}
        self._clients_lock = threading.Lock()
        self._running = False
        self._accept_thread: threading.Thread = None
        self._on_receive = None
        self._on_client_connect = None
        self._on_client_disconnect = None

    @property
    def key(self) -> str:
        return f'{self.host}:{self.port}'

    @property
    def listening(self) -> bool:
        return self._running

    def start(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(5)
        self._running = True
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

    def stop(self):
        self._running = False
        with self._clients_lock:
            for ci in list(self.clients.values()):
                try:
                    ci.sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    ci.sock.close()
                except OSError:
                    pass
            self.clients.clear()
        srv = self.server_sock
        self.server_sock = None
        if srv:
            try:
                srv.close()
            except OSError:
                pass

    def send(self, data: bytes, client_key: str = None):
        with self._clients_lock:
            if client_key:
                ci = self.clients.get(client_key)
                if ci:
                    try:
                        ci.sock.sendall(data)
                    except OSError:
                        pass
            else:
                for ci in list(self.clients.values()):
                    try:
                        ci.sock.sendall(data)
                    except OSError:
                        pass

    def _accept_loop(self):
        while self._running:
            try:
                self.server_sock.settimeout(1.0)
                client_sock, addr = self.server_sock.accept()
                ci = ClientInfo(client_sock, addr)
                with self._clients_lock:
                    self.clients[ci.key] = ci
                if self._on_client_connect:
                    self._on_client_connect(self.key, ci.key, addr)
                t = threading.Thread(target=self._recv_loop, args=(ci,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _recv_loop(self, ci: ClientInfo):
        while self._running:
            try:
                data = ci.sock.recv(4096)
                if not data:
                    break
                if self._on_receive:
                    self._on_receive(data, self.key, ci.key)
            except OSError:
                break
        with self._clients_lock:
            self.clients.pop(ci.key, None)
        try:
            ci.sock.close()
        except OSError:
            pass
        if self._on_client_disconnect:
            self._on_client_disconnect(self.key, ci.key)


class TcpServer:
    """TCP服务端管理器 - 支持多实例"""

    def __init__(self):
        self._instances: dict[str, ServerInstance] = {}
        self._on_receive = None
        self._on_client_connect = None
        self._on_client_disconnect = None

    @property
    def connected(self) -> bool:
        return any(inst.listening for inst in self._instances.values())

    @property
    def listening(self) -> bool:
        return self.connected

    def get_instance_keys(self) -> list[str]:
        return list(self._instances.keys())

    def get_client_list(self, instance_key: str = None) -> list[str]:
        if instance_key:
            inst = self._instances.get(instance_key)
            if inst:
                with inst._clients_lock:
                    return list(inst.clients.keys())
            return []
        result = []
        for inst in self._instances.values():
            with inst._clients_lock:
                result.extend(inst.clients.keys())
        return result

    def start(self, host: str, port: int):
        key = f'{host}:{port}'
        if key in self._instances:
            return
        inst = ServerInstance(host, port)
        inst._on_receive = self._on_receive
        inst._on_client_connect = self._on_client_connect
        inst._on_client_disconnect = self._on_client_disconnect
        inst.start()
        self._instances[key] = inst

    def stop(self, instance_key: str = None):
        if instance_key:
            inst = self._instances.pop(instance_key, None)
            if inst:
                inst.stop()
        else:
            for inst in list(self._instances.values()):
                inst.stop()
            self._instances.clear()

    def send(self, data: bytes, client_key: str = None, instance_key: str = None):
        if instance_key:
            inst = self._instances.get(instance_key)
            if inst:
                inst.send(data, client_key=client_key)
        else:
            for inst in self._instances.values():
                inst.send(data, client_key=client_key)

    def get_client_count(self, instance_key: str = None) -> int:
        if instance_key:
            inst = self._instances.get(instance_key)
            if inst:
                with inst._clients_lock:
                    return len(inst.clients)
            return 0
        total = 0
        for inst in self._instances.values():
            with inst._clients_lock:
                total += len(inst.clients)
        return total

    def set_on_receive(self, callback):
        self._on_receive = callback

    def set_on_client_connect(self, callback):
        self._on_client_connect = callback

    def set_on_client_disconnect(self, callback):
        self._on_client_disconnect = callback
