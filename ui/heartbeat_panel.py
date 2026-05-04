"""心跳自动回复面板 - 支持收到指定心跳数据后自动回复，以及定时主动发送心跳"""

import tkinter as tk
from tkinter import ttk
from utils.hex_utils import hex_str_to_bytes, bytes_to_hex_str, is_valid_hex
from utils.context_menu import add_entry_context_menu


class HexEntry:
    """Hex 输入框辅助类：自动过滤非法字符、格式化显示、发送前补零"""

    def __init__(self, entry: ttk.Entry, var: tk.StringVar):
        self.entry = entry
        self.var = var
        entry.bind('<KeyRelease>', self._on_input_change)

    def _on_input_change(self, event=None):
        """自动过滤非法字符并格式化显示"""
        cursor_pos = self.entry.index(tk.INSERT)
        raw = self.var.get()

        # 过滤掉非 16 进制字符和空格的内容
        cleaned = ''
        for ch in raw:
            if ch in '0123456789abcdefABCDEF':
                cleaned += ch.upper()
            elif ch == ' ':
                cleaned += ' '

        # 去除多余空格，只保留单个空格
        parts = cleaned.split()
        cleaned = ' '.join(parts)

        # 自动添加空格：每两个 16 进制数后加空格
        hex_chars = ''.join([ch for ch in cleaned if ch in '0123456789ABCDEF'])

        formatted = cleaned  # 默认不格式化
        if len(hex_chars) >= 2:
            # 按两个字符一组重新格式化
            formatted_parts = []
            for i in range(0, len(hex_chars), 2):
                formatted_parts.append(hex_chars[i:i+2])

            # 如果原始输入最后一个字节还没输完（奇数个字符），保留最后一个字符但不加空格
            last_incomplete = ''
            if len(hex_chars) % 2 == 1:
                last_incomplete = hex_chars[-1]
                formatted_parts.pop()

            # 只有完整的字节才用空格连接
            if formatted_parts:
                formatted = ' '.join(formatted_parts)
                if last_incomplete:
                    formatted += ' ' + last_incomplete
            else:
                formatted = last_incomplete

        # 如果格式化后的内容与当前不同，则更新
        if formatted != raw:
            self.var.set(formatted)
            # 智能恢复光标位置
            if cursor_pos >= len(raw):
                self.entry.icursor(len(formatted))
            else:
                char_count_before_cursor = sum(1 for ch in raw[:cursor_pos] if ch in '0123456789ABCDEFabcdef')
                new_cursor = char_count_before_cursor + (char_count_before_cursor - 1) // 2
                if cursor_pos < len(raw) and raw[cursor_pos] == ' ':
                    new_cursor += 1
                self.entry.icursor(min(new_cursor, len(formatted)))

    def get_bytes(self) -> bytes:
        """获取字节数据，自动补零"""
        text = self.var.get().strip()
        if not text:
            return b''
        hex_chars = ''.join([ch for ch in text if ch in '0123456789ABCDEFabcdef'])
        if len(hex_chars) % 2 == 1:
            # 奇数个 16 进制字符，在最后一个数字前补零
            last_hex_pos = -1
            for i in range(len(text) - 1, -1, -1):
                if text[i] in '0123456789ABCDEFabcdef':
                    last_hex_pos = i
                    break
            if last_hex_pos >= 0:
                text = text[:last_hex_pos] + '0' + text[last_hex_pos:]
                self.var.set(text)
        return hex_str_to_bytes(text)


