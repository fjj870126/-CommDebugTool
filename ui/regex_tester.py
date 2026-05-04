"""正则表达式测试器 - 实时测试正则匹配"""

import tkinter as tk
from tkinter import ttk, messagebox
import re
from utils.context_menu import add_entry_context_menu


class RegexTester(ttk.LabelFrame):
    """正则表达式测试器"""

    def __init__(self, parent):
        super().__init__(parent, text=' 正则表达式测试器 ', padding=8)
        self._build_ui()

    def _build_ui(self):
        # ===== 正则表达式输入 =====
        ttk.Label(self, text='正则表达式:', font=('', 12, 'bold')).pack(anchor=tk.W)

        regex_frame = ttk.Frame(self)
        regex_frame.pack(fill=tk.X, pady=(0, 4))

        self.regex_var = tk.StringVar(value='')
        self.regex_entry = ttk.Entry(regex_frame, textvariable=self.regex_var,
                                     font=('Courier New', 12))
        self.regex_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        add_entry_context_menu(self.regex_entry)

        # 常用正则快速插入
        quick_frame = ttk.Frame(self)
        quick_frame.pack(fill=tk.X, pady=(0, 8))

        quick_patterns = [
            ('IP地址', r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'),
            ('MAC地址', r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'),
            ('Hex字节', r'[0-9A-Fa-f]{2}'),
            ('数字', r'\d+'),
            ('邮箱', r'[\w\.-]+@[\w\.-]+\.\w+'),
            ('URL', r'https?://[^\s]+'),
        ]
        for label, pattern in quick_patterns:
            btn = ttk.Button(quick_frame, text=label, width=8,
                           command=lambda p=pattern: self._insert_pattern(p))
            btn.pack(side=tk.LEFT, padx=1)

        # ===== 标志位 =====
        flags_frame = ttk.Frame(self)
        flags_frame.pack(fill=tk.X, pady=(0, 8))

        self.flag_ignorecase = tk.BooleanVar(value=True)
        ttk.Checkbutton(flags_frame, text='忽略大小写', variable=self.flag_ignorecase).pack(side=tk.LEFT, padx=2)
        self.flag_multiline = tk.BooleanVar(value=False)
        ttk.Checkbutton(flags_frame, text='多行模式', variable=self.flag_multiline).pack(side=tk.LEFT, padx=2)
        self.flag_dotall = tk.BooleanVar(value=False)
        ttk.Checkbutton(flags_frame, text='点号匹配换行', variable=self.flag_dotall).pack(side=tk.LEFT, padx=2)
        self.flag_unicode = tk.BooleanVar(value=True)
        ttk.Checkbutton(flags_frame, text='Unicode', variable=self.flag_unicode).pack(side=tk.LEFT, padx=2)

        # 绑定标志变化
        for var in [self.flag_ignorecase, self.flag_multiline, self.flag_dotall, self.flag_unicode]:
            var.trace_add('write', lambda *args: self._do_test())

        # ===== 测试文本 =====
        ttk.Label(self, text='测试文本:', font=('', 12, 'bold')).pack(anchor=tk.W)

        text_frame = ttk.Frame(self)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        self.test_text = tk.Text(text_frame, height=8, font=('Courier New', 12),
                                 wrap=tk.WORD, undo=True)
        text_scroll_y = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.test_text.yview)
        text_scroll_x = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.test_text.xview)
        self.test_text.configure(yscrollcommand=text_scroll_y.set, xscrollcommand=text_scroll_x.set)

        self.test_text.grid(row=0, column=0, sticky='nsew')
        text_scroll_y.grid(row=0, column=1, sticky='ns')
        text_scroll_x.grid(row=1, column=0, sticky='ew')
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        # 绑定文本变化
        self.test_text.bind('<<Modified>>', self._on_text_modified)

        # ===== 操作按钮 =====
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(btn_frame, text='🔍 测试匹配', command=self._do_test, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='替换', command=self._do_replace, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='分割', command=self._do_split, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='清空', command=self._clear, width=8).pack(side=tk.LEFT, padx=(8, 0))

        # 替换输入
        ttk.Label(btn_frame, text='替换为:').pack(side=tk.LEFT, padx=(12, 2))
        self.replace_var = tk.StringVar(value='')
        self.replace_entry = ttk.Entry(btn_frame, textvariable=self.replace_var,
                                       font=('Courier New', 11), width=15)
        self.replace_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        add_entry_context_menu(self.replace_entry)

        # ===== 结果区 =====
        result_frame = ttk.LabelFrame(self, text=' 匹配结果 ', padding=4)
        result_frame.pack(fill=tk.BOTH, expand=True)

        # 结果表格
        columns = ('index', 'match', 'start', 'end', 'length')
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show='headings',
                                        height=6)
        self.result_tree.heading('index', text='#')
        self.result_tree.heading('match', text='匹配内容')
        self.result_tree.heading('start', text='起始')
        self.result_tree.heading('end', text='结束')
        self.result_tree.heading('length', text='长度')

        self.result_tree.column('index', width=40, minwidth=30, anchor=tk.CENTER)
        self.result_tree.column('match', width=250, minwidth=100)
        self.result_tree.column('start', width=60, minwidth=50, anchor=tk.CENTER)
        self.result_tree.column('end', width=60, minwidth=50, anchor=tk.CENTER)
        self.result_tree.column('length', width=60, minwidth=50, anchor=tk.CENTER)

        result_scroll = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=result_scroll.set)

        self.result_tree.grid(row=0, column=0, sticky='nsew')
        result_scroll.grid(row=0, column=1, sticky='ns')
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        # 双击结果跳转到匹配位置
        self.result_tree.bind('<Double-1>', self._on_result_double_click)

        # 状态栏
        self.status_var = tk.StringVar(value='就绪')
        ttk.Label(self, textvariable=self.status_var, foreground='gray').pack(anchor=tk.W, pady=(4, 0))

        # 绑定正则输入变化自动测试
        self.regex_var.trace_add('write', lambda *args: self._do_test())

    def _insert_pattern(self, pattern: str):
        """插入常用正则"""
        self.regex_var.set(pattern)
        self.regex_entry.icursor(tk.END)
        self.regex_entry.focus()

    def _on_text_modified(self, event=None):
        """文本修改时自动测试"""
        if self.test_text.edit_modified():
            self._do_test()
            self.test_text.edit_modified(False)

    def _get_flags(self) -> int:
        """获取正则标志"""
        flags = 0
        if self.flag_ignorecase.get():
            flags |= re.IGNORECASE
        if self.flag_multiline.get():
            flags |= re.MULTILINE
        if self.flag_dotall.get():
            flags |= re.DOTALL
        if self.flag_unicode.get():
            flags |= re.UNICODE
        return flags

    def _do_test(self):
        """执行正则匹配测试"""
        # 清除旧结果
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

        # 清除旧高亮
        self.test_text.tag_delete('match')
        self.test_text.tag_delete('match_sel')

        pattern = self.regex_var.get().strip()
        text = self.test_text.get('1.0', tk.END).rstrip('\n')

        if not pattern:
            self.status_var.set('请输入正则表达式')
            return

        if not text:
            self.status_var.set('请输入测试文本')
            return

        try:
            flags = self._get_flags()
            compiled = re.compile(pattern, flags)
            matches = list(compiled.finditer(text))

            if not matches:
                self.status_var.set('无匹配结果')
                return

            # 配置高亮标签
            self.test_text.tag_configure('match', background='#FFFF00', foreground='#000000')
            self.test_text.tag_configure('match_sel', background='#FFA500', foreground='#000000')

            # 插入结果
            for i, m in enumerate(matches):
                match_text = m.group()
                self.result_tree.insert('', tk.END, iid=str(i),
                                        values=(i + 1, match_text, m.start(), m.end(), len(match_text)))

                # 高亮匹配
                start_idx = f'1.0 + {m.start()} chars'
                end_idx = f'1.0 + {m.end()} chars'
                self.test_text.tag_add('match', start_idx, end_idx)

            # 选中第一个匹配
            if matches:
                first = matches[0]
                self.test_text.tag_add('match_sel', f'1.0 + {first.start()} chars',
                                       f'1.0 + {first.end()} chars')
                self.test_text.see(f'1.0 + {first.start()} chars')

            # 显示分组信息
            group_info = ''
            if matches and matches[0].groups():
                group_info = f', 分组: {matches[0].groups()}'
                if matches[0].groupdict():
                    group_info += f' {matches[0].groupdict()}'

            self.status_var.set(f'找到 {len(matches)} 个匹配{group_info}')

        except re.error as e:
            self.status_var.set(f'正则错误: {e}')
        except Exception as e:
            self.status_var.set(f'错误: {e}')

    def _do_replace(self):
        """执行替换"""
        pattern = self.regex_var.get().strip()
        replacement = self.replace_var.get()
        text = self.test_text.get('1.0', tk.END).rstrip('\n')

        if not pattern:
            messagebox.showwarning('提示', '请输入正则表达式')
            return

        try:
            flags = self._get_flags()
            compiled = re.compile(pattern, flags)
            result, count = compiled.subn(replacement, text)

            # 显示替换结果
            self.test_text.delete('1.0', tk.END)
            self.test_text.insert('1.0', result)

            self.status_var.set(f'替换完成: {count} 处替换')

        except re.error as e:
            self.status_var.set(f'正则错误: {e}')
        except Exception as e:
            self.status_var.set(f'替换失败: {e}')

    def _do_split(self):
        """执行分割"""
        pattern = self.regex_var.get().strip()
        text = self.test_text.get('1.0', tk.END).rstrip('\n')

        if not pattern:
            messagebox.showwarning('提示', '请输入正则表达式')
            return

        try:
            flags = self._get_flags()
            compiled = re.compile(pattern, flags)
            parts = compiled.split(text)

            # 清除旧结果
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)

            # 显示分割结果
            for i, part in enumerate(parts):
                self.result_tree.insert('', tk.END, iid=str(i),
                                        values=(i + 1, part[:100], '', '', len(part)))

            self.status_var.set(f'分割为 {len(parts)} 部分')

        except re.error as e:
            self.status_var.set(f'正则错误: {e}')
        except Exception as e:
            self.status_var.set(f'分割失败: {e}')

    def _on_result_double_click(self, event):
        """双击结果跳转到匹配位置"""
        sel = self.result_tree.selection()
        if not sel:
            return
        item = self.result_tree.item(sel[0])
        values = item['values']
        if len(values) < 4:
            return

        try:
            start = int(values[2])
            end = int(values[3])

            # 清除旧选中高亮
            self.test_text.tag_delete('match_sel')

            # 高亮选中的匹配
            self.test_text.tag_configure('match_sel', background='#FFA500', foreground='#000000')
            self.test_text.tag_add('match_sel', f'1.0 + {start} chars', f'1.0 + {end} chars')
            self.test_text.see(f'1.0 + {start} chars')

            # 聚焦到文本区域
            self.test_text.focus_set()
        except Exception:
            pass

    def _clear(self):
        """清空所有"""
        self.regex_var.set('')
        self.replace_var.set('')
        self.test_text.delete('1.0', tk.END)
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self.test_text.tag_delete('match')
        self.test_text.tag_delete('match_sel')
        self.status_var.set('就绪')

    def get_settings(self) -> dict:
        return {
            'regex': self.regex_var.get(),
            'replace': self.replace_var.get(),
            'flag_ignorecase': self.flag_ignorecase.get(),
            'flag_multiline': self.flag_multiline.get(),
            'flag_dotall': self.flag_dotall.get(),
            'flag_unicode': self.flag_unicode.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        self.regex_var.set(settings.get('regex', ''))
        self.replace_var.set(settings.get('replace', ''))
        self.flag_ignorecase.set(settings.get('flag_ignorecase', True))
        self.flag_multiline.set(settings.get('flag_multiline', False))
        self.flag_dotall.set(settings.get('flag_dotall', False))
        self.flag_unicode.set(settings.get('flag_unicode', True))
