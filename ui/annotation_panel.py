"""备注标注面板 - 在日志中添加备注标记"""

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from datetime import datetime
from utils.context_menu import add_entry_context_menu


class AnnotationPanel(ttk.LabelFrame):
    """备注标注面板"""

    def __init__(self, parent, log_panel=None):
        super().__init__(parent, text=' 备注标注 ', padding=8)
        self._log_panel = log_panel
        self._annotations = []  # [(timestamp, text, color)]
        self._build_ui()

    def _build_ui(self):
        # 备注输入
        input_frame = ttk.Frame(self)
        input_frame.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(input_frame, text='备注内容:').pack(anchor=tk.W)
        self.text_var = tk.StringVar()
        self.text_entry = ttk.Entry(input_frame, textvariable=self.text_var,
                                    font=('', 10))
        self.text_entry.pack(fill=tk.X, pady=(2, 4))
        self.text_entry.bind('<Return>', lambda e: self._add_annotation())
        add_entry_context_menu(self.text_entry)

        # 操作按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(0, 4))

        ttk.Button(btn_frame, text='📝 添加备注', command=self._add_annotation, width=10).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text='🎨 颜色', command=self._choose_color, width=6).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(btn_frame, text='🗑 清空', command=self._clear_annotations, width=6).pack(side=tk.LEFT, padx=(4, 0))

        # 颜色预览
        self.color_var = tk.StringVar(value='#2196F3')
        self.color_preview = tk.Canvas(btn_frame, width=20, height=20,
                                       bg=self.color_var.get(), highlightthickness=1,
                                       highlightbackground='gray')
        self.color_preview.pack(side=tk.LEFT, padx=(8, 0))

        # 快速备注按钮
        quick_frame = ttk.LabelFrame(self, text=' 快速备注 ', padding=4)
        quick_frame.pack(fill=tk.X, pady=(0, 4))

        quick_notes = ['开始测试', '结束测试', '异常数据', '正常通信', '配置变更', '重启设备']
        for note in quick_notes:
            btn = ttk.Button(quick_frame, text=note, width=10,
                           command=lambda n=note: self._quick_add(n))
            btn.pack(side=tk.LEFT, padx=1, pady=1)

        # 备注列表
        list_frame = ttk.LabelFrame(self, text=' 备注历史 ', padding=4)
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('time', 'text')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=5)
        self.tree.heading('time', text='时间')
        self.tree.heading('text', text='备注内容')

        self.tree.column('time', width=80, minwidth=60)
        self.tree.column('text', width=200, minwidth=100)

        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        tree_scroll.grid(row=0, column=1, sticky='ns')
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.tree.bind('<Double-Button-1>', self._on_double_click)

    def _add_annotation(self):
        """添加备注"""
        text = self.text_var.get().strip()
        if not text:
            messagebox.showwarning('提示', '请输入备注内容')
            return

        timestamp = datetime.now().strftime('%H:%M:%S')
        color = self.color_var.get()

        self._annotations.append((timestamp, text, color))
        self._add_to_tree(timestamp, text, color)

        # 添加到日志
        if self._log_panel:
            self._log_panel.log_info(f'[备注] {text}')

        self.text_var.set('')
        self.text_entry.focus()

    def _quick_add(self, text: str):
        """快速添加备注"""
        self.text_var.set(text)
        self._add_annotation()

    def _choose_color(self):
        """选择颜色"""
        color = colorchooser.askcolor(title='选择备注颜色', initialcolor=self.color_var.get())
        if color and color[1]:
            self.color_var.set(color[1])
            self.color_preview.configure(bg=color[1])

    def _add_to_tree(self, timestamp: str, text: str, color: str):
        """添加到列表"""
        item_id = self.tree.insert('', tk.END, values=(timestamp, text))
        # 设置颜色标签
        self.tree.tag_configure(f'color_{item_id}', foreground=color)
        self.tree.item(item_id, tags=(f'color_{item_id}',))
        self.tree.see(item_id)

    def _on_double_click(self, event):
        """双击删除备注"""
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        values = self.tree.item(item_id, 'values')
        if messagebox.askyesno('确认', f'删除备注 "{values[1]}"？'):
            # 从数据中删除
            for i, (ts, text, color) in enumerate(self._annotations):
                if ts == values[0] and text == values[1]:
                    self._annotations.pop(i)
                    break
            self.tree.delete(item_id)

    def _clear_annotations(self):
        """清空所有备注"""
        if not self._annotations:
            return
        if messagebox.askyesno('确认', '确定要清空所有备注吗？'):
            self._annotations.clear()
            for item in self.tree.get_children():
                self.tree.delete(item)

    def get_annotations(self) -> list:
        """获取所有备注"""
        return self._annotations

    def get_settings(self) -> dict:
        return {
            'annotations': self._annotations,
            'color': self.color_var.get(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        self._annotations = settings.get('annotations', [])
        self.color_var.set(settings.get('color', '#2196F3'))
        self.color_preview.configure(bg=self.color_var.get())
        for ts, text, color in self._annotations:
            self._add_to_tree(ts, text, color)
