"""JSON/XML 格式化面板 - 自动格式化显示接收到的 JSON/XML 数据"""

import json
import re
import xml.dom.minidom as minidom
import tkinter as tk
from tkinter import ttk, messagebox
from ui.theme import get_theme


class FormatterPanel(ttk.LabelFrame):
    """JSON/XML 格式化面板"""

    def __init__(self, parent, log_panel=None):
        super().__init__(parent, text=' JSON/XML 格式化 ', padding=8)
        self._log_panel = log_panel
        self._build_ui()

    def _build_ui(self):
        # 输入区域
        input_frame = ttk.LabelFrame(self, text=' 输入 ', padding=4)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        # 工具栏
        toolbar = ttk.Frame(input_frame)
        toolbar.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(toolbar, text='格式:').pack(side=tk.LEFT)
        self.format_var = tk.StringVar(value='自动检测')
        format_cb = ttk.Combobox(toolbar, textvariable=self.format_var,
                                 values=['自动检测', 'JSON', 'XML'],
                                 state='readonly', width=10)
        format_cb.pack(side=tk.LEFT, padx=(4, 8))

        ttk.Button(toolbar, text='🔄 格式化', command=self._format_data, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text='📋 复制结果', command=self._copy_result, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text='🗑 清空', command=self._clear, width=6).pack(side=tk.RIGHT, padx=2)

        # 输入文本框
        theme = get_theme()
        self.input_text = tk.Text(input_frame, wrap=tk.NONE, height=8)
        theme.configure_text_widget(self.input_text, 'monospace_large')
        input_v_scroll = ttk.Scrollbar(input_frame, orient=tk.VERTICAL, command=self.input_text.yview)
        input_h_scroll = ttk.Scrollbar(input_frame, orient=tk.HORIZONTAL, command=self.input_text.xview)
        self.input_text.configure(yscrollcommand=input_v_scroll.set, xscrollcommand=input_h_scroll.set)

        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        input_v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        input_h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # 输出区域
        output_frame = ttk.LabelFrame(self, text=' 格式化结果 ', padding=4)
        output_frame.pack(fill=tk.BOTH, expand=True)

        self.output_text = tk.Text(output_frame, wrap=tk.NONE, height=12,
                                   state=tk.DISABLED)
        theme.configure_text_widget(self.output_text, 'monospace_large')
        output_v_scroll = ttk.Scrollbar(output_frame, orient=tk.VERTICAL, command=self.output_text.yview)
        output_h_scroll = ttk.Scrollbar(output_frame, orient=tk.HORIZONTAL, command=self.output_text.xview)
        self.output_text.configure(yscrollcommand=output_v_scroll.set, xscrollcommand=output_h_scroll.set)

        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        output_v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        output_h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # 右键菜单
        self._setup_context_menu()

    def _setup_context_menu(self):
        """设置右键菜单"""
        menu = tk.Menu(self.input_text, tearoff=0)
        menu.add_command(label='粘贴', command=lambda: self.input_text.event_generate('<<Paste>>'))
        menu.add_command(label='清空', command=self._clear)
        self.input_text.bind('<Button-3>', lambda e: menu.tk_popup(e.x_root, e.y_root))
        self.input_text.bind('<Control-Button-1>', lambda e: menu.tk_popup(e.x_root, e.y_root))

    def _detect_format(self, text: str) -> str:
        """自动检测数据格式"""
        text = text.strip()
        if not text:
            return 'unknown'
        
        # 检测 JSON
        if text.startswith('{') or text.startswith('['):
            try:
                json.loads(text)
                return 'json'
            except json.JSONDecodeError:
                pass
        
        # 检测 XML
        if text.startswith('<') and text.endswith('>'):
            if re.match(r'<\?xml|<[a-zA-Z]', text):
                try:
                    minidom.parseString(text)
                    return 'xml'
                except Exception:
                    pass
        
        # 检测 Hex 字符串中的 JSON/XML
        try:
            decoded = bytes.fromhex(text.replace(' ', '')).decode('utf-8', errors='ignore')
            if decoded.startswith('{') or decoded.startswith('['):
                try:
                    json.loads(decoded)
                    return 'json_hex'
                except json.JSONDecodeError:
                    pass
            if decoded.startswith('<') and re.match(r'<\?xml|<[a-zA-Z]', decoded):
                try:
                    minidom.parseString(decoded)
                    return 'xml_hex'
                except Exception:
                    pass
        except Exception:
            pass
        
        return 'unknown'

    def _format_data(self):
        """格式化数据"""
        text = self.input_text.get('1.0', tk.END).strip()
        if not text:
            messagebox.showwarning('提示', '请输入要格式化的数据')
            return

        fmt = self.format_var.get()
        if fmt == '自动检测':
            detected = self._detect_format(text)
        else:
            detected = fmt.lower()

        try:
            if detected == 'json':
                result = self._format_json(text)
            elif detected == 'xml':
                result = self._format_xml(text)
            elif detected == 'json_hex':
                decoded = bytes.fromhex(text.replace(' ', '')).decode('utf-8')
                result = self._format_json(decoded)
                result = f'// 从 Hex 解码后格式化:\n// {decoded}\n\n{result}'
            elif detected == 'xml_hex':
                decoded = bytes.fromhex(text.replace(' ', '')).decode('utf-8')
                result = self._format_xml(decoded)
                result = f'<!-- 从 Hex 解码后格式化: -->\n<!-- {decoded} -->\n\n{result}'
            else:
                messagebox.showwarning('提示', '无法识别数据格式，请手动选择 JSON 或 XML')
                return

            self.output_text.configure(state=tk.NORMAL)
            self.output_text.delete('1.0', tk.END)
            self.output_text.insert('1.0', result)
            self.output_text.configure(state=tk.DISABLED)

            if self._log_panel:
                self._log_panel.log_info(f'[格式化] 已格式化 {detected.upper()} 数据')

        except Exception as e:
            messagebox.showerror('格式化失败', str(e))

    def _format_json(self, text: str) -> str:
        """格式化 JSON 数据"""
        # 尝试解析
        obj = json.loads(text)
        # 格式化输出
        return json.dumps(obj, ensure_ascii=False, indent=2)

    def _format_xml(self, text: str) -> str:
        """格式化 XML 数据"""
        dom = minidom.parseString(text)
        return dom.toprettyxml(indent='  ')

    def _copy_result(self):
        """复制格式化结果"""
        try:
            text = self.output_text.get('1.0', tk.END).strip()
            if text:
                self.output_text.clipboard_clear()
                self.output_text.clipboard_append(text)
                if self._log_panel:
                    self._log_panel.log_info('[格式化] 结果已复制到剪贴板')
        except Exception:
            pass

    def _clear(self):
        """清空输入和输出"""
        self.input_text.delete('1.0', tk.END)
        self.output_text.configure(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.configure(state=tk.DISABLED)

    def format_from_log(self, data: bytes):
        """从日志接收数据自动格式化（供外部调用）"""
        try:
            text = data.decode('utf-8', errors='ignore').strip()
            if not text:
                return
            
            # 检测是否为 JSON 或 XML
            fmt = self._detect_format(text)
            if fmt in ('json', 'xml'):
                self.input_text.delete('1.0', tk.END)
                self.input_text.insert('1.0', text)
                self._format_data()
        except Exception:
            pass

    def get_settings(self) -> dict:
        return {
            'format': self.format_var.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        if 'format' in settings:
            self.format_var.set(settings['format'])
