"""校验和计算器 - 支持多种校验算法"""

import tkinter as tk
from tkinter import ttk, messagebox
import hashlib
import struct
from ui.theme import get_theme


class ChecksumPanel(ttk.LabelFrame):
    """校验和计算器"""

    def __init__(self, parent):
        super().__init__(parent, text=' 校验和计算器 ', padding=8)
        self._build_ui()

    def _build_ui(self):
        # 输入
        row1 = ttk.Frame(self)
        row1.pack(fill=tk.X, pady=(0, 4))
        
        ttk.Label(row1, text='输入数据(Hex):').pack(side=tk.LEFT)
        self.input_var = tk.StringVar(value='01 02 03 04')
        self.input_entry = ttk.Entry(row1, textvariable=self.input_var, width=30)
        self.input_entry.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)

        # 算法选择
        row2 = ttk.Frame(self)
        row2.pack(fill=tk.X, pady=(0, 4))
        
        ttk.Label(row2, text='算法:').pack(side=tk.LEFT)
        self.algorithm_var = tk.StringVar(value='CRC16-Modbus')
        self.algorithm_cb = ttk.Combobox(row2, textvariable=self.algorithm_var,
                                         values=[
                                             'CRC8', 'CRC16-Modbus', 'CRC16-CCITT',
                                             'CRC32', 'MD5', 'SHA1', 'SHA256',
                                             'XOR校验', '累加和', '异或累加',
                                         ],
                                         state='readonly', width=18)
        self.algorithm_cb.pack(side=tk.LEFT, padx=(4, 0))
        
        ttk.Button(row2, text='计算', command=self._calculate, width=8).pack(side=tk.LEFT, padx=(8, 0))

        # 结果
        row3 = ttk.Frame(self)
        row3.pack(fill=tk.X, pady=(0, 4))
        
        ttk.Label(row3, text='结果:').pack(side=tk.LEFT)
        self.result_var = tk.StringVar(value='')
        self.result_entry = ttk.Entry(row3, textvariable=self.result_var,
                                      font=('Courier New', 11), width=30)
        self.result_entry.pack(side=tk.LEFT, padx=(4, 0), fill=tk.X, expand=True)
        
        ttk.Button(row3, text='复制', command=self._copy_result, width=6).pack(side=tk.RIGHT)
        ttk.Button(row3, text='插入', command=self._insert_result, width=6).pack(side=tk.RIGHT, padx=(4, 0))

        # 详细结果
        detail_frame = ttk.LabelFrame(self, text=' 详细结果 ', padding=4)
        detail_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        
        self.detail_text = tk.Text(detail_frame, height=6, state=tk.DISABLED)
        get_theme().configure_text_widget(self.detail_text, 'monospace')
        detail_scroll = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=detail_scroll.set)
        self.detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _get_data(self) -> bytes:
        """获取输入数据"""
        hex_str = self.input_var.get().strip()
        if not hex_str:
            return b''
        try:
            return bytes.fromhex(hex_str.replace(' ', ''))
        except ValueError:
            messagebox.showerror('错误', '无效的 Hex 数据')
            return None

    def _calculate(self):
        """计算校验和"""
        data = self._get_data()
        if data is None:
            return
        if not data:
            messagebox.showwarning('提示', '请输入数据')
            return
        
        algorithm = self.algorithm_var.get()
        
        try:
            if algorithm == 'CRC8':
                result = self._calc_crc8(data)
                self._show_result(result, 'CRC8', '1 byte')
            elif algorithm == 'CRC16-Modbus':
                result = self._calc_crc16_modbus(data)
                self._show_result(result, 'CRC16-Modbus', '2 bytes')
            elif algorithm == 'CRC16-CCITT':
                result = self._calc_crc16_ccitt(data)
                self._show_result(result, 'CRC16-CCITT', '2 bytes')
            elif algorithm == 'CRC32':
                result = self._calc_crc32(data)
                self._show_result(result, 'CRC32', '4 bytes')
            elif algorithm == 'MD5':
                result = hashlib.md5(data).hexdigest().upper()
                self._show_result(result, 'MD5', '16 bytes')
            elif algorithm == 'SHA1':
                result = hashlib.sha1(data).hexdigest().upper()
                self._show_result(result, 'SHA1', '20 bytes')
            elif algorithm == 'SHA256':
                result = hashlib.sha256(data).hexdigest().upper()
                self._show_result(result, 'SHA256', '32 bytes')
            elif algorithm == 'XOR校验':
                result = self._calc_xor(data)
                self._show_result(result, 'XOR校验', '1 byte')
            elif algorithm == '累加和':
                result = self._calc_sum(data)
                self._show_result(result, '累加和', '1 byte')
            elif algorithm == '异或累加':
                result = self._calc_xor_sum(data)
                self._show_result(result, '异或累加', '1 byte')
        except Exception as e:
            messagebox.showerror('计算失败', str(e))

    def _show_result(self, result, name: str, size: str):
        """显示结果"""
        self.result_var.set(str(result))
        
        self.detail_text.configure(state=tk.NORMAL)
        self.detail_text.delete('1.0', tk.END)
        self.detail_text.insert(tk.END, f'算法: {name}\n')
        self.detail_text.insert(tk.END, f'大小: {size}\n')
        self.detail_text.insert(tk.END, f'结果: {result}\n')
        
        # 显示二进制表示
        if isinstance(result, str) and all(c in '0123456789ABCDEF' for c in result):
            try:
                result_bytes = bytes.fromhex(result)
                self.detail_text.insert(tk.END, f'二进制: {result_bytes}\n')
            except ValueError:
                pass
        
        self.detail_text.configure(state=tk.DISABLED)

    def _calc_crc8(self, data: bytes) -> str:
        """计算 CRC8"""
        crc = 0xFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x07
                else:
                    crc <<= 1
                crc &= 0xFF
        return f'{crc:02X}'

    def _calc_crc16_modbus(self, data: bytes) -> str:
        """计算 CRC16-Modbus"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        # Modbus 是小端输出
        return f'{crc & 0xFF:02X} {(crc >> 8) & 0xFF:02X}'

    def _calc_crc16_ccitt(self, data: bytes) -> str:
        """计算 CRC16-CCITT"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return f'{(crc >> 8) & 0xFF:02X} {crc & 0xFF:02X}'

    def _calc_crc32(self, data: bytes) -> str:
        """计算 CRC32"""
        crc = 0xFFFFFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xEDB88320
                else:
                    crc >>= 1
        crc ^= 0xFFFFFFFF
        # 大端输出
        result = struct.pack('>I', crc)
        return ' '.join(f'{b:02X}' for b in result)

    def _calc_xor(self, data: bytes) -> str:
        """计算 XOR 校验"""
        result = 0
        for byte in data:
            result ^= byte
        return f'{result:02X}'

    def _calc_sum(self, data: bytes) -> str:
        """计算累加和"""
        total = sum(data)
        return f'{total & 0xFF:02X}'

    def _calc_xor_sum(self, data: bytes) -> str:
        """计算异或累加"""
        result = 0
        for byte in data:
            result ^= byte
        result = (~result) & 0xFF
        return f'{result:02X}'

    def _copy_result(self):
        """复制结果"""
        result = self.result_var.get()
        if result:
            self.winfo_toplevel().clipboard_clear()
            self.winfo_toplevel().clipboard_append(result)

    def _insert_result(self):
        """插入结果到发送数据（通过剪贴板）"""
        result = self.result_var.get()
        if result:
            self.winfo_toplevel().clipboard_clear()
            self.winfo_toplevel().clipboard_append(result)

    def get_settings(self) -> dict:
        return {
            'input': self.input_var.get(),
            'algorithm': self.algorithm_var.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        self.input_var.set(settings.get('input', '01 02 03 04'))
        self.algorithm_var.set(settings.get('algorithm', 'CRC16-Modbus'))
