"""终端面板 - 虚拟终端，支持命令行交互、ANSI 转义序列解析"""
import tkinter as tk
from tkinter import ttk
from utils.hex_utils import bytes_to_hex_str
from utils.context_menu import add_entry_context_menu
import re

ANSI_RE = re.compile(r'\x1b\[([0-9;]*)m')
ANSI_COLORS = {
    '30':'#000000','31':'#AA0000','32':'#00AA00','33':'#AA5500',
    '34':'#0000AA','35':'#AA00AA','36':'#00AAAA','37':'#AAAAAA',
}
ANSI_BG = {'40':'#000000','41':'#AA0000','42':'#00AA00','43':'#AA5500',
           '44':'#0000AA','45':'#AA00AA','46':'#00AAAA','47':'#AAAAAA'}

class AnsiParser:
    def __init__(self):
        self._fg = self._bg = None
        self._bold = False
    def reset(self):
        self._fg = self._bg = None
        self._bold = False
    def parse(self, text):
        segs = []; last = 0
        for m in ANSI_RE.finditer(text):
            if m.start() > last:
                segs.append((text[last:m.start()], self._tags()))
            self._apply(m.group(1)); last = m.end()
        if last < len(text):
            segs.append((text[last:], self._tags()))
        return segs
    def _tags(self):
        d = {}
        if self._fg: d['foreground'] = self._fg
        if self._bg: d['background'] = self._bg
        if self._bold: d['font'] = ('Consolas', 10, 'bold')
        return d or None
    def _apply(self, p):
        if not p: self.reset(); return
        for x in p.split(';'):
            x = x.strip()
            if not x: continue
            if x == '0': self.reset()
            elif x == '1': self._bold = True
            elif x == '22': self._bold = False
            elif x in ANSI_COLORS: self._fg = ANSI_COLORS[x]
            elif x in ANSI_BG: self._bg = ANSI_BG[x]

CS = {'绿底黑字':{'bg':'#000000','fg':'#00FF00','ic':'#00FF00'},
      '白底黑字':{'bg':'#000000','fg':'#FFFFFF','ic':'#FFFFFF'},
      '经典黑白':{'bg':'#FFFFFF','fg':'#000000','ic':'#000000'},
      '深色主题':{'bg':'#1E1E1E','fg':'#D4D4D4','ic':'#D4D4D4'}}

