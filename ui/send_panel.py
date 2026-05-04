"""快捷发送面板 - 支持直接输入Hex/ASCII发送"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from utils.hex_utils import hex_str_to_bytes, is_valid_hex
from utils.context_menu import add_entry_context_menu


class SendPanel(ttk.LabelFrame):
    def __init__(self, parent, on_send=None):
        super().__init__(parent, text=' 快捷发送 ', padding=8)
        self._on_send = on_send
        
        # 发送历史
        self._history = []  # [(mode, text), ...]
        self._history_index = -1
        self._max_history = 50
        
        # 快捷指令
        self._shortcuts = []  # [(name, mode, text), ...]
        
        # 发送统计
        self._send_count = 0
        self._send_bytes = 0
        
        self._build_ui()

    def _build_ui(self):
        # ========== 顶部控制栏（紧凑单行布局）==========
        top_bar = ttk.Frame(self)
        top_bar.pack(fill=tk.X, pady=(0, 6))

        # --- 左侧：模式与编码 ---
        left_controls = ttk.Frame(top_bar)
        left_controls.pack(side=tk.LEFT, fill=tk.X)

        # 输入模式
        mode_frame = ttk.Frame(left_controls)
        mode_frame.pack(side=tk.LEFT, padx=(0, 8))
        self.mode_var = tk.StringVar(value='hex')
        ttk.Radiobutton(mode_frame, text='Hex', variable=self.mode_var,
                        value='hex', command=self._on_mode_change, width=5).pack(side=tk.LEFT, padx=0)
        ttk.Radiobutton(mode_frame, text='ASCII', variable=self.mode_var,
                        value='ascii', command=self._on_mode_change, width=5).pack(side=tk.LEFT, padx=0)

        ttk.Separator(left_controls, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=(6, 6))

        # 编码选择
        ttk.Label(left_controls, text='编码:').pack(side=tk.LEFT)
        self.encoding_var = tk.StringVar(value='UTF-8')
        self.encoding_cb = ttk.Combobox(left_controls, textvariable=self.encoding_var,
                                        values=['UTF-8', 'GBK', 'GB2312', 'ISO-8859-1', 'ASCII'],
                                        state='readonly', width=8)
        self.encoding_cb.pack(side=tk.LEFT, padx=(4, 6))

        # 换行符
        ttk.Label(left_controls, text='换行:').pack(side=tk.LEFT)
        self.newline_var = tk.StringVar(value='无')
        self.newline_cb = ttk.Combobox(left_controls, textvariable=self.newline_var,
                                       values=['无', '\\r\\n', '\\n', '\\r'], state='readonly', width=6)
        self.newline_cb.pack(side=tk.LEFT, padx=(4, 0))

        # --- 右侧：统计与操作 ---
        right_controls = ttk.Frame(top_bar)
        right_controls.pack(side=tk.RIGHT, fill=tk.X)

        # 发送统计
        self.count_label = ttk.Label(right_controls, text='发送: 0', foreground='gray')
        self.count_label.pack(side=tk.LEFT, padx=(0, 8))

        # 数据长度
        self.len_label = ttk.Label(right_controls, text='长度: 0', foreground='gray')
        self.len_label.pack(side=tk.LEFT, padx=(0, 8))

        # 快捷键提示
        ttk.Label(right_controls, text='Ctrl+Enter 发送', foreground='gray').pack(side=tk.LEFT, padx=(0, 4))

        # ========== 主编辑区：行号 + 输入框（压缩高度）==========
        input_section = ttk.Frame(self)
        input_section.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        # 左侧行号（固定宽度）
        self._line_numbers = tk.Text(input_section, width=4, height=4,
                                     font=('Consolas', 10), bg='#f5f5f5', fg='#666',
                                     state=tk.DISABLED, padx=2, pady=2,
                                     highlightthickness=0, borderwidth=0)
        self._line_numbers.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 4))

        # 中间输入框（压缩高度）
        self.input_text = tk.Text(input_section, height=4, font=('Consolas', 10),
                                  wrap=tk.NONE, undo=True, relief=tk.FLAT, borderwidth=1)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        self.input_text.bind('<Return>', lambda e: self._on_enter_in_text(e))
        self.input_text.bind('<KeyRelease>', self._on_input_change)
        self.input_text.bind('<Up>', self._on_history_up)
        self.input_text.bind('<Down>', self._on_history_down)
        add_entry_context_menu(self.input_text)

        # 滚动条
        text_scroll = ttk.Scrollbar(input_section, orient=tk.VERTICAL,
                                    command=self._on_text_scroll)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.input_text.configure(yscrollcommand=text_scroll.set)

        self._update_line_numbers()

        # ========== 底部按钮行：发送 + 历史 ==========
        bottom_bar = ttk.Frame(self)
        bottom_bar.pack(fill=tk.X, pady=(0, 6))

        # 左侧：发送按钮（主操作）
        send_frame = ttk.Frame(bottom_bar)
        send_frame.pack(side=tk.LEFT)
        self.send_btn = ttk.Button(send_frame, text='▶ 发送', command=self._do_send, width=10)
        self.send_btn.pack(side=tk.LEFT)

        # 右侧：历史记录（标签 + 下拉 + 清空）
        hist_frame = ttk.Frame(bottom_bar)
        hist_frame.pack(side=tk.LEFT, padx=(20, 0))

        ttk.Label(hist_frame, text='历史:', font=('', 9)).pack(side=tk.LEFT)
        self.history_var = tk.StringVar()
        self.history_cb = ttk.Combobox(hist_frame, textvariable=self.history_var,
                                       state='readonly', width=14)
        self.history_cb.pack(side=tk.LEFT, padx=(4, 4))
        self.history_cb.bind('<<ComboboxSelected>>', self._on_history_select)
        ttk.Button(hist_frame, text='清空', command=self._clear_history,
                   width=6).pack(side=tk.LEFT)

        # ========== 中部：折叠面板区域（快捷指令 + 追加数据 + 定时发送）==========
        panels_nb = ttk.Notebook(self)
        panels_nb.pack(fill=tk.X, pady=(0, 6))

        # --- Tab 1: 快捷指令 ---
        shortcut_tab = ttk.Frame(panels_nb, padding=6)
        panels_nb.add(shortcut_tab, text=' 快捷指令 ')

        # 按钮工具栏（紧凑网格）
        toolbar = ttk.Frame(shortcut_tab)
        toolbar.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(toolbar, text='+ 添加', command=self._add_shortcut, width=8).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(toolbar, text='管理', command=self._manage_shortcuts, width=8).pack(side=tk.LEFT)

        # 按钮区域（带滚动）
        self._shortcut_canvas = tk.Canvas(shortcut_tab, highlightthickness=0, height=70, bg='#fafafa')
        self._shortcut_inner = ttk.Frame(self._shortcut_canvas)
        self._shortcut_scroll = ttk.Scrollbar(shortcut_tab, orient=tk.VERTICAL,
                                               command=self._shortcut_canvas.yview)
        self._shortcut_canvas.configure(yscrollcommand=self._shortcut_scroll.set)

        self._shortcut_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._shortcut_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._shortcut_canvas_win = self._shortcut_canvas.create_window(
            (0, 0), window=self._shortcut_inner, anchor='nw', width=200)
        self._shortcut_inner.bind('<Configure>', self._on_shortcut_inner_configure)
        self._shortcut_canvas.bind('<Configure>', self._on_shortcut_canvas_configure)

        # 鼠标滚轮（仅作用于快捷指令区域）
        self._shortcut_canvas.bind('<MouseWheel>', lambda e: self._shortcut_canvas.yview_scroll(-1*(e.delta//120), 'units'))
        self._shortcut_canvas.bind('<Button-4>', lambda e: self._shortcut_canvas.yview_scroll(-1, 'units'))
        self._shortcut_canvas.bind('<Button-5>', lambda e: self._shortcut_canvas.yview_scroll(1, 'units'))

        # --- Tab 2: 追加数据 ---
        append_tab = ttk.Frame(panels_nb, padding=6)
        panels_nb.add(append_tab, text=' 追加数据 ')

        append_grid = ttk.Frame(append_tab)
        append_grid.pack(fill=tk.X)
        ttk.Label(append_grid, text='前缀:').grid(row=0, column=0, sticky=tk.W, padx=(0, 4))
        self.prefix_var = tk.StringVar()
        self.prefix_entry = ttk.Entry(append_grid, textvariable=self.prefix_var,
                                      font=('Consolas', 10), width=24)
        self.prefix_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 12))
        add_entry_context_menu(self.prefix_entry)

        ttk.Label(append_grid, text='后缀:').grid(row=1, column=0, sticky=tk.W, padx=(0, 4), pady=(4, 0))
        self.suffix_var = tk.StringVar()
        self.suffix_entry = ttk.Entry(append_grid, textvariable=self.suffix_var,
                                      font=('Consolas', 10), width=24)
        self.suffix_entry.grid(row=1, column=1, sticky=tk.EW, pady=(4, 0))
        add_entry_context_menu(self.suffix_entry)
        append_grid.columnconfigure(1, weight=1)

        # --- Tab 3: 定时发送 ---
        timer_tab = ttk.Frame(panels_nb, padding=6)
        panels_nb.add(timer_tab, text=' 定时发送 ')

        timer_grid = ttk.Frame(timer_tab)
        timer_grid.pack(fill=tk.X)
        self.timer_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(timer_grid, text='启用定时', variable=self.timer_var,
                        command=self._toggle_timer).grid(row=0, column=0, sticky=tk.W, padx=(0, 12))
        ttk.Label(timer_grid, text='间隔(ms):').grid(row=0, column=1, sticky=tk.W, padx=(0, 4))
        self.interval_var = tk.StringVar(value='1000')
        self.interval_entry = ttk.Entry(timer_grid, textvariable=self.interval_var, width=8)
        self.interval_entry.grid(row=0, column=2, sticky=tk.W, padx=(0, 12))
        add_entry_context_menu(self.interval_entry)

        ttk.Label(timer_grid, text='行延迟(ms):').grid(row=0, column=3, sticky=tk.W, padx=(0, 4))
        self.line_delay_var = tk.StringVar(value='0')
        self.line_delay_entry = ttk.Entry(timer_grid, textvariable=self.line_delay_var, width=8)
        self.line_delay_entry.grid(row=0, column=4, sticky=tk.W)
        add_entry_context_menu(self.line_delay_entry)

        self._timer_id = None

    def _on_shortcut_inner_configure(self, event):
        """快捷指令内部 Frame 尺寸变化时更新 Canvas 滚动区域"""
        self._shortcut_canvas.configure(scrollregion=self._shortcut_canvas.bbox('all'))
        # 自动调整 Canvas 高度
        self._shortcut_canvas.configure(height=min(event.height, 120))

    def _on_shortcut_canvas_configure(self, event):
        """Canvas 宽度变化时调整内部 Frame 宽度"""
        self._shortcut_canvas.itemconfig(self._shortcut_canvas_win, width=event.width)

    def _on_text_scroll(self, *args):
        """同步行号滚动（转发滚动命令到输入框和行号）"""
        self._line_numbers.yview(*args)
        self.input_text.yview(*args)

    def _update_line_numbers(self):
        """更新行号显示"""
        lines = self.input_text.get('1.0', 'end-1c').split('\n')
        line_count = len(lines)
        self._line_numbers.configure(state=tk.NORMAL)
        self._line_numbers.delete('1.0', tk.END)
        self._line_numbers.insert('1.0', '\n'.join(str(i) for i in range(1, line_count + 1)))
        self._line_numbers.configure(state=tk.DISABLED)

    def _on_mode_change(self):
        """切换输入模式"""
        if self.mode_var.get() == 'hex':
            # 切换到 Hex 模式时，格式化当前内容
            text = self._get_input_text()
            if text:
                self._set_input_text(self._format_hex(text))

    def _get_input_text(self) -> str:
        """获取输入框文本"""
        return self.input_text.get('1.0', 'end-1c').strip()

    def _set_input_text(self, text: str):
        """设置输入框文本"""
        self.input_text.delete('1.0', tk.END)
        self.input_text.insert('1.0', text)
        self._update_line_numbers()

    def _on_enter_in_text(self, event):
        """在 Text 中按 Enter：Ctrl+Enter 发送，普通 Enter 换行"""
        if event.state & 0x0004:  # Ctrl
            self._do_send()
            return 'break'
        return None

    def _on_input_change(self, event=None):
        """输入变化时更新长度显示和 Hex 格式化"""
        text = self._get_input_text()
        
        # 更新长度显示
        try:
            if self.mode_var.get() == 'hex':
                hex_chars = ''.join(ch for ch in text if ch in '0123456789ABCDEFabcdef')
                byte_len = len(hex_chars) // 2
                # 奇数个 hex 字符时提示
                if hex_chars and len(hex_chars) % 2 == 1:
                    self.len_label.configure(text=f'长度: {byte_len} (奇数位, 将补0)',
                                             foreground='orange')
                else:
                    self.len_label.configure(text=f'长度: {byte_len}', foreground='gray')
            else:
                byte_len = len(text.encode(self.encoding_var.get() or 'UTF-8'))
                self.len_label.configure(text=f'长度: {byte_len}', foreground='gray')
        except Exception:
            self.len_label.configure(text='长度: -', foreground='red')

        # Hex 模式下自动格式化
        if self.mode_var.get() == 'hex' and event and event.keysym not in ('Up', 'Down', 'Left', 'Right'):
            self._auto_format_hex()

        self._update_line_numbers()

    def _auto_format_hex(self):
        """Hex 模式下自动格式化"""
        text = self._get_input_text()
        formatted = self._format_hex(text)
        if formatted != text:
            cursor_idx = self.input_text.index(tk.INSERT)
            cursor_row, cursor_col = map(int, cursor_idx.split('.'))
            
            line_before = self.input_text.get(f'{cursor_row}.0', cursor_idx)
            hex_chars_before = ''.join(ch for ch in line_before if ch in '0123456789ABCDEFabcdef').upper()
            
            self._set_input_text(formatted)
            
            if hex_chars_before:
                new_col = len(hex_chars_before) + (len(hex_chars_before) // 2)
                if len(hex_chars_before) % 2 == 0:
                    new_col -= 1
            else:
                new_col = 0
            try:
                self.input_text.mark_set(tk.INSERT, f'{cursor_row}.{new_col}')
            except Exception:
                pass

    def _format_hex(self, text: str) -> str:
        """格式化 Hex 字符串：每两个字符一组用空格分隔"""
        # 提取所有 Hex 字符
        hex_chars = ''.join(ch for ch in text if ch in '0123456789ABCDEFabcdef').upper()
        if not hex_chars:
            return ''
        
        # 按两个字符一组分组
        parts = []
        for i in range(0, len(hex_chars), 2):
            parts.append(hex_chars[i:i+2])
        
        return ' '.join(parts)

    # ============================================================
    # 发送历史管理
    # ============================================================

    def _refresh_history_list(self):
        """刷新历史下拉列表"""
        display = []
        for mode, text in self._history:
            prefix = 'H' if mode == 'hex' else 'A'
            short = text[:30] + '...' if len(text) > 30 else text
            display.append(f'[{prefix}] {short}')
        self.history_cb['values'] = display
        self.history_var.set('')

    def _on_history_select(self, event=None):
        """从历史下拉选择"""
        idx = self.history_cb.current()
        if idx < 0:
            return
        history = self._history
        if idx < len(history):
            mode, text = history[idx]
            self.mode_var.set(mode)
            self._set_input_text(text)
            if mode == 'hex':
                formatted = self._format_hex(text)
                if formatted != text:
                    self._set_input_text(formatted)

    def _on_history_up(self, event):
        """上箭头：切换历史"""
        if not self._history:
            return
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            mode, text = self._history[-(self._history_index + 1)]
            self.mode_var.set(mode)
            self._set_input_text(text)

    def _on_history_down(self, event):
        """下箭头：切换历史"""
        if self._history_index >= 0:
            self._history_index -= 1
            if self._history_index >= 0:
                mode, text = self._history[-(self._history_index + 1)]
                self.mode_var.set(mode)
                self._set_input_text(text)
            else:
                self._set_input_text('')

    def _add_to_history(self, mode: str, text: str):
        """添加到发送历史"""
        # 避免重复
        if self._history and self._history[-1] == (mode, text):
            return
        self._history.append((mode, text))
        if len(self._history) > self._max_history:
            self._history.pop(0)
        self._history_index = -1
        self._refresh_history_list()

    def _clear_history(self):
        """清空发送历史"""
        if not self._history:
            return
        if messagebox.askyesno('确认', '确定要清空所有发送历史吗？'):
            self._history.clear()
            self._history_index = -1
            self._refresh_history_list()

    def _get_send_data(self, text: str) -> bytes:
        """根据模式和编码获取要发送的字节数据"""
        if not text:
            return b''
        
        if self.mode_var.get() == 'hex':
            # Hex 模式
            hex_chars = ''.join(ch for ch in text if ch in '0123456789ABCDEFabcdef')
            if len(hex_chars) % 2 == 1:
                hex_chars = '0' + hex_chars
            return bytes.fromhex(hex_chars)
        else:
            # ASCII 模式
            encoding = self.encoding_var.get() or 'UTF-8'
            data = text.encode(encoding)
            
            # 追加换行符
            nl = self.newline_var.get()
            if nl == '\\r\\n':
                data += b'\r\n'
            elif nl == '\\n':
                data += b'\n'
            elif nl == '\\r':
                data += b'\r'
            
            return data

    def _do_send(self):
        """执行发送"""
        if not self._on_send:
            return
        
        text = self._get_input_text()
        if not text:
            return
        
        # 获取前缀和后缀
        prefix_text = self.prefix_var.get().strip()
        suffix_text = self.suffix_var.get().strip()
        
        # 按行分割
        lines = text.split('\n')
        line_delay = 0
        try:
            line_delay = int(self.line_delay_var.get())
        except ValueError:
            line_delay = 0
        line_delay = max(0, min(line_delay, 10000))
        
        def _send_line(index):
            if index >= len(lines):
                return
            line = lines[index].strip()
            if not line:
                _send_line(index + 1)
                return
            
            try:
                # 组合数据：前缀 + 行内容 + 后缀
                full_text = line
                if prefix_text:
                    full_text = prefix_text + ' ' + full_text
                if suffix_text:
                    full_text = full_text + ' ' + suffix_text
                
                data = self._get_send_data(full_text)
                if data:
                    self._on_send(data)
                    self._send_count += 1
                    self._send_bytes += len(data)
                    self.count_label.configure(
                        text=f'发送: {self._send_count} 次 / {self._send_bytes} B')
                    
                    # 添加到历史
                    self._add_to_history(self.mode_var.get(), line)
            except Exception as e:
                self.count_label.configure(text=f'发送失败: {e}')
            
            # 如果有行延迟且不是最后一行，延迟发送下一行
            if line_delay > 0 and index < len(lines) - 1:
                self.after(line_delay, lambda: _send_line(index + 1))
            else:
                # 无延迟或最后一行，立即发送下一行
                _send_line(index + 1)
        
        _send_line(0)

    def _toggle_timer(self):
        if self.timer_var.get():
            self._start_timer()
        else:
            self._stop_timer()

    def _start_timer(self):
        try:
            interval = int(self.interval_var.get())
        except ValueError:
            interval = 1000
        interval = max(10, interval)

        def _tick():
            if self.timer_var.get():
                self._do_send()
                self._timer_id = self.after(interval, _tick)

        self._timer_id = self.after(interval, _tick)

    def _stop_timer(self):
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None

    # ============================================================
    # 快捷指令管理
    # ============================================================

    def _refresh_shortcut_buttons(self):
        """刷新快捷指令按钮（自动换行）"""
        for w in self._shortcut_inner.winfo_children():
            w.destroy()
        
        if not self._shortcuts:
            ttk.Label(self._shortcut_inner, text='(无快捷指令，点击"添加"创建)',
                      foreground='gray').pack(side=tk.LEFT, padx=4)
            return
        
        # 分组显示 - 使用自动换行的 Frame
        groups = {}
        for name, mode, text in self._shortcuts:
            group = '默认'
            if ':' in name:
                group, name = name.split(':', 1)
            if group not in groups:
                groups[group] = []
            groups[group].append((name, mode, text))
        
        for group_name, items in groups.items():
            group_frame = ttk.Frame(self._shortcut_inner)
            group_frame.pack(fill=tk.X, pady=(1, 0))
            
            ttk.Label(group_frame, text=f'[{group_name}]',
                      font=('', 9, 'bold'), foreground='#555').pack(side=tk.LEFT, padx=(0, 4))
            
            for name, mode, text in items:
                display_text = text[:15] + '...' if len(text) > 15 else text
                btn = ttk.Button(group_frame, text=f'{name} ({display_text})',
                                 command=lambda m=mode, t=text: self._send_shortcut(m, t),
                                 style='Toolbutton')
                btn.pack(side=tk.LEFT, padx=(1, 1))

    def _send_shortcut(self, mode: str, text: str):
        """发送快捷指令"""
        self.mode_var.set(mode)
        self._set_input_text(text)
        self._do_send()

    def _center_dialog(self, win, w, h):
        win.withdraw()
        win.update_idletasks()
        pw = self.winfo_toplevel().winfo_width()
        ph = self.winfo_toplevel().winfo_height()
        px = self.winfo_toplevel().winfo_rootx()
        py = self.winfo_toplevel().winfo_rooty()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        win.geometry(f'{w}x{h}+{x}+{y}')
        win.deiconify()

    def _add_shortcut(self):
        """添加快捷指令"""
        dialog = tk.Toplevel(self)
        dialog.title('添加快捷指令')
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        self._center_dialog(dialog, 500, 320)
        
        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 名称
        ttk.Label(frame, text='名称:').pack(anchor=tk.W)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(frame, textvariable=name_var, width=40)
        name_entry.pack(fill=tk.X, pady=(2, 10))
        name_entry.focus()
        
        # 分组
        ttk.Label(frame, text='分组 (可选, 格式: 分组名:名称):').pack(anchor=tk.W)
        group_var = tk.StringVar()
        ttk.Entry(frame, textvariable=group_var, width=40).pack(fill=tk.X, pady=(2, 10))
        
        # 模式
        ttk.Label(frame, text='模式:').pack(anchor=tk.W)
        mode_var = tk.StringVar(value=self.mode_var.get())
        mode_frame = ttk.Frame(frame)
        mode_frame.pack(fill=tk.X, pady=(2, 10))
        ttk.Radiobutton(mode_frame, text='Hex', variable=mode_var,
                         value='hex').pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(mode_frame, text='ASCII', variable=mode_var,
                         value='ascii').pack(side=tk.LEFT)
        
        # 数据
        ttk.Label(frame, text='数据:').pack(anchor=tk.W)
        text_var = tk.StringVar(value=self._get_input_text())
        text_entry = ttk.Entry(frame, textvariable=text_var, font=('Courier New', 10), width=40)
        text_entry.pack(fill=tk.X, pady=(2, 10))
        
        def _on_text_entry_keyrelease(event=None):
            if mode_var.get() == 'hex':
                raw = text_entry.get()
                hex_chars = ''.join(ch for ch in raw if ch in '0123456789ABCDEFabcdef').upper()
                parts = []
                for i in range(0, len(hex_chars), 2):
                    parts.append(hex_chars[i:i+2])
                formatted = ' '.join(parts)
                if formatted != raw:
                    text_var.set(formatted)
                    # 光标放在格式化后文本的末尾
                    text_entry.icursor(tk.END)
        
        def _on_mode_change_shortcut():
            if mode_var.get() == 'hex':
                _on_text_entry_keyrelease()
        
        text_entry.bind('<KeyRelease>', _on_text_entry_keyrelease)
        mode_var.trace_add('write', lambda *_: _on_mode_change_shortcut())
        
        def _ok():
            name = name_var.get().strip()
            raw_text = text_var.get().strip()
            group = group_var.get().strip()
            if not name:
                messagebox.showwarning('提示', '请输入名称')
                return
            if not raw_text:
                messagebox.showwarning('提示', '请输入数据')
                return
            
            mode = mode_var.get()
            # Hex 模式校验并自动格式化
            if mode == 'hex':
                hex_chars = ''.join(ch for ch in raw_text if ch in '0123456789ABCDEFabcdef')
                if not hex_chars:
                    messagebox.showwarning('提示', 'Hex 模式下请输入有效的十六进制字符')
                    return
                if len(hex_chars) % 2 != 0:
                    messagebox.showwarning('提示', 'Hex 字符数必须为偶数')
                    return
                parts = []
                for i in range(0, len(hex_chars), 2):
                    parts.append(hex_chars[i:i+2].upper())
                text = ' '.join(parts)
                # 更新输入框显示格式化结果
                text_var.set(text)
            else:
                text = raw_text
            
            if group:
                full_name = f'{group}:{name}'
            else:
                full_name = name
            self._shortcuts.append((full_name, mode, text))
            self._refresh_shortcut_buttons()
            self._save_shortcuts()
            dialog.destroy()
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text='确定', command=_ok, width=10).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_frame, text='取消', command=dialog.destroy, width=10).pack(side=tk.RIGHT)

    def _manage_shortcuts(self):
        """管理快捷指令"""
        if not self._shortcuts:
            messagebox.showinfo('提示', '暂无快捷指令')
            return
        
        dialog = tk.Toplevel(self)
        dialog.title('管理快捷指令')
        dialog.transient(self)
        dialog.grab_set()
        self._center_dialog(dialog, 550, 450)
        
        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 列表
        columns = ('name', 'mode', 'text')
        tree = ttk.Treeview(frame, columns=columns, show='headings', selectmode='browse')
        tree.heading('name', text='名称')
        tree.heading('mode', text='模式')
        tree.heading('text', text='数据')
        tree.column('name', width=180)
        tree.column('mode', width=60)
        tree.column('text', width=270)
        
        for name, mode, text in self._shortcuts:
            tree.insert('', tk.END, values=(name, mode, text))
        
        tree.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        def _delete():
            sel = tree.selection()
            if not sel:
                return
            item = tree.item(sel[0])
            values = item['values']
            if values:
                name, mode, text = values
                self._shortcuts = [(n, m, t) for n, m, t in self._shortcuts
                                   if not (n == name and m == mode and t == text)]
                tree.delete(sel[0])
                self._refresh_shortcut_buttons()
                self._save_shortcuts()
        
        def _clear_all():
            if messagebox.askyesno('确认', '确定要清空所有快捷指令吗？'):
                self._shortcuts.clear()
                for item in tree.get_children():
                    tree.delete(item)
                self._refresh_shortcut_buttons()
                self._save_shortcuts()
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text='删除选中', command=_delete).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_frame, text='清空全部', command=_clear_all).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text='关闭', command=dialog.destroy).pack(side=tk.RIGHT)

    def get_shortcuts_data(self) -> list:
        return list(self._shortcuts)

    def load_shortcuts_data(self, data: list):
        if data:
            self._shortcuts = [(item[0], item[1], item[2]) for item in data if len(item) >= 3]
        self._refresh_shortcut_buttons()

    def _save_shortcuts(self):
        pass

    def _load_shortcuts(self):
        pass

    # ============================================================
    # 设置保存/恢复
    # ============================================================

    def destroy(self):
        self._stop_timer()
        super().destroy()

    def get_settings(self) -> dict:
        return {
            'mode': self.mode_var.get(),
            'input': self._get_input_text(),
            'interval': self.interval_var.get(),
            'encoding': self.encoding_var.get(),
            'newline': self.newline_var.get(),
            'prefix': self.prefix_var.get(),
            'suffix': self.suffix_var.get(),
            'line_delay': self.line_delay_var.get(),
            'history': self._history[-50:],
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        self.mode_var.set(settings.get('mode', 'hex'))
        self._set_input_text(settings.get('input', ''))
        self.interval_var.set(settings.get('interval', '1000'))
        self.encoding_var.set(settings.get('encoding', 'UTF-8'))
        self.newline_var.set(settings.get('newline', '无'))
        self.prefix_var.set(settings.get('prefix', ''))
        self.suffix_var.set(settings.get('suffix', ''))
        history = settings.get('history')
        if history:
            self._history = [(m, t) for m, t in history if isinstance(m, str) and isinstance(t, str)]
            self._refresh_history_list()
        self.line_delay_var.set(settings.get('line_delay', '0'))
