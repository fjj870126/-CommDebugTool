"""组包面板 - 字段表格、校验配置、预览、发送"""

import json
import os
import random
import copy
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont
from packet.packet_builder import (
    PacketBuilder, PacketField,
    FIELD_TYPES, FIELD_TYPE_DATA, FIELD_TYPE_CHECKSUM, FIELD_TYPE_LENGTH
)
from packet.checksum import get_algorithm_names, get_algorithm_width
from utils.context_menu import add_entry_context_menu, add_combobox_context_menu
from ui.theme import get_theme


class _CellTooltip:
    """Treeview 单元格悬停提示，仅在内容完整显示不下时出现"""

    def __init__(self, tree: 'ttk.Treeview'):
        self.tree = tree
        self.tip = None
        self.label = None
        self._current_cell = None  # (row_id, col_id)
        self._after_id = None
        tree.bind('<Motion>', self._on_motion, add='+')
        tree.bind('<Leave>', lambda e: self._hide(), add='+')
        tree.bind('<ButtonPress>', lambda e: self._hide(), add='+')

    def _on_motion(self, event):
        region = self.tree.identify('region', event.x, event.y)
        if region != 'cell':
            self._hide()
            return
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            self._hide()
            return
        cell = (row_id, col_id)
        if cell == self._current_cell and self.tip is not None:
            return
        self._hide()
        self._current_cell = cell
        # 延迟弹出，避免频繁闪现
        self._after_id = self.tree.after(400,
                                          lambda: self._maybe_show(cell, event.x_root, event.y_root))

    def _maybe_show(self, cell, x_root, y_root):
        if cell != self._current_cell:
            return
        row_id, col_id = cell
        try:
            col_idx = int(col_id.replace('#', '')) - 1
            columns = self.tree['columns']
            if col_idx < 0 or col_idx >= len(columns):
                return
            values = self.tree.item(row_id, 'values')
            if col_idx >= len(values):
                return
            text = str(values[col_idx])
            if not text:
                return
            col_name = columns[col_idx]
            col_width = int(self.tree.column(col_name, 'width'))
            font = tkfont.nametofont('TkDefaultFont')
            text_width = font.measure(text)
            # 预留边距，超出则提示
            if text_width + 12 <= col_width:
                return
            self._show(text, x_root, y_root)
        except Exception:
            pass

    def _show(self, text, x_root, y_root):
        self.tip = tk.Toplevel(self.tree)
        self.tip.wm_overrideredirect(True)
        self.tip.attributes('-topmost', True)
        try:
            self.tip.tk.call('::tk::unsupported::MacWindowStyle', 'style',
                             self.tip._w, 'help', 'noActivates')
        except Exception:
            pass
        self.label = tk.Label(self.tip, text=text, justify=tk.LEFT,
                              background=get_theme().color('tooltip_bg'),
                              relief=tk.SOLID, borderwidth=1,
                              padx=6, pady=3)
        self.label.pack()
        self.tip.geometry(f'+{x_root + 12}+{y_root + 12}')

    def _hide(self):
        if self._after_id is not None:
            try:
                self.tree.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if self.tip is not None:
            try:
                self.tip.destroy()
            except Exception:
                pass
            self.tip = None
            self.label = None
        self._current_cell = None


