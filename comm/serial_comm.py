"""串口通信模块"""

import threading

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class SerialComm:
    def __init__(self):
        self.ser = None
        self._running = False
        self._recv_thread: threading.Thread = None
        self._on_receive = None
        self._on_disconnect = None

    @property
    def connected(self) -> bool:
        return self._running and self.ser is not None and self.ser.is_open

    @staticmethod
    def list_ports() -> list:
        """列出所有可用串口"""
        if not SERIAL_AVAILABLE:
            return []
        ports = serial.tools.list_ports.comports()
        return [(p.device, p.description) for p in ports]

    def connect(self, port: str, baudrate: int = 115200,
                bytesize: int = 8, parity: str = 'N', stopbits: float = 1,
                timeout: float = None):
        if self.connected:
            return
        if not SERIAL_AVAILABLE:
            raise ImportError("pyserial 未安装，请运行: pip install pyserial")

        parity_map = {
            'N': serial.PARITY_NONE,
            'E': serial.PARITY_EVEN,
            'O': serial.PARITY_ODD,
        }
        stopbits_map = {
            1: serial.STOPBITS_ONE,
            1.5: serial.STOPBITS_ONE_POINT_FIVE,
            2: serial.STOPBITS_TWO,
        }

        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=bytesize,
            parity=parity_map.get(parity, serial.PARITY_NONE),
            stopbits=stopbits_map.get(stopbits, serial.STOPBITS_ONE),
            timeout=1,
        )
        self._running = True
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()

    def disconnect(self):
        self._running = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.ser = None

    def send(self, data: bytes):
        if self.ser and self.ser.is_open:
            self.ser.write(data)

    def set_on_receive(self, callback):
        """callback(data: bytes)"""
        self._on_receive = callback

    def set_on_disconnect(self, callback):
        self._on_disconnect = callback

    def _recv_loop(self):
        while self._running:
            try:
                if self.ser and self.ser.is_open and self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting)
                    if data and self._on_receive:
                        self._on_receive(data)
                else:
                    threading.Event().wait(0.01)
            except OSError:
                break
        if self._on_disconnect:
            self._on_disconnect()