class HeartbeatPanel(ttk.LabelFrame):
    """心跳自动回复面板

    功能:
    1. 自动回复: 收到匹配的心跳请求数据后，自动回复指定数据
    2. 定时心跳: 按设定间隔自动发送心跳数据
    """

    def __init__(self, parent, on_send=None):
        super().__init__(parent, text=' 心跳设置 ', padding=8)
        self._on_send = on_send
        self._auto_reply_enabled = False
        self._timer_enabled = False
        self._timer_id = None
        self._build_ui()

    def _build_ui(self):
        # ===== 自动回复区 =====
        reply_frame = ttk.LabelFrame(self, text=' 自动回复 ', padding=6)
        reply_frame.pack(fill=tk.X, pady=(0, 4))

        # 第一行: 启用 + 匹配模式
        row1 = ttk.Frame(reply_frame)
        row1.pack(fill=tk.X, pady=(0, 4))

        self.reply_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row1, text='启用自动回复', variable=self.reply_enabled_var,
                        command=self._on_reply_toggle).pack(side=tk.LEFT)

        ttk.Separator(row1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Label(row1, text='匹配模式:').pack(side=tk.LEFT)
        self.match_mode_var = tk.StringVar(value='完全匹配')
        ttk.Radiobutton(row1, text='完全匹配', variable=self.match_mode_var,
                        value='完全匹配').pack(side=tk.LEFT, padx=(4, 2))
        ttk.Radiobutton(row1, text='包含匹配', variable=self.match_mode_var,
                        value='包含匹配').pack(side=tk.LEFT, padx=2)

        # 第二行: 匹配数据 (心跳请求)
        row2 = ttk.Frame(reply_frame)
        row2.pack(fill=tk.X, pady=2)

        ttk.Label(row2, text='心跳请求(Hex):').pack(side=tk.LEFT)
        self.match_var = tk.StringVar(value='AA 55 00 01 FE')
        self.match_entry = ttk.Entry(row2, textvariable=self.match_var,
                                     font=('Courier New', 10), width=40)
        self.match_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        add_entry_context_menu(self.match_entry)
        self._match_hex = HexEntry(self.match_entry, self.match_var)

        # 第三行: 回复数据
        row3 = ttk.Frame(reply_frame)
        row3.pack(fill=tk.X, pady=2)

        ttk.Label(row3, text='回复数据(Hex):').pack(side=tk.LEFT)
        self.reply_var = tk.StringVar(value='AA 55 80 01 7E')
        self.reply_entry = ttk.Entry(row3, textvariable=self.reply_var,
                                     font=('Courier New', 10), width=40)
        self.reply_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        add_entry_context_menu(self.reply_entry)
        self._reply_hex = HexEntry(self.reply_entry, self.reply_var)

        # ===== 定时心跳区 =====
        timer_frame = ttk.LabelFrame(self, text=' 定时心跳 ', padding=6)
        timer_frame.pack(fill=tk.X)

        row4 = ttk.Frame(timer_frame)
        row4.pack(fill=tk.X, pady=(0, 4))

        self.timer_enabled_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row4, text='启用定时发送', variable=self.timer_enabled_var,
                        command=self._on_timer_toggle).pack(side=tk.LEFT)

        ttk.Separator(row4, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Label(row4, text='间隔(ms):').pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value='3000')
        self.interval_entry = ttk.Entry(row4, textvariable=self.interval_var, width=8)
        self.interval_entry.pack(side=tk.LEFT, padx=(4, 12))
        add_entry_context_menu(self.interval_entry)

        self.timer_status_var = tk.StringVar(value='已停止')
        self.timer_status_label = ttk.Label(row4, textvariable=self.timer_status_var,
                                            foreground='gray')
        self.timer_status_label.pack(side=tk.LEFT)

        # 定时发送的数据
        row5 = ttk.Frame(timer_frame)
        row5.pack(fill=tk.X, pady=2)

        ttk.Label(row5, text='心跳数据(Hex):').pack(side=tk.LEFT)
        self.heartbeat_var = tk.StringVar(value='AA 55 00 01 FE')
        self.heartbeat_entry = ttk.Entry(row5, textvariable=self.heartbeat_var,
                                         font=('Courier New', 10), width=40)
        self.heartbeat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        add_entry_context_menu(self.heartbeat_entry)
        self._heartbeat_hex = HexEntry(self.heartbeat_entry, self.heartbeat_var)

    def _on_reply_toggle(self):
        self._auto_reply_enabled = self.reply_enabled_var.get()

    def _on_timer_toggle(self):
        if self.timer_enabled_var.get():
            self._start_timer()
        else:
            self._stop_timer()

    def _start_timer(self):
        try:
            interval = int(self.interval_var.get())
        except ValueError:
            interval = 3000
        interval = max(100, interval)

        self._timer_enabled = True
        self.timer_status_var.set('运行中')
        self.timer_status_label.configure(foreground='green')

        def _tick():
            if self._timer_enabled:
                self._send_heartbeat()
                self._timer_id = self.after(interval, _tick)

        # 立即发一次，然后定时
        self._send_heartbeat()
        self._timer_id = self.after(interval, _tick)

    def _stop_timer(self):
        self._timer_enabled = False
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None
        self.timer_status_var.set('已停止')
        self.timer_status_label.configure(foreground='gray')

    def _send_heartbeat(self):
        """发送定时心跳数据"""
        if not self._on_send:
            return
        data = self._heartbeat_hex.get_bytes()
        if not data:
            return
        self._on_send(data, is_heartbeat=True)

    def check_and_reply(self, received_data: bytes) -> bool:
        """检查接收数据是否匹配心跳请求，如匹配则自动回复
        返回: True 表示已匹配并回复
        """
        if not self._auto_reply_enabled:
            return False

        match_bytes = self._match_hex.get_bytes()
        if not match_bytes:
            return False

        # 匹配判断
        mode = self.match_mode_var.get()
        matched = False
        if mode == '完全匹配':
            matched = (received_data == match_bytes)
        elif mode == '包含匹配':
            matched = (match_bytes in received_data)

        if not matched:
            return False

        # 发送回复
        reply_data = self._reply_hex.get_bytes()
        if not reply_data:
            return False

        if self._on_send:
            self._on_send(reply_data, is_heartbeat=True)
        return True

    def stop(self):
        """停止所有定时任务"""
        self._stop_timer()
        self._auto_reply_enabled = False
        self.reply_enabled_var.set(False)
        self.timer_enabled_var.set(False)

    def destroy(self):
        self._stop_timer()
        super().destroy()

    def get_settings(self) -> dict:
        return {
            'reply_enabled': self.reply_enabled_var.get(),
            'match_hex': self.match_var.get(),
            'reply_hex': self.reply_var.get(),
            'match_mode': self.match_mode_var.get(),
            'heartbeat_hex': self.heartbeat_var.get(),
            'interval': self.interval_var.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        self.match_var.set(settings.get('match_hex', 'AA 55 00 01 FE'))
        self.reply_var.set(settings.get('reply_hex', 'AA 55 80 01 7E'))
        self.match_mode_var.set(settings.get('match_mode', '完全匹配'))
        self.heartbeat_var.set(settings.get('heartbeat_hex', 'AA 55 00 01 FE'))
        self.interval_var.set(settings.get('interval', '3000'))
        # 恢复自动回复启用状态
        enabled = settings.get('reply_enabled', False)
        self.reply_enabled_var.set(enabled)
        self._auto_reply_enabled = enabled