class FieldEditDialog(tk.Toplevel):
    """字段编辑对话框"""

    def __init__(self, parent, title='编辑字段', field: PacketField = None,
                 field_names: list = None):
        super().__init__(parent)
        self.title(title)
        self.withdraw()  # 先隐藏，避免在左上角闪现后再跳到中间
        self.resizable(False, False)
        self.result = None
        self._field_names = field_names or []
        self.transient(parent)  # 设置为主窗口的临时窗口
        self.grab_set()  # 模态对话框，阻止操作主窗口
        
        # macOS 上保持窗口置顶的增强处理
        self.attributes('-topmost', True)
        self.after(100, self._keep_on_top)  # 延迟确保生效
        
        # 依靠 transient + grab_set 保证模态层级，不再绑定 FocusOut 抢回置顶
        # （避免 Combobox 下拉被刷新顶层推下去而隐藏）

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        # 字段名
        ttk.Label(frame, text='字段名:').grid(row=0, column=0, sticky=tk.W, pady=4)
        self.name_var = tk.StringVar(value=field.name if field else '新字段')
        self.name_entry = ttk.Entry(frame, textvariable=self.name_var, width=20)
        self.name_entry.grid(row=0, column=1, padx=(8, 0), pady=4)
        add_entry_context_menu(self.name_entry)

        # hex 值含义
        ttk.Label(frame, text='含义:').grid(row=7, column=0, sticky=tk.W, pady=4)
        self.desc_var = tk.StringVar(value=field.description if field else '')
        self.desc_entry = ttk.Entry(frame, textvariable=self.desc_var, width=20)
        self.desc_entry.grid(row=7, column=1, padx=(8, 0), pady=4, sticky=tk.EW)
        add_entry_context_menu(self.desc_entry)

        # 数值 (支持 Hex / Dec 切换)
        self.value_label = ttk.Label(frame, text='Hex值:')
        self.value_label.grid(row=1, column=0, sticky=tk.W, pady=4)
        value_frame = ttk.Frame(frame)
        value_frame.grid(row=1, column=1, padx=(8, 0), pady=4, sticky=tk.EW)
        self.hex_var = tk.StringVar(value=field.hex_value if field else '00')
        self.value_entry = ttk.Entry(value_frame, textvariable=self.hex_var, width=14)
        self.value_entry.pack(side=tk.LEFT)
        add_entry_context_menu(self.value_entry)
        self._input_mode = tk.StringVar(value='hex')
        ttk.Radiobutton(value_frame, text='Hex', variable=self._input_mode,
                         value='hex', command=self._on_mode_switch).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Radiobutton(value_frame, text='Dec', variable=self._input_mode,
                         value='dec', command=self._on_mode_switch).pack(side=tk.LEFT, padx=(2, 0))

        # 字节数
        ttk.Label(frame, text='字节数:').grid(row=2, column=0, sticky=tk.W, pady=4)
        self.count_var = tk.StringVar(value=str(field.byte_count if field else 1))
        ttk.Spinbox(frame, textvariable=self.count_var, from_=1, to=256,
                     width=8).grid(row=2, column=1, padx=(8, 0), pady=4, sticky=tk.W)

        # 类型
        ttk.Label(frame, text='类型:').grid(row=3, column=0, sticky=tk.W, pady=4)
        self.type_var = tk.StringVar(value=field.field_type if field else FIELD_TYPE_DATA)
        type_cb = ttk.Combobox(frame, textvariable=self.type_var, values=FIELD_TYPES,
                     state='readonly', width=10)
        type_cb.grid(row=3, column=1, padx=(8, 0), pady=4, sticky=tk.W)
        type_cb.bind('<<ComboboxSelected>>', self._on_type_change)
        add_combobox_context_menu(type_cb)

        # 长度字段专用配置区
        self.len_config_frame = ttk.LabelFrame(frame, text=' 长度计算配置 ', padding=6)
        self.len_config_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW,
                                   pady=(8, 0))

        range_options = [f'{i}: {n}' for i, n in enumerate(self._field_names)]

        r1 = ttk.Frame(self.len_config_frame)
        r1.pack(fill=tk.X, pady=2)
        ttk.Label(r1, text='计算起始:').pack(side=tk.LEFT)
        self.len_start_var = tk.StringVar()
        self.len_start_cb = ttk.Combobox(r1, textvariable=self.len_start_var,
                                          values=range_options, state='readonly', width=14)
        self.len_start_cb.pack(side=tk.LEFT, padx=(4, 0))
        add_combobox_context_menu(self.len_start_cb)

        r2 = ttk.Frame(self.len_config_frame)
        r2.pack(fill=tk.X, pady=2)
        ttk.Label(r2, text='计算结束:').pack(side=tk.LEFT)
        self.len_end_var = tk.StringVar()
        self.len_end_cb = ttk.Combobox(r2, textvariable=self.len_end_var,
                                        values=range_options, state='readonly', width=14)
        self.len_end_cb.pack(side=tk.LEFT, padx=(4, 0))
        add_combobox_context_menu(self.len_end_cb)

        r3 = ttk.Frame(self.len_config_frame)
        r3.pack(fill=tk.X, pady=2)
        ttk.Label(r3, text='字节序:').pack(side=tk.LEFT)
        self.len_endian_var = tk.StringVar(value='big')
        ttk.Radiobutton(r3, text='大端', variable=self.len_endian_var,
                         value='big').pack(side=tk.LEFT, padx=(4, 2))
        ttk.Radiobutton(r3, text='小端', variable=self.len_endian_var,
                         value='little').pack(side=tk.LEFT, padx=2)

        # 初始化长度配置值
        if field and field.field_type == FIELD_TYPE_LENGTH:
            if range_options and field.length_start < len(range_options):
                self.len_start_var.set(range_options[field.length_start])
            if range_options and field.length_end < len(range_options):
                self.len_end_var.set(range_options[field.length_end])
            self.len_endian_var.set(field.length_byte_order)
        elif range_options:
            self.len_start_var.set(range_options[0])
            self.len_end_var.set(range_options[-1])

        # 校验字段专用配置区
        self.chk_config_frame = ttk.LabelFrame(frame, text=' 校验配置 ', padding=6)
        self.chk_config_frame.grid(row=5, column=0, columnspan=2, sticky=tk.EW,
                                   pady=(8, 0))

        c1 = ttk.Frame(self.chk_config_frame)
        c1.pack(fill=tk.X, pady=2)
        ttk.Label(c1, text='校验算法:').pack(side=tk.LEFT)
        self.chk_algo_var = tk.StringVar(value='CRC16/MODBUS')
        self.chk_algo_cb = ttk.Combobox(c1, textvariable=self.chk_algo_var,
                                         values=get_algorithm_names(), state='readonly', width=16)
        self.chk_algo_cb.pack(side=tk.LEFT, padx=(4, 0))
        add_combobox_context_menu(self.chk_algo_cb)

        c2 = ttk.Frame(self.chk_config_frame)
        c2.pack(fill=tk.X, pady=2)
        ttk.Label(c2, text='校验起始:').pack(side=tk.LEFT)
        self.chk_start_var = tk.StringVar()
        self.chk_start_cb = ttk.Combobox(c2, textvariable=self.chk_start_var,
                                          values=range_options, state='readonly', width=14)
        self.chk_start_cb.pack(side=tk.LEFT, padx=(4, 0))
        add_combobox_context_menu(self.chk_start_cb)

        c3 = ttk.Frame(self.chk_config_frame)
        c3.pack(fill=tk.X, pady=2)
        ttk.Label(c3, text='校验结束:').pack(side=tk.LEFT)
        self.chk_end_var = tk.StringVar()
        self.chk_end_cb = ttk.Combobox(c3, textvariable=self.chk_end_var,
                                        values=range_options, state='readonly', width=14)
        self.chk_end_cb.pack(side=tk.LEFT, padx=(4, 0))
        add_combobox_context_menu(self.chk_end_cb)

        c4 = ttk.Frame(self.chk_config_frame)
        c4.pack(fill=tk.X, pady=2)
        ttk.Label(c4, text='字节序:').pack(side=tk.LEFT)
        self.chk_endian_var = tk.StringVar(value='big')
        ttk.Radiobutton(c4, text='大端', variable=self.chk_endian_var,
                         value='big').pack(side=tk.LEFT, padx=(4, 2))
        ttk.Radiobutton(c4, text='小端', variable=self.chk_endian_var,
                         value='little').pack(side=tk.LEFT, padx=2)

        # 初始化校验配置值
        if field and field.field_type == FIELD_TYPE_CHECKSUM:
            self.chk_algo_var.set(field.checksum_algorithm)
            if range_options and field.checksum_start < len(range_options):
                self.chk_start_var.set(range_options[field.checksum_start])
            if range_options and field.checksum_end < len(range_options):
                self.chk_end_var.set(range_options[field.checksum_end])
            self.chk_endian_var.set(field.checksum_byte_order)
        elif range_options:
            self.chk_start_var.set(range_options[0])
            if len(range_options) > 1:
                self.chk_end_var.set(range_options[-2])
            else:
                self.chk_end_var.set(range_options[0])

        self._on_type_change()

        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=8, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(btn_frame, text='确定', command=self._ok, width=8).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text='取消', command=self.destroy, width=8).pack(side=tk.LEFT, padx=4)

        # 居中后才显示，避免左上角闪现
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f'+{x}+{y}')
        self.deiconify()
        self.wait_window()

    def _on_mode_switch(self):
        """Hex / Dec 切换时转换当前输入值"""
        raw = self.hex_var.get().strip()
        mode = self._input_mode.get()
        if mode == 'dec':
            # hex -> dec
            self.value_label.config(text='Dec值:')
            try:
                val = int(raw, 16) if raw else 0
                self.hex_var.set(str(val))
            except ValueError:
                pass
        else:
            # dec -> hex
            self.value_label.config(text='Hex值:')
            try:
                val = int(raw) if raw else 0
                hex_str = format(val, 'X')
                if len(hex_str) % 2:
                    hex_str = '0' + hex_str
                self.hex_var.set(hex_str)
            except ValueError:
                pass

    def _get_hex_value(self) -> str:
        """获取当前输入值的 hex 表示（无论当前输入模式）"""
        raw = self.hex_var.get().strip().replace(' ', '')
        if self._input_mode.get() == 'dec':
            try:
                val = int(raw) if raw else 0
                hex_str = format(val, 'X')
                if len(hex_str) % 2:
                    hex_str = '0' + hex_str
                return hex_str
            except ValueError:
                return '00'
        return raw

    def _on_focus_out(self, event=None):
        """失去焦点时重新置顶（延迟检查，避免 Combobox 下拉受干扰）"""
        if not self.winfo_exists():
            return
        # 焦点切换是异步的，延迟一拍再决策
        self.after(80, self._maybe_reassert_topmost)

    def _maybe_reassert_topmost(self):
        if not self.winfo_exists():
            return
        try:
            focused = self.focus_get()
        except Exception:
            focused = None
        # 焦点仍在 Tk 内部（如 Combobox 下拉 listbox）→ 不要抢回置顶
        if focused is not None:
            return
        # 真正失焦到其他应用，才重新置顶
        self.lift()
        self.attributes('-topmost', True)
        self.after(50, lambda: self._restore_topmost())
    
    def _restore_topmost(self):
        """恢复置顶状态"""
        if self.winfo_exists():
            self.attributes('-topmost', False)
            self.after(50, lambda: self.attributes('-topmost', True))
    
    def _keep_on_top(self):
        """确保窗口保持在最上层"""
        if self.winfo_exists():
            self.lift()
            self.attributes('-topmost', True)
    
    def destroy(self):
        """销毁对话框"""
        try:
            self.grab_release()
        except:
            pass
        super().destroy()

    def _on_type_change(self, event=None):
        if self.type_var.get() == FIELD_TYPE_LENGTH:
            self.len_config_frame.grid()
        else:
            self.len_config_frame.grid_remove()
        
        if self.type_var.get() == FIELD_TYPE_CHECKSUM:
            self.chk_config_frame.grid()
        else:
            self.chk_config_frame.grid_remove()
        
        # 当类型从长度或校验切换为数据或固定值时，根据字节数设置默认 hex 值
        if self.type_var.get() in (FIELD_TYPE_DATA, '固定值'):
            current_hex = self.hex_var.get().strip()
            if not current_hex or current_hex == '(自动)':
                try:
                    byte_count = int(self.count_var.get())
                    # 根据字节数生成默认值，例如 2字节 -> "00 00"
                    self.hex_var.set(' '.join(['00'] * byte_count))
                except ValueError:
                    self.hex_var.set('00')

    @staticmethod
    def _parse_range_index(val: str) -> int:
        if not val:
            return 0
        try:
            return int(val.split(':')[0].strip())
        except (ValueError, IndexError):
            return 0

    def _ok(self):
        try:
            count = int(self.count_var.get())
        except ValueError:
            count = 1
        name = self.name_var.get().strip()
        if not name:
            name = '未命名'
        self.result = PacketField(
            name=name,
            hex_value=self._get_hex_value(),
            byte_count=count,
            field_type=self.type_var.get(),
            length_start=self._parse_range_index(self.len_start_var.get()),
            length_end=self._parse_range_index(self.len_end_var.get()),
            length_byte_order=self.len_endian_var.get(),
            checksum_algorithm=self.chk_algo_var.get(),
            checksum_start=self._parse_range_index(self.chk_start_var.get()),
            checksum_end=self._parse_range_index(self.chk_end_var.get()),
            checksum_byte_order=self.chk_endian_var.get(),
            description=self.desc_var.get().strip(),
        )
        self.destroy()


