"""MQTT 通信模块 - 基于 paho-mqtt 实现发布/订阅功能"""

import json
import threading
import time
from typing import Callable, Optional

try:
    import paho.mqtt.client as mqtt
    HAS_PAHO = True
except ImportError:
    HAS_PAHO = False


class MqttComm:
    """MQTT 客户端封装，支持连接、发布、订阅、遗嘱消息、自动重连"""

    def __init__(self):
        self._client: Optional[mqtt.Client] = None
        self._connected = False
        self._on_receive: Optional[Callable] = None
        self._on_connect: Optional[Callable] = None
        self._on_disconnect: Optional[Callable] = None
        self._subscriptions: dict = {}  # topic -> qos
        self._broker_host = ''
        self._broker_port = 1883
        self._client_id = ''
        self._username = ''
        self._password = ''
        self._use_tls = False
        self._auto_reconnect = True
        self._reconnect_delay = 5  # 重连间隔（秒）
        self._max_reconnect_retries = 0  # 0=无限重试
        self._reconnect_count = 0
        self._lock = threading.Lock()

    # ============================================================
    # 属性
    # ============================================================

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def subscriptions(self) -> dict:
        return dict(self._subscriptions)

    @property
    def reconnect_count(self) -> int:
        return self._reconnect_count

    # ============================================================
    # 回调设置
    # ============================================================

    def set_on_receive(self, callback: Callable):
        """设置接收回调 callback(data: bytes, topic: str)"""
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

    def connect(self, host: str, port: int = 1883, client_id: str = '',
                username: str = '', password: str = '',
                use_tls: bool = False,
                ca_cert: str = '', client_cert: str = '', client_key: str = '',
                keepalive: int = 60,
                clean_session: bool = True,
                will_topic: str = '', will_payload: str = '',
                will_qos: int = 0, will_retain: bool = False,
                auto_reconnect: bool = True,
                reconnect_delay: int = 5,
                max_reconnect_retries: int = 0):
        """连接到 MQTT Broker"""
        if not HAS_PAHO:
            raise ImportError('请先安装 paho-mqtt: pip install paho-mqtt')

        self.disconnect()

        self._broker_host = host
        self._broker_port = port
        self._client_id = client_id
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._auto_reconnect = auto_reconnect
        self._reconnect_delay = reconnect_delay
        self._max_reconnect_retries = max_reconnect_retries
        self._reconnect_count = 0

        # 创建客户端
        if client_id:
            self._client = mqtt.Client(client_id=client_id, clean_session=clean_session)
        else:
            self._client = mqtt.Client(clean_session=clean_session)

        # 设置回调
        self._client.on_connect = self._on_mqtt_connect
        self._client.on_disconnect = self._on_mqtt_disconnect
        self._client.on_message = self._on_mqtt_message

        # 用户名/密码
        if username:
            self._client.username_pw_set(username, password)

        # TLS 证书配置
        if use_tls:
            if ca_cert or client_cert or client_key:
                self._client.tls_set(ca_certs=ca_cert if ca_cert else None,
                                     certfile=client_cert if client_cert else None,
                                     keyfile=client_key if client_key else None)
            else:
                self._client.tls_set()

        # 遗嘱消息
        if will_topic:
            self._client.will_set(will_topic, will_payload.encode() if will_payload else b'',
                                  qos=will_qos, retain=will_retain)

        # 连接
        self._client.connect(host, port, keepalive=keepalive)

        # 启动网络循环（后台线程）
        self._client.loop_start()

    def disconnect(self):
        """断开连接（在后台线程中执行，避免阻塞 UI）"""
        client = None
        with self._lock:
            if self._client:
                client = self._client
                self._client = None
            self._connected = False
            self._reconnect_count = 0

        if client:
            def _do_disconnect():
                try:
                    client.loop_stop()
                    client.disconnect()
                except Exception:
                    pass
            threading.Thread(target=_do_disconnect, daemon=True).start()

    # ============================================================
    # MQTT 内部回调
    # ============================================================

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """连接成功/失败回调"""
        if rc == 0:
            self._connected = True
            self._reconnect_count = 0
            # 重新订阅之前的所有主题
            for topic, qos in self._subscriptions.items():
                try:
                    self._client.subscribe(topic, qos)
                except Exception:
                    pass
            if self._on_connect:
                self._on_connect()
        else:
            self._connected = False
            reason_map = {
                1: '协议版本错误',
                2: 'Client ID 被拒',
                3: '服务器不可用',
                4: '用户名或密码错误',
                5: '未授权',
            }
            reason = reason_map.get(rc, f'未知错误({rc})')
            if self._on_disconnect:
                self._on_disconnect(reason)

    def _on_mqtt_disconnect(self, client, userdata, rc):
        """断开回调"""
        self._connected = False
        reason = '正常断开' if rc == 0 else f'异常断开(rc={rc})'
        if self._on_disconnect:
            self._on_disconnect(reason)

        # 自动重连
        if rc != 0 and self._auto_reconnect:
            if self._max_reconnect_retries == 0 or self._reconnect_count < self._max_reconnect_retries:
                self._reconnect_count += 1
                threading.Timer(self._reconnect_delay, self._try_reconnect).start()

    def _try_reconnect(self):
        """尝试重连"""
        if self._connected or not self._client:
            return
        try:
            self._client.reconnect()
        except Exception:
            # 重连失败，继续重试
            if self._auto_reconnect:
                if self._max_reconnect_retries == 0 or self._reconnect_count < self._max_reconnect_retries:
                    self._reconnect_count += 1
                    threading.Timer(self._reconnect_delay, self._try_reconnect).start()

    def _on_mqtt_message(self, client, userdata, msg):
        """收到消息回调"""
        if self._on_receive:
            self._on_receive(msg.payload, msg.topic)

    # ============================================================
    # 发布
    # ============================================================

    def publish(self, topic: str, payload: bytes, qos: int = 0, retain: bool = False) -> bool:
        """发布消息到指定主题"""
        if not self._connected or not self._client:
            return False
        try:
            result = self._client.publish(topic, payload, qos=qos, retain=retain)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception:
            return False

    # ============================================================
    # 订阅/取消订阅
    # ============================================================

    def subscribe(self, topic: str, qos: int = 0) -> bool:
        """订阅主题"""
        if not self._client:
            return False
        try:
            result = self._client.subscribe(topic, qos)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                self._subscriptions[topic] = qos
                return True
            return False
        except Exception:
            return False

    def unsubscribe(self, topic: str) -> bool:
        """取消订阅"""
        if not self._client:
            return False
        try:
            result = self._client.unsubscribe(topic)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                self._subscriptions.pop(topic, None)
                return True
            return False
        except Exception:
            return False

    def get_subscriptions(self) -> list:
        """获取已订阅的主题列表"""
        return list(self._subscriptions.keys())
