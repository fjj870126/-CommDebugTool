"""脚本自动化面板 - 编写 Python 脚本自动化测试流程"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import traceback
import os
import sys
import io
from ui.theme import get_theme


class ScriptPanel(ttk.LabelFrame):
    """脚本自动化面板"""

    def __init__(self, parent, on_send=None, log_panel=None):
        super().__init__(parent, text=' 脚本自动化 ', padding=8)
        self._on_send = on_send
        self._on_send_silent = None  # 由外部设置静默发送回调
        self._log_panel = log_panel
        self._running = False
        self._stop_flag = False
        self._script_path = None
        self._build_ui()

    def _build_ui(self):
        # 工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 4))
        
        ttk.Button(toolbar, text='📂 打开', command=self._open_script, width=8).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(toolbar, text='💾 保存', command=self._save_script, width=8).pack(side=tk.LEFT, padx=(2, 2))
        ttk.Button(toolbar, text='📋 新建', command=self._new_script, width=8).pack(side=tk.LEFT, padx=(2, 4))
        
        self.run_btn = ttk.Button(toolbar, text='▶ 运行', command=self._run_script, width=8)
        self.run_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        self.stop_btn = ttk.Button(toolbar, text='■ 停止', command=self._stop_script,
                                   state=tk.DISABLED, width=8)
        self.stop_btn.pack(side=tk.LEFT)

        ttk.Button(toolbar, text='🗑 清除', command=self._clear_script, width=7).pack(side=tk.LEFT, padx=(4, 0))

        # 脚本编辑器
        editor_frame = ttk.LabelFrame(self, text=' 脚本编辑器 ', padding=4)
        editor_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
        
        theme = get_theme()
        self.editor = tk.Text(editor_frame, wrap=tk.NONE, height=10)
        theme.configure_text_widget(self.editor, 'monospace_large')
        
        # 行号
        line_numbers = tk.Text(editor_frame, font=('Menlo', 11), width=4,
                               bg='#252526', fg='#858585', padx=4, state=tk.DISABLED)
        
        h_scroll = ttk.Scrollbar(editor_frame, orient=tk.HORIZONTAL, command=self.editor.xview)
        v_scroll = ttk.Scrollbar(editor_frame, orient=tk.VERTICAL, command=self.editor.yview)
        self.editor.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        self.editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 更新行号
        def _update_line_numbers(event=None):
            line_numbers.configure(state=tk.NORMAL)
            line_numbers.delete('1.0', tk.END)
            lines = self.editor.get('1.0', tk.END).count('\n')
            line_numbers.insert('1.0', '\n'.join(str(i) for i in range(1, lines + 1)))
            line_numbers.configure(state=tk.DISABLED)
        self.editor.bind('<KeyRelease>', _update_line_numbers)
        self.editor.bind('<MouseWheel>', _update_line_numbers)
        
        # 输出区域
        output_frame = ttk.LabelFrame(self, text=' 输出 ', padding=4)
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        self.output_text = tk.Text(output_frame, height=6, state=tk.DISABLED)
        get_theme().configure_text_widget(self.output_text, 'monospace')
        self.output_text.configure(font=('Menlo', 10))
        output_scroll = ttk.Scrollbar(output_frame, orient=tk.VERTICAL, command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=output_scroll.set)
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        output_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 默认脚本
        self._load_default_script()

    def _load_default_script(self):
        """加载默认脚本"""
        default_script = '''# 通信调试工具 - 自动化脚本
# 可用 API:
#   send(data)          - 发送数据 (bytes 或 hex 字符串)
#   wait(ms)            - 等待指定毫秒
#   log(msg)            - 输出日志
#   assert_eq(a, b)     - 断言相等
#   assert_contains(s, sub) - 断言包含
#   hex_to_bytes(s)     - Hex 字符串转 bytes
#   bytes_to_hex(b)     - bytes 转 Hex 字符串

# 示例: 发送数据并等待回复
log("开始测试流程...")

# 发送查询指令
send("AA BB CC DD EE FF")
wait(500)

# 发送配置指令
send("01 02 03 04")
wait(200)

# 循环发送
for i in range(5):
    send(f"AA {i:02X} BB")
    wait(100)

log("测试完成!")
'''
        self.editor.insert('1.0', default_script)

    def _open_script(self):
        """打开脚本文件"""
        file_path = filedialog.askopenfilename(
            title='打开脚本',
            filetypes=[('Python 脚本', '*.py'), ('所有文件', '*.*')])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.editor.delete('1.0', tk.END)
                self.editor.insert('1.0', content)
                self._script_path = file_path
            except Exception as e:
                messagebox.showerror('打开失败', str(e))

    def _save_script(self):
        """保存脚本"""
        if not self._script_path:
            file_path = filedialog.asksaveasfilename(
                title='保存脚本',
                defaultextension='.py',
                filetypes=[('Python 脚本', '*.py'), ('所有文件', '*.*')])
            if not file_path:
                return
            self._script_path = file_path
        try:
            content = self.editor.get('1.0', tk.END)
            with open(self._script_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            messagebox.showerror('保存失败', str(e))

    def _new_script(self):
        """新建脚本"""
        self.editor.delete('1.0', tk.END)
        self._load_default_script()
        self._script_path = None

    def _clear_script(self):
        """清除当前脚本"""
        if messagebox.askyesno('确认', '确定清除当前脚本？', parent=self.winfo_toplevel()):
            self.editor.delete('1.0', tk.END)

    def _run_script(self):
        """运行脚本"""
        if self._running:
            return
        
        self._running = True
        self._stop_flag = False
        self.run_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        
        # 清空输出
        self.output_text.configure(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.configure(state=tk.DISABLED)
        
        # 获取脚本内容
        script = self.editor.get('1.0', tk.END)
        
        # 在后台线程中执行
        thread = threading.Thread(target=self._exec_script, args=(script,), daemon=True)
        thread.start()

    def _exec_script(self, script: str):
        """执行脚本"""
        # 创建脚本环境
        env = {
            'send': self._api_send,
            'wait': self._api_wait,
            'log': self._api_log,
            'assert_eq': self._api_assert_eq,
            'assert_contains': self._api_assert_contains,
            'hex_to_bytes': self._api_hex_to_bytes,
            'bytes_to_hex': self._api_bytes_to_hex,
            '__builtins__': __builtins__,
        }
        
        # 重定向输出
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        output_buffer = io.StringIO()
        sys.stdout = output_buffer
        sys.stderr = output_buffer
        
        try:
            exec(script, env)
            self._api_log('✅ 脚本执行完成')
        except SystemExit:
            pass
        except Exception as e:
            self._api_log(f'❌ 错误: {e}')
            self._api_log(traceback.format_exc())
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self._running = False
            self.root().after(0, self._on_script_done)

    def _on_script_done(self):
        """脚本执行完毕"""
        self.run_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)

    def _stop_script(self):
        """停止脚本"""
        self._stop_flag = True
        self.stop_btn.configure(state=tk.DISABLED)
        self._api_log('⏹ 脚本已停止')

    # ---- API 函数 ----

    def _api_send(self, data):
        """发送数据 API"""
        if self._stop_flag:
            raise SystemExit()
        if isinstance(data, str):
            data = bytes.fromhex(data.replace(' ', ''))
        
        # 优先使用静默发送（不弹窗）
        if self._on_send_silent:
            if self._on_send_silent(data):
                self._api_log(f'📤 发送: {data.hex().upper()}')
            else:
                self._api_log('⚠️ 未连接，脚本已停止')
                raise SystemExit()  # 停止脚本
        elif self._on_send:
            self._on_send(data)
            self._api_log(f'📤 发送: {data.hex().upper()}')
        else:
            self._api_log('⚠️ 未连接，脚本已停止')
            raise SystemExit()  # 停止脚本

    def _api_wait(self, ms: int):
        """等待 API"""
        if self._stop_flag:
            raise SystemExit()
        import time
        time.sleep(ms / 1000.0)

    def _api_log(self, msg: str):
        """日志 API"""
        self.root().after(0, lambda: self._append_output(msg))
        if self._log_panel:
            self._log_panel.log_info(f'[脚本] {msg}')

    def _api_assert_eq(self, a, b):
        """断言相等 API"""
        if a != b:
            raise AssertionError(f'断言失败: {a!r} != {b!r}')
        self._api_log(f'✅ 断言通过: {a!r} == {b!r}')

    def _api_assert_contains(self, s, sub):
        """断言包含 API"""
        if sub not in s:
            raise AssertionError(f'断言失败: {sub!r} 不在 {s!r} 中')
        self._api_log(f'✅ 断言通过: {sub!r} 在 {s!r} 中')

    def _api_hex_to_bytes(self, s: str) -> bytes:
        """Hex 转 bytes API"""
        return bytes.fromhex(s.replace(' ', ''))

    def _api_bytes_to_hex(self, b: bytes) -> str:
        """bytes 转 Hex API"""
        return b.hex().upper()

    def _append_output(self, msg: str):
        """追加输出"""
        self.output_text.configure(state=tk.NORMAL)
        self.output_text.insert(tk.END, msg + '\n')
        self.output_text.see(tk.END)
        self.output_text.configure(state=tk.DISABLED)

    def root(self):
        w = self
        while w.master:
            w = w.master
        return w

    def get_settings(self) -> dict:
        return {
            'script': self.editor.get('1.0', tk.END),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        if 'script' in settings:
            self.editor.delete('1.0', tk.END)
            self.editor.insert('1.0', settings['script'])