class PacketPanel(ttk.LabelFrame):
    def __init__(self, parent, on_send=None):
        super().__init__(parent, text=' 组包面板 ', padding=8)
        self._on_send = on_send
        self.builder = PacketBuilder()
        self._template_snapshot = None
        self._last_template_path = None  # 上次打开/保存的模板路径
        self._templates = {}  # 存储所有模板 {名称: 数据}
        self._current_template_name = None  # 当前选中的模板名称
        self._undo_stack = []  # 撤销栈，保存操作前的字段快照
        self._build_ui()
        self._load_default_template()

    def _build_ui(self):
        # 模板选择区域
        template_frame = ttk.Frame(self)
        template_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(template_frame, text='模板:').pack(side=tk.LEFT)
        self.template_var = tk.StringVar(value='默认模板')
        self.template_cb = ttk.Combobox(template_frame, textvariable=self.template_var,
                                        state='readonly', width=20)
        self.template_cb.pack(side=tk.LEFT, padx=(4, 4), fill=tk.X, expand=True)
        self.template_cb.bind('<<ComboboxSelected>>', self._on_template_change)
        add_combobox_context_menu(self.template_cb)

        ttk.Button(template_frame, text='新建', command=self._new_template, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(template_frame, text='重命名', command=self._rename_template, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(template_frame, text='删除', command=self._delete_template, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(template_frame, text='模板保存', command=self._save_template_as, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(template_frame, text='加载模板', command=self._load_template, width=8).pack(side=tk.LEFT, padx=2)

        # 上部: 表格 + 右侧按钮
        top = ttk.Frame(self)
        top.pack(fill=tk.BOTH, expand=True)

        # 右侧按钮区（先 pack 以锁定宽度，保证按钮始终完整可见）
        btn_frame = ttk.Frame(top)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))

        buttons = [
            ('添加字段', self._add_field),
            ('编辑字段', self._edit_field),
            ('删除字段', self._delete_field),
            ('上移', self._move_up),
            ('下移', self._move_down),
            ('清空', self._clear_fields),
            ('恢复', self._undo),
            ('默认模板', self._restore_default),
        ]
        for text, cmd in buttons:
            ttk.Button(btn_frame, text=text, command=cmd, width=10).pack(pady=2)

        # 字段表格（填充剩余区域）
        table_frame = ttk.Frame(top)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        columns = ('name', 'hex', 'bytes', 'type', 'desc')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                 selectmode='browse')
        self.tree.heading('name', text='字段名')
        self.tree.heading('hex', text='Hex值')
        self.tree.heading('bytes', text='字节数')
        self.tree.heading('type', text='类型')
        self.tree.heading('desc', text='含义')

        # stretch=False 保证调整某列宽度时不会联动其他列
        self.tree.column('name', width=100, minwidth=60, stretch=False)
        self.tree.column('hex', width=140, minwidth=80, stretch=False)
        self.tree.column('bytes', width=50, minwidth=40, anchor=tk.CENTER, stretch=False)
        self.tree.column('type', width=60, minwidth=50, anchor=tk.CENTER, stretch=False)
        self.tree.column('desc', width=160, minwidth=80, stretch=False)

        tree_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        tree_hscroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll.set, xscrollcommand=tree_hscroll.set)
        # 使用 grid 以同时安置水平/垂直滚动条
        self.tree.grid(row=0, column=0, sticky='nsew')
        tree_scroll.grid(row=0, column=1, sticky='ns')
        tree_hscroll.grid(row=1, column=0, sticky='ew')
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.bind('<Double-1>', self._on_double_click)

        # 列宽自适应划换的备份：{col: 划换前的宽度}
        self._auto_fit_prev_widths = {}

        # 悬停提示：内容被截断时弹出完整文本
        self._cell_tooltip = _CellTooltip(self.tree)

        # 下部: 预览 + 操作按钮
        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.X, pady=(8, 0))

        ttk.Label(bottom, text='组包预览:').pack(side=tk.LEFT)
        self.preview_var = tk.StringVar(value='(空)')
        self.preview_entry = ttk.Entry(bottom, textvariable=self.preview_var,
                                  state='readonly', font=('Courier New', 10))
        self.preview_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 8))
        add_entry_context_menu(self.preview_entry)

        btn_bar = ttk.Frame(bottom)
        btn_bar.pack(side=tk.RIGHT)
        ttk.Button(btn_bar, text='发送', command=self._do_send, width=8).pack(side=tk.LEFT, padx=2)

    # ============================================================
    # 快照 & 修改检测
    # ============================================================

    def _take_snapshot(self):
        self._sync_builder_config()
        self._template_snapshot = json.dumps(self.builder.to_dict(), sort_keys=True)

    def is_template_modified(self) -> bool:
        if self._template_snapshot is None:
            return False
        self._sync_builder_config()
        current = json.dumps(self.builder.to_dict(), sort_keys=True)
        return current != self._template_snapshot

    # ============================================================
    # 默认模板
    # ============================================================

    def _make_range_label(self, idx: int) -> str:
        if 0 <= idx < len(self.builder.fields):
            return f'{idx}: {self.builder.fields[idx].name}'
        return str(idx)

    def _load_default_template(self):
        self.builder.fields = [
            PacketField('帧头', 'AA55', 2, '固定值', description='协议起始标志'),
            PacketField('命令字', '01', 1, '数据', description='功能码'),
            PacketField('数据长度', '', 1, '长度', length_start=3, length_end=3, length_byte_order='big',
                       description='数据区长度'),
            PacketField('数据', '00', 1, '数据', description='业务数据'),
            PacketField('CRC校验', '', 2, '校验',
                       checksum_algorithm='CRC16/MODBUS',
                       checksum_start=0, checksum_end=3,
                       checksum_byte_order='little',
                       description='CRC16/MODBUS 校验值'),
        ]
        self._refresh_tree()
        self._update_preview()
        self._take_snapshot()
        # 添加到模板列表
        self._templates['默认模板'] = self.builder.to_dict()
        self._current_template_name = '默认模板'
        self._update_template_list()

    # ============================================================
    # 表格刷新 & 范围选项
    # ============================================================

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        # 尝试计算整个数据包，用于获取长度/校验字段的真实值
        try:
            packet = self.builder.build_packet()
        except Exception:
            packet = None
        
        from utils.hex_utils import bytes_to_hex_str
        
        offset = 0
        for i, f in enumerate(self.builder.fields):
            if f.field_type in (FIELD_TYPE_CHECKSUM, FIELD_TYPE_LENGTH):
                # 在(自动)后面显示真实计算值
                if packet is not None and offset + f.byte_count <= len(packet):
                    real_bytes = packet[offset:offset + f.byte_count]
                    hex_display = f'(自动) {bytes_to_hex_str(real_bytes)}'
                else:
                    hex_display = '(自动)'
            else:
                hex_display = f.get_hex_display()
            
            self.tree.insert('', tk.END, iid=str(i), values=(
                f.name, hex_display, f.byte_count, f.field_type,
                f.description,
            ))
            offset += f.byte_count
        self._update_range_options()

    def _update_range_options(self):
        # 校验范围已经移到各个校验字段中，不需要更新全局的范围选项
        pass

    @staticmethod
    def _parse_range_index(val: str) -> int:
        if not val:
            return 0
        try:
            return int(val.split(':')[0].strip())
        except (ValueError, IndexError):
            return 0

    def _update_template_list(self):
        """更新模板下拉框列表"""
        template_names = list(self._templates.keys())
        self.template_cb['values'] = template_names
        if self._current_template_name and self._current_template_name in template_names:
            self.template_var.set(self._current_template_name)
        elif template_names:
            self.template_var.set(template_names[0])
            self._current_template_name = template_names[0]

    def _on_template_change(self, event=None):
        """模板切换事件"""
        selected = self.template_var.get()
        if selected and selected in self._templates:
            # 保存当前模板的修改
            if self._current_template_name:
                self._sync_builder_config()
                self._templates[self._current_template_name] = self.builder.to_dict()
            
            # 加载选中的模板
            self._load_template_data(self._templates[selected])
            self._current_template_name = selected

    def _load_template_data(self, template_data: dict):
        """加载模板数据到界面"""
        try:
            self.builder = PacketBuilder.from_dict(template_data)
            self._refresh_tree()
            self._update_preview()
            self._take_snapshot()
        except Exception as e:
            messagebox.showerror('加载失败', str(e))

    def _new_template(self):
        """新建模板"""
        # 先保存当前模板
        if self._current_template_name:
            self._sync_builder_config()
            self._templates[self._current_template_name] = self.builder.to_dict()
        
        # 弹出对话框输入模板名称
        dialog = tk.Toplevel(self)
        dialog.title('新建模板')
        dialog.withdraw()  # 先隐藏，避免在左上角闪现
        dialog.resizable(False, False)
        dialog.transient(self)  # 设置为主窗口的临时窗口
        dialog.grab_set()  # 模态对话框
        dialog.attributes('-topmost', True)  # 始终显示在最上层
        dialog.after(100, lambda: dialog.attributes('-topmost', True))  # 延迟确保生效
        
        # 依靠 transient + grab_set 保证模态层级，不再绑定 FocusOut 抢回置顶
        # （避免 Combobox 下拉被刷新顶层推下去而隐藏）
        
        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text='模板名称:').pack(anchor=tk.W, pady=(0, 4))
        name_var = tk.StringVar()
        name_entry = ttk.Entry(frame, textvariable=name_var, width=25)
        name_entry.pack(fill=tk.X, pady=(0, 12))
        add_entry_context_menu(name_entry)
        
        # 添加复制模板选项
        ttk.Label(frame, text='复制现有模板:').pack(anchor=tk.W, pady=(0, 4))
        copy_var = tk.StringVar(value='不复制（使用默认模板）')
        template_names = ['不复制（使用默认模板）'] + list(self._templates.keys())
        copy_cb = ttk.Combobox(frame, textvariable=copy_var, values=template_names,
                               state='readonly', width=30)
        copy_cb.pack(fill=tk.X, pady=(0, 12))
        add_combobox_context_menu(copy_cb)
        
        # 当选择复制模板时，自动生成默认名称
        def on_copy_change(event=None):
            selected = copy_var.get()
            if selected == '不复制（使用默认模板）':
                name_var.set('')
            else:
                # 生成随机后缀
                random_suffix = random.randint(1000, 9999)
                new_name = f"{selected}_{random_suffix}"
                name_var.set(new_name)
        
        copy_cb.bind('<<ComboboxSelected>>', on_copy_change)
        
        def on_ok():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning('提示', '请输入模板名称')
                return
            if name in self._templates:
                messagebox.showwarning('提示', f'模板 "{name}" 已存在')
                return
            
            # 根据选择创建新模板
            selected_template = copy_var.get()
            if selected_template == '不复制（使用默认模板）':
                # 使用默认模板数据
                self._load_default_template()
            else:
                # 复制选中的模板
                self._load_template_data(self._templates[selected_template])
            
            self._current_template_name = name
            self._templates[name] = self.builder.to_dict()
            self._update_template_list()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # 绑定回车键
        name_entry.bind('<Return>', lambda e: on_ok())
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text='确定', command=on_ok, width=8).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text='取消', command=on_cancel, width=8).pack(side=tk.LEFT, padx=4)
        
        # 居中后才显示
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f'+{x}+{y}')
        dialog.deiconify()
        name_entry.focus()
        dialog.wait_window()

    def _delete_template(self):
        """删除模板"""
        if not self._current_template_name:
            messagebox.showwarning('提示', '没有可删除的模板')
            return
        
        if self._current_template_name == '默认模板':
            messagebox.showwarning('提示', '不能删除默认模板')
            return
        
        # 确认删除
        if not messagebox.askyesno('确认删除', f'确定要删除模板 "{self._current_template_name}" 吗？'):
            return
        
        # 删除模板
        del self._templates[self._current_template_name]
        
        # 切换到默认模板
        if '默认模板' in self._templates:
            self._current_template_name = '默认模板'
            self._load_template_data(self._templates['默认模板'])
        elif self._templates:
            # 如果没有默认模板，选择第一个
            first_name = list(self._templates.keys())[0]
            self._current_template_name = first_name
            self._load_template_data(self._templates[first_name])
        else:
            # 如果所有模板都被删除，重新创建默认模板
            self._load_default_template()
        
        self._update_template_list()

    def _rename_template(self):
        """重命名当前模板"""
        if not self._current_template_name:
            messagebox.showwarning('提示', '没有可重命名的模板')
            return
        
        # 弹出对话框输入新名称
        dialog = tk.Toplevel(self)
        dialog.title('重命名模板')
        dialog.withdraw()  # 先隐藏，避免在左上角闪现
        dialog.resizable(False, False)
        dialog.transient(self)  # 设置为主窗口的临时窗口
        dialog.grab_set()  # 模态对话框
        dialog.attributes('-topmost', True)  # 始终显示在最上层
        dialog.after(100, lambda: dialog.attributes('-topmost', True))  # 延迟确保生效
        
        # 依靠 transient + grab_set 保证模态层级，不再绑定 FocusOut 抢回置顶
        
        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text='当前名称:').pack(anchor=tk.W, pady=(0, 4))
        ttk.Label(frame, text=self._current_template_name, foreground='gray').pack(anchor=tk.W, pady=(0, 12))
        
        ttk.Label(frame, text='新名称:').pack(anchor=tk.W, pady=(0, 4))
        name_var = tk.StringVar(value=self._current_template_name)
        name_entry = ttk.Entry(frame, textvariable=name_var, width=25)
        name_entry.pack(fill=tk.X, pady=(0, 12))
        name_entry.select_range(0, tk.END)
        name_entry.focus()
        add_entry_context_menu(name_entry)
        
        def on_ok():
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showwarning('提示', '请输入模板名称')
                return
            if new_name == self._current_template_name:
                messagebox.showinfo('提示', '名称未改变')
                dialog.destroy()
                return
            if new_name in self._templates:
                messagebox.showwarning('提示', f'模板 "{new_name}" 已存在')
                return
            
            # 重命名模板
            self._templates[new_name] = self._templates.pop(self._current_template_name)
            self._current_template_name = new_name
            self._update_template_list()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # 绑定回车键
        name_entry.bind('<Return>', lambda e: on_ok())
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text='确定', command=on_ok, width=8).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text='取消', command=on_cancel, width=8).pack(side=tk.LEFT, padx=4)
        
        # 居中后才显示
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f'+{x}+{y}')
        dialog.deiconify()
        dialog.wait_window()

    def _sync_builder_config(self):
        # 校验配置已经移到各个字段中，不需要同步全局配置
        pass

    def _update_preview(self):
        self._sync_builder_config()
        if not self.builder.fields:
            self.preview_var.set('(空)')
            return
        try:
            preview = self.builder.get_preview()
            self.preview_var.set(preview)
            self._refresh_tree()
        except Exception as e:
            self.preview_var.set(f'错误: {e}')

    # ============================================================
    # 字段操作
    # ============================================================

    def _get_selected_index(self) -> int:
        sel = self.tree.selection()
        if not sel:
            return -1
        return int(sel[0])

    def _get_field_names(self) -> list:
        return [f.name for f in self.builder.fields]

    def _add_field(self):
        dlg = FieldEditDialog(self.winfo_toplevel(), title='添加字段',
                              field_names=self._get_field_names())
        if dlg.result:
            self._push_undo()
            idx = self._get_selected_index()
            if idx >= 0:
                insert_pos = idx + 1
                self.builder.insert_field(insert_pos, dlg.result)
            else:
                insert_pos = len(self.builder.fields) - 1
                self.builder.add_field(dlg.result)
            self._refresh_tree()
            self._update_preview()
            self.tree.selection_set(str(insert_pos))
            self.tree.focus(str(insert_pos))

    def _edit_field(self):
        idx = self._get_selected_index()
        if idx < 0:
            return
        field = self.builder.fields[idx]
        dlg = FieldEditDialog(self.winfo_toplevel(), title='编辑字段', field=field,
                              field_names=self._get_field_names())
        if dlg.result:
            self._push_undo()
            self.builder.fields[idx] = dlg.result
            self._refresh_tree()
            self._update_preview()
            self.tree.selection_set(str(idx))
            self.tree.focus(str(idx))

    def _on_double_click(self, event):
        region = self.tree.identify('region', event.x, event.y)
        if region == 'heading':
            col_id = self.tree.identify_column(event.x)
            self._toggle_auto_fit_column(col_id)
            return 'break'
        if region == 'separator':
            return
        self._edit_field()

    def _toggle_auto_fit_column(self, col_id: str):
        """双击列头：首次按最大内容自适应，再次恢复之前的宽度"""
        try:
            col_idx = int(col_id.replace('#', '')) - 1
        except ValueError:
            return
        columns = self.tree['columns']
        if col_idx < 0 or col_idx >= len(columns):
            return
        col_name = columns[col_idx]
        # 已经是自适应状态 → 恢复
        if col_name in self._auto_fit_prev_widths:
            try:
                self.tree.column(col_name, width=int(self._auto_fit_prev_widths[col_name]))
            except (ValueError, TypeError):
                pass
            del self._auto_fit_prev_widths[col_name]
            return
        # 备份当前宽度后计算自适应宽度
        try:
            current_width = int(self.tree.column(col_name, 'width'))
        except (ValueError, TypeError):
            current_width = 100
        try:
            min_width = int(self.tree.column(col_name, 'minwidth'))
        except (ValueError, TypeError):
            min_width = 40
        try:
            font = tkfont.nametofont('TkDefaultFont')
        except Exception:
            font = tkfont.Font()
        # 取列头与所有行文本的最大宽度
        try:
            heading_text = str(self.tree.heading(col_name).get('text') or '')
        except Exception:
            heading_text = ''
        max_text_width = font.measure(heading_text)
        for row_id in self.tree.get_children():
            values = self.tree.item(row_id, 'values')
            if col_idx < len(values):
                w = font.measure(str(values[col_idx]))
                if w > max_text_width:
                    max_text_width = w
        # 预留边距
        new_width = max(min_width, max_text_width + 16)
        self._auto_fit_prev_widths[col_name] = current_width
        try:
            self.tree.column(col_name, width=new_width)
        except (ValueError, TypeError):
            pass

    def _delete_field(self):
        idx = self._get_selected_index()
        if idx < 0:
            return
        self._push_undo()
        self.builder.remove_field(idx)
        self._refresh_tree()
        self._update_preview()
        if self.builder.fields:
            new_idx = min(idx, len(self.builder.fields) - 1)
            self.tree.selection_set(str(new_idx))
            self.tree.focus(str(new_idx))

    def _move_up(self):
        idx = self._get_selected_index()
        if idx < 1:
            return
        self._push_undo()
        self.builder.move_field_up(idx)
        self._refresh_tree()
        self._update_preview()
        new_idx = idx - 1
        self.tree.selection_set(str(new_idx))
        self.tree.focus(str(new_idx))

    def _move_down(self):
        idx = self._get_selected_index()
        if idx < 0 or idx >= len(self.builder.fields) - 1:
            return
        self._push_undo()
        self.builder.move_field_down(idx)
        self._refresh_tree()
        self._update_preview()
        new_idx = idx + 1
        self.tree.selection_set(str(new_idx))
        self.tree.focus(str(new_idx))

    def _clear_fields(self):
        """清空表格所有字段"""
        if not self.builder.fields:
            return
        if not messagebox.askyesno('确认清空', '确定要清空所有字段吗？'): 
            return
        self._push_undo()
        self.builder.fields.clear()
        self._refresh_tree()
        self._update_preview()

    def _push_undo(self):
        """将当前字段状态压入撤销栈"""
        self._undo_stack.append(copy.deepcopy(self.builder.fields))
        # 限制栈深度，最多保留 20 步
        if len(self._undo_stack) > 20:
            self._undo_stack.pop(0)

    def _undo(self):
        """恢复上一次操作"""
        if not self._undo_stack:
            messagebox.showinfo('提示', '没有可恢复的操作')
            return
        self.builder.fields = self._undo_stack.pop()
        self._refresh_tree()
        self._update_preview()

    def _restore_default(self):
        """将当前模板恢复为默认模板的字段数据"""
        if self.builder.fields:
            if not messagebox.askyesno('确认恢复', '确定要恢复为默认模板吗？当前数据将丢失。'):
                return
        
        self._push_undo()
        # 恢复为默认字段数据
        from packet.packet_builder import PacketField
        self.builder.fields = [
            PacketField('帧头', 'AA55', 2, '固定值', description='协议起始标志'),
            PacketField('命令字', '01', 1, '数据', description='功能码'),
            PacketField('数据长度', '', 1, '长度', length_start=3, length_end=3, length_byte_order='big',
                       description='数据区长度'),
            PacketField('数据', '00', 1, '数据', description='业务数据'),
            PacketField('CRC校验', '', 2, '校验',
                       checksum_algorithm='CRC16/MODBUS',
                       checksum_start=0, checksum_end=3,
                       checksum_byte_order='little',
                       description='CRC16/MODBUS 校验值'),
        ]
        self._refresh_tree()
        self._update_preview()
        # 更新当前模板的数据
        if self._current_template_name:
            self._templates[self._current_template_name] = self.builder.to_dict()

    # ============================================================
    # 发送 & 模板
    # ============================================================

    def _do_send(self):
        if self._on_send:
            self._sync_builder_config()
            try:
                packet = self.builder.build_packet()
                self._on_send(packet)
            except Exception as e:
                messagebox.showerror('发送错误', str(e))

    def _save_template(self):
        """保存模板到当前选中的模板"""
        self._sync_builder_config()
        if self._current_template_name:
            self._templates[self._current_template_name] = self.builder.to_dict()
            self._take_snapshot()
            messagebox.showinfo('成功', f'模板 "{self._current_template_name}" 已保存')
        else:
            messagebox.showwarning('提示', '请先选择一个模板')

    def _save_template_as(self):
        """另存为模板文件"""
        self._sync_builder_config()
        
        # 默认文件名优先取当前模板名，没有才退回上次路径的文件名
        init_file = ''
        init_dir = None
        if self._current_template_name:
            init_file = f'{self._current_template_name}.json'
        if self._last_template_path:
            init_dir = os.path.dirname(self._last_template_path)
            if not init_file:
                init_file = os.path.basename(self._last_template_path)
        kwargs = {
            'defaultextension': '.json',
            'filetypes': [('JSON文件', '*.json'), ('所有文件', '*.*')],
            'title': '另存为组包模板',
        }
        if init_file:
            kwargs['initialfile'] = init_file
        if init_dir:
            kwargs['initialdir'] = init_dir
        filepath = filedialog.asksaveasfilename(**kwargs)
        if filepath:
            try:
                # 保存当前模板的完整数据（包括所有字段和配置）
                template_data = self.builder.to_dict()
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(template_data, f, ensure_ascii=False, indent=2)
                self._last_template_path = filepath
                self._take_snapshot()
                messagebox.showinfo('成功', f'模板已保存到:\n{filepath}')
            except Exception as e:
                messagebox.showerror('保存失败', str(e))

    def save_template_to_file(self):
        """保存模板到文件"""
        init_file = ''
        init_dir = None
        if self._last_template_path:
            init_dir = os.path.dirname(self._last_template_path)
            init_file = os.path.basename(self._last_template_path)
        kwargs = {
            'defaultextension': '.json',
            'filetypes': [('JSON文件', '*.json'), ('所有文件', '*.*')],
            'title': '保存组包模板',
        }
        if init_file:
            kwargs['initialfile'] = init_file
        if init_dir:
            kwargs['initialdir'] = init_dir
        filepath = filedialog.asksaveasfilename(**kwargs)
        if filepath:
            self._sync_builder_config()
            try:
                self.builder.save_template(filepath)
                self._last_template_path = filepath
                self._take_snapshot()
                messagebox.showinfo('成功', '模板已保存')
            except Exception as e:
                messagebox.showerror('保存失败', str(e))

    def save_template_to(self, filepath: str):
        """保存模板到指定文件（供 main_window 调用）"""
        self._sync_builder_config()
        self.builder.save_template(filepath)
        self._last_template_path = filepath
        self._take_snapshot()

    def _load_template(self):
        kwargs = {
            'filetypes': [('JSON文件', '*.json'), ('所有文件', '*.*')],
            'title': '加载组包模板',
        }
        if self._last_template_path:
            kwargs['initialdir'] = os.path.dirname(self._last_template_path)
        filepath = filedialog.askopenfilename(**kwargs)
        if filepath:
            self._load_template_from(filepath)

    def _load_template_from(self, filepath: str):
        """从文件加载模板"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
            
            # 从文件名获取模板名
            template_name = os.path.splitext(os.path.basename(filepath))[0]
            
            # 如果已存在，添加序号
            if template_name in self._templates:
                i = 1
                while f'{template_name}_{i}' in self._templates:
                    i += 1
                template_name = f'{template_name}_{i}'
            
            self._templates[template_name] = template_data
            self._current_template_name = template_name
            self._last_template_path = filepath
            self._load_template_data(template_data)
            self._update_template_list()
        except Exception as e:
            messagebox.showerror('加载失败', str(e))

    # ============================================================
    # 配置保存/恢复（供 main_window 调用）
    # ============================================================

    def _get_column_widths(self) -> dict:
        widths = {}
        try:
            for col in self.tree['columns']:
                widths[col] = int(self.tree.column(col, 'width'))
        except Exception:
            pass
        return widths

    def _apply_column_widths(self, widths: dict):
        if not widths:
            return
        try:
            for col in self.tree['columns']:
                if col in widths:
                    try:
                        self.tree.column(col, width=int(widths[col]))
                    except (ValueError, TypeError):
                        pass
        except Exception:
            pass

    def get_settings(self) -> dict:
        self._sync_builder_config()
        # 保存当前模板的修改
        if self._current_template_name:
            self._templates[self._current_template_name] = self.builder.to_dict()
        return {
            'templates': self._templates,
            'current_template_name': self._current_template_name or '',
            'last_template_path': self._last_template_path or '',
            'column_widths': self._get_column_widths(),
        }

    def load_settings(self, settings: dict):
        if not settings:
            return
        self._last_template_path = settings.get('last_template_path') or None

        # 恢复列宽
        self._apply_column_widths(settings.get('column_widths') or {})
        
        # 加载模板列表
        templates = settings.get('templates')
        if templates:
            self._templates = templates
        
        # 加载当前选中的模板
        current_name = settings.get('current_template_name')
        if current_name and current_name in self._templates:
            self._current_template_name = current_name
            self._load_template_data(self._templates[current_name])
        elif self._templates:
            # 如果没有找到上次选中的模板，选择第一个
            first_name = list(self._templates.keys())[0]
            self._current_template_name = first_name
            self._load_template_data(self._templates[first_name])
        else:
            # 如果没有模板，使用默认模板
            self._load_default_template()
        
        self._update_template_list()

    def get_packet_data(self) -> bytes:
        self._sync_builder_config()
        return self.builder.build_packet()
