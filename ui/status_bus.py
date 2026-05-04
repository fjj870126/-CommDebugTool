"""全局状态总线 - 各面板向主窗口状态栏发送状态"""


class StatusBus:
    """全局状态总线，各面板通过 send() 发送状态更新，
    主窗口通过 register() 注册回调接收。"""

    _listeners = []

    @classmethod
    def register(cls, callback):
        if callback not in cls._listeners:
            cls._listeners.append(callback)

    @classmethod
    def unregister(cls, callback):
        if callback in cls._listeners:
            cls._listeners.remove(callback)

    @classmethod
    def send(cls, source: str, status: str, level: str = 'info'):
        """发送状态更新

        Args:
            source: 来源面板名称，如 '压力测试', '隧道'
            status: 状态文本，如 '运行中', '已停止', '发送100条'
            level: 级别，info / warning / error / success
        """
        for cb in cls._listeners:
            try:
                cb(source, status, level)
            except Exception:
                pass

    @classmethod
    def clear_listeners(cls):
        cls._listeners.clear()
