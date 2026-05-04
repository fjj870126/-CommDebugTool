"""WebSocket 通信模块 - 支持 ws:// 和 wss:// 协议"""

import json
import threading
import time
from typing import Callable, Optional

try:
    import websocket
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False


class WebSocketComm:
    """WebSocket 客户端封装，支持连接、发送、接收、自动重连"""

    def __init__(self):
        self._ws: Optional[websocket.WebSocketApp] = None
        self._connected = False
        self._on_receive: Optional[Callable] = None
        self._on_connect: Optional[Callable] = None
        self._on_disconnect: Optional[Callable] = None
        self._url = ''
        self._auto_reconnect = True
        self._reconnect_delay = 5
        self._max_reconnect_retries = 0
        self._reconnect_count = 0
        self._stop_thread = False
        self._thread: Optional[threading.Thread] = None

    # ============================================================
    # 属性
    # ============================================================

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def reconnect_count(self) -> int:
        return self._reconnect_count

    # ============================================================
    # 回调设置
    # ============================================================

    def set_on_receive(self, callback: Callable):
        """设置接收回调 callback(data: bytes)"""
        self._on_receive = callback

    def set_on_connect(self, callback: Callable):
        """设置连接回调"""
        self._on_connect = callback

    def set_on_disconnect(self, callback: Callable):
        """设置断开回调"""
        self._on_disconnect = callback

    # ============================================================
    # 连接/断开
    # ============================================================

    def connect(self, url: str,
                auto_reconnect: bool = True,
                reconnect_delay: int = 5,
                max_reconnect_retries: int = 0):
        """连接到 WebSocket 服务器"""
        if not HAS_WEBSOCKET:
            raise ImportError('请先安装 websocket-client: pip install websocket-client')

        self.disconnect()

        self._url = url
        self._auto_reconnect = auto_reconnect
        self._reconnect_delay = reconnect_delay
        self._max_reconnect_retries = max_reconnect_retries
        self._reconnect_count = 0
        self._stop_thread = False

        # 创建 WebSocketApp
        self._ws = websocket.WebSocketApp(
            url,
            on_open=self._on_ws_open,
            on_message=self._on_ws_message,
            on_error=self._on_ws_error,
            on_close=self._on_ws_close,
        )

        # 在后台线程中运行
        self._thread = threading.Thread(target=self._ws.run_forever, daemon=True)
        self._thread.start()

    def disconnect(self):
        """断开连接"""
        self._stop_thread = True
        self._auto_reconnect = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._connected = False
        self._reconnect_count = 0

    # ============================================================
    # WebSocket 内部回调
    # ============================================================

    def _on_ws_open(self, ws):
        """连接成功"""
        self._connected = True
        self._reconnect_count = 0
        if self._on_connect:
            self._on_connect()

    def _on_ws_message(self, ws, message):
        """收到消息"""
        if self._on_receive:
            if isinstance(message, str):
                self._on_receive(message.encode('utf-8'))
            else:
                self._on_receive(message)

    def _on_ws_error(self, ws, error):
        """连接错误"""
        self._connected = False
        if self._on_disconnect:
            self._on_disconnect(f'错误: {error}')

    def _on_ws_close(self, ws, close_status_code, close_msg):
        """连接关闭"""
        self._connected = False
        reason = f'关闭(code={close_status_code})' if close_status_code else '正常关闭'
        if self._on_disconnect:
            self._on_disconnect(reason)

        # 自动重连
        if not self._stop_thread and self._auto_reconnect:
            if self._max_reconnect_retries == 0 or self._reconnect_count < self._max_reconnect_retries:
                self._reconnect_count += 1
                threading.Timer(self._reconnect_delay, self._try_reconnect).start()

    def _try_reconnect(self):
        """尝试重连"""
        if self._connected or self._stop_thread:
            return
        try:
            self.connect(
                url=self._url,
                auto_reconnect=self._auto_reconnect,
                reconnect_delay=self._reconnect_delay,
                max_reconnect_retries=self._max_reconnect_retries,
            )
        except Exception:
            if not self._stop_thread and self._auto_reconnect:
                if self._max_reconnect_retries == 0 or self._reconnect_count < self._max_reconnect_retries:
                    self._reconnect_count += 1
                    threading.Timer(self._reconnect_delay, self._try_reconnect).start()

    # ============================================================
    # 发送
    # ============================================================

    def send(self, data: bytes) -> bool:
        """发送数据"""
        if not self._connected or not self._ws:
            return False
        try:
            self._ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
            return True
        except Exception:
            return False

    def send_text(self, text: str) -> bool:
        """发送文本"""
        if not self._connected or not self._ws:
            return False
        try:
            self._ws.send(text, opcode=websocket.ABNF.OPCODE_TEXT)
            return True
        except Exception:
            return False
