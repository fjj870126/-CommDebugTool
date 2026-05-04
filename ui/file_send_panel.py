"""文件发送面板 - 选择文件作为二进制数据发送，支持大文件分片"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time


class FileSendPanel(ttk.LabelFrame):
    """文件发送面板"""

    def __init__(self, parent, on_send=None):
        super().__init__(parent, text=' 文件发送 ', padding=8)
        self._on_send = on_send
        self._file_path = None
        self._file_size = 0
        self._sending = False
        self._stop_flag = False
        self._build_ui()

    def _build_ui(self):
        # 文件选择
        row1 = ttk.Frame(self)
        row1.pack(fill=tk.X, pady=(0, 4))
        
        ttk.Label(row1, text='文件:').pack(side=tk.LEFT)
        self.file_path_var = tk.StringVar(value='未选择文件')
        self.file_path_label = ttk.Label(row1, textvariable=self.file_path_var,
                                         foreground='gray', width=30)
        self.file_path_label.pack(side=tk.LEFT, padx=(4, 4), fill=tk.X, expand=True)
        ttk.Button(row1, text='浏览...', command=self._browse_file, width=8).pack(side=tk.RIGHT)

        # 文件信息
        row2 = ttk.Frame(self)
        row2.pack(fill=tk.X, pady=(0, 4))
        
        ttk.Label(row2, text='大小:').pack(side=tk.LEFT)
        self.file_size_var = tk.StringVar(value='-')
        ttk.Label(row2, textvariable=self.file_size_var).pack(side=tk.LEFT, padx=(2, 10))
        
        ttk.Label(row2, text='分片大小:').pack(side=tk.LEFT)
        self.chunk_size_var = tk.StringVar(value='1024')
        self.chunk_size_cb = ttk.Combobox(row2, textvariable=self.chunk_size_var,
                                          values=['256', '512', '1024', '2048', '4096', '8192'],
                                          state='readonly', width=8)
        self.chunk_size_cb.pack(side=tk.LEFT, padx=(2, 10))
        
        ttk.Label(row2, text='间隔(ms):').pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value='50')
        ttk.Spinbox(row2, from_=0, to=1000, textvariable=self.interval_var,
                    width=6).pack(side=tk.LEFT, padx=(2, 0))

        # 发送选项
        row3 = ttk.Frame(self)
        row3.pack(fill=tk.X, pady=(0, 4))
        
        self.add_header_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text='添加长度头(4字节)', variable=self.add_header_var).pack(side=tk.LEFT, padx=(0, 10))
        
        self.add_crc_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text='添加CRC16校验', variable=self.add_crc_var).pack(side=tk.LEFT)

        # 控制按钮
        row4 = ttk.Frame(self)
        row4.pack(fill=tk.X, pady=(0, 4))
        
        self.send_btn = ttk.Button(row4, text='📤 发送文件', command=self._send_file, width=12)
        self.send_btn.pack(side=tk.LEFT, padx=(0, 4))
        
        self.stop_btn = ttk.Button(row4, text='■ 停止', command=self._stop_send,
                                   state=tk.DISABLED, width=8)
        self.stop_btn.pack(side=tk.LEFT)

        # 进度条
        self.progress = ttk.Progressbar(self, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(0, 4))

        # 状态信息
        self.status_var = tk.StringVar(value='就绪')
        ttk.Label(self, textvariable=self.status_var, foreground='gray').pack(anchor=tk.W)

    def _browse_file(self):
        """浏览选择文件"""
        file_path = filedialog.askopenfilename(title='选择要发送的文件')
        if file_path:
            self._file_path = file_path
            self._file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            self.file_path_var.set(file_name)
            self.file_size_var.set(self._format_size(self._file_size))
            self.progress['value'] = 0
            self.status_var.set(f'已选择: {file_name}')

    def _format_size(self, n: int) -> str:
        if n < 1024:
            return f'{n} B'
        elif n < 1024 * 1024:
            return f'{n / 1024:.1f} KB'
        else:
            return f'{n / 1024 / 1024:.1f} MB'

    def _send_file(self):
        """发送文件"""
        if not self._file_path:
            messagebox.showwarning('提示', '请先选择文件')
            return
        
        if not self._on_send:
            messagebox.showwarning('提示', '请先连接设备')
            return
        
        try:
            chunk_size = int(self.chunk_size_var.get())
            interval = int(self.interval_var.get())
        except ValueError:
            messagebox.showerror('错误', '参数格式错误')
            return
        
        self._sending = True
        self._stop_flag = False
        self.send_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        
        total_chunks = (self._file_size + chunk_size - 1) // chunk_size
        self.progress['maximum'] = total_chunks
        self.progress['value'] = 0
        
        # 在后台线程中发送
        thread = threading.Thread(
            target=self._send_worker,
            args=(chunk_size, interval, total_chunks),
            daemon=True
        )
        thread.start()

    def _send_worker(self, chunk_size: int, interval: int, total_chunks: int):
        """文件发送工作线程"""
        try:
            with open(self._file_path, 'rb') as f:
                chunk_index = 0
                while True:
                    if self._stop_flag:
                        break
                    
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    # 构建发送数据
                    data = chunk
                    if self.add_header_var.get():
                        # 添加4字节长度头（小端）
                        length = len(chunk)
                        data = length.to_bytes(4, 'little') + chunk
                    
                    if self.add_crc_var.get():
                        # 添加CRC16校验
                        crc = self._calc_crc16(chunk)
                        data = data + crc.to_bytes(2, 'little')
                    
                    # 发送
                    try:
                        self._on_send(data)
                    except Exception:
                        pass
                    
                    chunk_index += 1
                    
                    # 更新进度
                    self.winfo_toplevel().after(0, lambda: self.progress.step(1))
                    self.winfo_toplevel().after(0, lambda i=chunk_index, t=total_chunks: self.status_var.set(
                        f'发送中: {i}/{t} 分片'))
                    
                    # 间隔
                    if interval > 0:
                        time.sleep(interval / 1000.0)
            
            if not self._stop_flag:
                self.winfo_toplevel().after(0, self._on_send_complete)
        except Exception as e:
            self.winfo_toplevel().after(0, lambda: self.status_var.set(f'发送失败: {e}'))
        finally:
            self._sending = False
            self.winfo_toplevel().after(0, lambda: self.send_btn.configure(state=tk.NORMAL))
            self.winfo_toplevel().after(0, lambda: self.stop_btn.configure(state=tk.DISABLED))

    def _calc_crc16(self, data: bytes) -> int:
        """计算 CRC16"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def _on_send_complete(self):
        """发送完成"""
        self.status_var.set('✅ 文件发送完成')
        self.progress['value'] = self.progress['maximum']

    def _stop_send(self):
        """停止发送"""
        self._stop_flag = True
        self.stop_btn.configure(state=tk.DISABLED)
        self.status_var.set('⏹ 已停止发送')

    def get_settings(self) -> dict:
        return {
            'chunk_size': self.chunk_size_var.get(),
            'interval': self.interval_var.get(),
            'add_header': self.add_header_var.get(),
            'add_crc': self.add_crc_var.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        self.chunk_size_var.set(settings.get('chunk_size', '1024'))
        self.interval_var.set(settings.get('interval', '50'))
        self.add_header_var.set(settings.get('add_header', False))
        self.add_crc_var.set(settings.get('add_crc', False))