class TerminalPanel(ttk.LabelFrame):
    def __init__(self, parent, on_send=None):
        super().__init__(parent, text=' 终端 ', padding=6)
        self._on_send = on_send
        self._ansi = True; self._dmode = 'ascii'; self._cs_name = '绿底黑字'
        self._hist = []; self._hi = -1; self._max_history = 100; self._shortcuts = []
        self._ap = AnsiParser(); self._max_lines = 5000; self._log = None; self._tag_count = 0; self._auto_scroll = True
        self._build()

    def _build(self):
        # 工具栏
        tb = ttk.Frame(self); tb.pack(fill=tk.X, pady=(0,4))
        ttk.Button(tb, text='清屏', command=self._clear, width=6).pack(side=tk.LEFT, padx=(0,2))
        ttk.Button(tb, text='录制...', command=self._toggle_recording, width=8).pack(side=tk.LEFT, padx=(0,2))
        ttk.Button(tb, text='发送HEX', command=self._hex_dialog, width=10).pack(side=tk.LEFT, padx=(0,2))
        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        ttk.Label(tb, text='显示:').pack(side=tk.LEFT)
        self._display_var = tk.StringVar(value='ASCII')
        dm = ttk.Combobox(tb, textvariable=self._display_var, values=['ASCII','HEX'], state='readonly', width=6)
        dm.pack(side=tk.LEFT, padx=(2,6))
        dm.bind('<<ComboboxSelected>>', lambda e: setattr(self,'_dmode','hex' if self._display_var.get()=='HEX' else 'ascii'))
        self._ansi_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tb, text='ANSI', variable=self._ansi_var, command=lambda: setattr(self,'_ansi',self._ansi_var.get())).pack(side=tk.LEFT, padx=(0,6))
        self._echo_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(tb, text='回显', variable=self._echo_var).pack(side=tk.LEFT, padx=(0,6))
        ttk.Label(tb, text='换行:').pack(side=tk.LEFT)
        self._line_mode_var = tk.StringVar(value='CR+LF')
        ttk.Combobox(tb, textvariable=self._line_mode_var, values=['CR','LF','CR+LF','无'], state='readonly', width=6).pack(side=tk.LEFT, padx=(2,4))
        ttk.Label(tb, text='配色:').pack(side=tk.LEFT)
        self._cs_var = tk.StringVar(value='绿底黑字')
        cc = ttk.Combobox(tb, textvariable=self._cs_var, values=list(CS.keys()), state='readonly', width=10)
        cc.pack(side=tk.LEFT, padx=(2,0))
        cc.bind('<<ComboboxSelected>>', lambda e: self._apply_color_scheme())

        # 终端输出区
        of = ttk.LabelFrame(self, text=' 终端输出 ', padding=2); of.pack(fill=tk.BOTH, expand=True, pady=(0,4))
        c = CS[self._cs_name]
        self._out = tk.Text(of, height=12, width=80, font=('Consolas',10),
            bg=c['bg'], fg=c['fg'], insertbackground=c['ic'], relief=tk.FLAT, borderwidth=1,
            wrap=tk.CHAR, state=tk.NORMAL, highlightthickness=0, padx=4, pady=4)
        self._out.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sy = ttk.Scrollbar(of, orient=tk.VERTICAL, command=self._on_scroll); sy.pack(side=tk.RIGHT, fill=tk.Y)
        self._out.config(yscrollcommand=sy.set)
        self._out.bind('<Key>', lambda e: 'break'); self._out.bind('<Button-3>', self._context_menu)

        # 快捷命令栏
        sf = ttk.LabelFrame(self, text=' 快捷命令 ', padding=2); sf.pack(fill=tk.X, pady=(0,4))
        sb = ttk.Frame(sf); sb.pack(fill=tk.X, padx=2, pady=2)
        ttk.Button(sb, text='+添加', command=self._add_shortcut, width=6).pack(side=tk.LEFT, padx=(0,4))
        self._sc_container = ttk.Frame(sb); self._sc_container.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._refresh_shortcuts()

        # 输入行
        i_f = ttk.Frame(self); i_f.pack(fill=tk.X)
        ttk.Label(i_f, text='>', font=('Consolas',11,'bold')).pack(side=tk.LEFT, padx=(0,4))
        self._input_var = tk.StringVar()
        self._input_entry = ttk.Entry(i_f, textvariable=self._input_var, font=('Consolas',11))
        self._input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,4))
        add_entry_context_menu(self._input_entry)
        self._input_entry.bind('<Return>', self._on_enter)
        self._input_entry.bind('<Up>', self._on_history_up)
        self._input_entry.bind('<Down>', self._on_history_down)
        self._input_entry.bind('<Control-l>', lambda e: self._clear())
        self._input_entry.bind('<Control-u>', lambda e: (self._input_var.set(''), self._input_entry.icursor(tk.END)))
        self._input_entry.bind('<Control-c>', lambda e: self._on_send and self._on_send(b'\x03'))
        ttk.Button(i_f, text='发送', command=self._send, width=6).pack(side=tk.LEFT)
        self.after(100, lambda: self._input_entry.focus_set())

    def _on_scroll(self, *a):
        self._out.yview(*a)
        try: t,b = self._out.yview(); self._auto_scroll = b >= 0.99
        except: self._auto_scroll = True
    def _apply_color_scheme(self):
        self._cs_name = self._cs_var.get(); c = CS[self._cs_name]
        self._out.config(bg=c['bg'], fg=c['fg'], insertbackground=c['ic'])
    def _clear(self):
        self._out.delete('1.0', tk.END); self._out.see(tk.END); self._ap.reset()
    def _context_menu(self, e):
        m = tk.Menu(self, tearoff=0)
        m.add_command(label='复制', command=self._copy_selection)
        m.add_command(label='复制全部', command=lambda: (self.winfo_toplevel().clipboard_clear(), self.winfo_toplevel().clipboard_append(self._out.get('1.0',tk.END))))
        m.add_separator(); m.add_command(label='清屏', command=self._clear)
        try: m.tk_popup(e.x_root, e.y_root)
        finally: m.grab_release()
    def _copy_selection(self):
        try: self.winfo_toplevel().clipboard_clear(); self.winfo_toplevel().clipboard_append(self._out.get(tk.SEL_FIRST, tk.SEL_LAST))
        except: pass
    def _write(self, text):
        if not text: return
        if self._dmode == 'hex':
            try: self._out.insert(tk.END, bytes_to_hex_str(text.encode('latin-1')) + ' '); self._auto_scroll_check(); return
            except: pass
        if self._ansi:
            for seg, ts in self._ap.parse(text):
                if ts:
                    n = f'a{self._tag_count}'; self._tag_count += 1
                    self._out.tag_configure(n, **ts)
                    self._out.insert(tk.END, seg, n)
                else: self._out.insert(tk.END, seg)
        else: self._out.insert(tk.END, ANSI_RE.sub('', text))
        self._auto_scroll_check()
    def _auto_scroll_check(self):
        if self._auto_scroll: self._out.see(tk.END)
        try: l = int(self._out.index('end-1c').split('.')[0]); l > self._max_lines and self._out.delete('1.0', f'{l-self._max_lines+1}.0')
        except: pass
    def _on_enter(self, e): self._send(); return 'break'
    def _send(self):
        text = self._input_var.get(); self._input_var.set('')
        if not text: return
        if self._echo_var.get(): self._write(f'> {text}\n')
        if not (self._hist and self._hist[-1]==text): self._hist.append(text); len(self._hist)>self._max_history and self._hist.pop(0)
        self._hi = -1
        data = text.encode('utf-8', errors='replace')
        mode = self._line_mode_var.get()
        if mode == 'CR': data += b'\r'
        elif mode == 'LF': data += b'\n'
        elif mode == 'CR+LF': data += b'\r\n'
        if data and self._on_send: self._on_send(data)
        if self._log:
            try: self._log.write(f'>>> {text}\n'.encode())
            except: pass
    def _on_history_up(self, e):
        if not self._hist: return 'break'
        if self._hi == -1: self._hi = len(self._hist) - 1
        elif self._hi > 0: self._hi -= 1
        else: return 'break'
        self._input_var.set(self._hist[self._hi]); self._input_entry.icursor(tk.END); return 'break'
    def _on_history_down(self, e):
        if self._hi == -1: return 'break'
        self._hi += 1
        if self._hi >= len(self._hist): self._hi = -1; self._input_var.set('')
        else: self._input_var.set(self._hist[self._hi])
        self._input_entry.icursor(tk.END); return 'break'
    def _hex_dialog(self):
        d = tk.Toplevel(self); d.title('发送HEX'); d.transient(self); d.grab_set(); d.resizable(False,False)
        d.withdraw(); d.update_idletasks()
        pw = self.winfo_toplevel().winfo_width(); ph = self.winfo_toplevel().winfo_height()
        px = self.winfo_toplevel().winfo_rootx(); py = self.winfo_toplevel().winfo_rooty()
        d.geometry(f'450x120+{px+(pw-450)//2}+{py+(ph-120)//2}'); d.deiconify()
        f = ttk.Frame(d, padding=12); f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text='HEX数据:').pack(anchor=tk.W)
        hv = tk.StringVar(); he = ttk.Entry(f, textvariable=hv, font=('Consolas',11)); he.pack(fill=tk.X, pady=(4,8))
        he.focus_set(); add_entry_context_menu(he)
        def go():
            h = hv.get().strip()
            if h:
                c = ''.join(x for x in h if x in '0123456789ABCDEFabcdef')
                if c and len(c)%2==0:
                    b = bytes.fromhex(c)
                    if b and self._on_send: self._on_send(b)
            d.destroy()
        bf = ttk.Frame(f); bf.pack(fill=tk.X)
        ttk.Button(bf, text='发送', command=go).pack(side=tk.RIGHT, padx=(4,0))
        ttk.Button(bf, text='取消', command=d.destroy).pack(side=tk.RIGHT)
        he.bind('<Return>', lambda e: go())
    def _refresh_shortcuts(self):
        for w in self._sc_container.winfo_children(): w.destroy()
        for n,t in self._shortcuts:
            ttk.Button(self._sc_container, text=n, command=lambda t=t: (self._input_var.set(t), self._send()), style='Toolbutton').pack(side=tk.LEFT, padx=(1,1))
        if not self._shortcuts: ttk.Label(self._sc_container, text='(无)', foreground='gray').pack(side=tk.LEFT, padx=4)
    def _add_shortcut(self):
        d = tk.Toplevel(self); d.title('添加快捷命令'); d.transient(self); d.grab_set(); d.resizable(False,False)
        d.withdraw(); d.update_idletasks()
        pw = self.winfo_toplevel().winfo_width(); ph = self.winfo_toplevel().winfo_height()
        px = self.winfo_toplevel().winfo_rootx(); py = self.winfo_toplevel().winfo_rooty()
        d.geometry(f'450x200+{px+(pw-450)//2}+{py+(ph-200)//2}'); d.deiconify()
        f = ttk.Frame(d, padding=12); f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text='名称:').pack(anchor=tk.W); nv = tk.StringVar(); ttk.Entry(f, textvariable=nv).pack(fill=tk.X, pady=(2,6))
        ttk.Label(f, text='命令内容:').pack(anchor=tk.W); tv = tk.StringVar(); ttk.Entry(f, textvariable=tv, font=('Consolas',11)).pack(fill=tk.X, pady=(2,8))
        def ok(): n=nv.get().strip(); c=tv.get().strip(); n and c and (self._shortcuts.append((n,c)), self._refresh_shortcuts(), d.destroy())
        bf = ttk.Frame(f); bf.pack(fill=tk.X)
        ttk.Button(bf, text='确定', command=ok).pack(side=tk.RIGHT, padx=(4,0))
        ttk.Button(bf, text='取消', command=d.destroy).pack(side=tk.RIGHT)
    def _toggle_recording(self):
        if self._log: self._stop_recording()
        else: self._start_recording()
    def _start_recording(self):
        from tkinter import filedialog
        p = filedialog.asksaveasfilename(title='保存终端日志', defaultextension='.log', filetypes=[('日志','*.log'),('文本','*.txt')])
        if not p: return
        try:
            self._log = open(p, 'wb')
            from datetime import datetime
            self._log.write(f'=== 终端日志 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ===\n'.encode())
            self._log.write(self._out.get('1.0', tk.END).encode())
            self._write('[录制开始]\n')
        except: self._log = None; self._write('[录制失败]\n')
    def _stop_recording(self):
        if self._log:
            try:
                from datetime import datetime
                self._log.write(f'\n=== 录制结束 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ===\n'.encode()); self._log.close()
            except: pass
            self._log = None; self._write('[录制已停止]\n')
    def append_received_data(self, data):
        if not data: return
        if self._log:
            try:
                from datetime import datetime
                self._log.write(f'[{datetime.now().strftime("%H:%M:%S.%f")[:-3]}] {data.hex()}\n'.encode())
            except: pass
        try: self._write(data.decode('utf-8', errors='replace'))
        except: self._write(f'[HEX] {bytes_to_hex_str(data)}\n')
    def append_sent_data(self, data):
        if not data or self._echo_var.get(): return
        if self._log:
            try:
                from datetime import datetime
                self._log.write(f'[{datetime.now().strftime("%H:%M:%S.%f")[:-3]}] >>> {data.hex()}\n'.encode())
            except: pass
        if self._dmode == 'hex': self._write(f'[TX] {bytes_to_hex_str(data)}\n')
    def get_settings(self):
        return {'ansi':self._ansi,'echo':self._echo_var.get(),'dmode':self._display_var.get(),
                'lmode':self._line_mode_var.get(),'cs':self._cs_var.get(),
                'hist':self._hist[-100:],'sc':list(self._shortcuts)}
    def load_settings(self, st):
        if not st: return
        self._ansi = st.get('ansi', True); self._ansi_var.set(self._ansi)
        self._echo_var.set(st.get('echo', False))
        self._display_var.set(st.get('dmode', 'ASCII'))
        self._line_mode_var.set(st.get('lmode', 'CR+LF'))
        self._cs_var.set(st.get('cs', '绿底黑字')); self._cs_name = self._cs_var.get(); self._apply_color_scheme()
        h = st.get('hist', []); h and setattr(self, '_hist', list(h))
        sc = st.get('sc', []); sc and (setattr(self, '_shortcuts', [(n,t) for n,t in sc]), self._refresh_shortcuts())
