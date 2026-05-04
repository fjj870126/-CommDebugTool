"""收发日志浮动功能测试"""
import unittest
import tkinter as tk
from ui.log_panel import LogPanel, FloatWindow, LogEntry, LOG_LEVEL_INFO, LOG_LEVEL_WARNING, LOG_LEVEL_ERROR


class TestLogPanel(unittest.TestCase):
    """测试 LogPanel 基本功能"""

    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.panel = LogPanel(self.root)

    def tearDown(self):
        self.panel.close_all_float_windows()
        self.panel.destroy()

    def test_panel_creation(self):
        """测试面板创建"""
        self.assertIsNotNone(self.panel)
        self.assertEqual(len(self.panel._all_entries), 0)
        self.assertEqual(self.panel._line_count, 0)

    def test_log_tx(self):
        """测试发送日志"""
        self.panel.log_tx(b'\x01\x02\x03', target='COM1')
        self.assertEqual(len(self.panel._all_entries), 1)
        self.assertEqual(self.panel._all_entries[0].direction, 'tx')

    def test_log_rx(self):
        """测试接收日志"""
        self.panel.log_rx(b'\x04\x05\x06', source='COM1')
        self.assertEqual(len(self.panel._all_entries), 1)
        self.assertEqual(self.panel._all_entries[0].direction, 'rx')

    def test_log_info(self):
        """测试信息日志"""
        self.panel.log_info('测试信息')
        self.assertEqual(len(self.panel._all_entries), 1)
        self.assertEqual(self.panel._all_entries[0].tag, 'info')

    def test_clear(self):
        """测试清空"""
        self.panel.log_tx(b'\x01')
        self.panel.log_rx(b'\x02')
        self.panel.log_info('test')
        self.assertEqual(len(self.panel._all_entries), 3)
        self.panel.clear()
        self.assertEqual(len(self.panel._all_entries), 0)
        self.assertEqual(self.panel._line_count, 0)

    def test_float_window_creation(self):
        """测试浮动窗口创建"""
        wid = self.panel._create_new_float_window()
        self.assertIn(wid, self.panel._float_windows)
        self.assertEqual(self.panel.get_float_window_count(), 1)

    def test_float_window_sync(self):
        """测试浮动窗口数据同步"""
        # 先记录日志
        self.panel.log_tx(b'\x01\x02', target='COM1')
        self.panel.log_rx(b'\x03\x04', source='COM1')
        self.panel.log_info('test info')

        # 创建浮动窗口
        wid = self.panel._create_new_float_window()
        fw = self.panel._float_windows[wid]
        self.assertTrue(fw.is_alive())

        # 验证数据同步
        content = fw._text_widget.get('1.0', tk.END)
        self.assertIn('TX', content)
        self.assertIn('RX', content)
        self.assertIn('test info', content)

    def test_float_window_close(self):
        """测试浮动窗口关闭"""
        wid = self.panel._create_new_float_window()
        self.assertEqual(self.panel.get_float_window_count(), 1)
        self.panel._remove_float_window(wid)
        self.assertEqual(self.panel.get_float_window_count(), 0)

    def test_close_all_float_windows(self):
        """测试关闭所有浮动窗口"""
        self.panel._create_new_float_window()
        self.panel._create_new_float_window()
        self.panel._create_new_float_window()
        self.assertEqual(self.panel.get_float_window_count(), 3)
        self.panel.close_all_float_windows()
        self.assertEqual(self.panel.get_float_window_count(), 0)

    def test_export_log(self):
        """测试日志导出"""
        self.panel.log_tx(b'\x01\x02', target='COM1')
        content = self.panel.get_log_content()
        self.assertIn('TX', content)

    def test_get_all_entries(self):
        """测试获取所有条目"""
        self.panel.log_tx(b'\x01')
        self.panel.log_rx(b'\x02')
        entries = self.panel.get_all_entries()
        self.assertEqual(len(entries), 2)

    def test_level_filter(self):
        """测试级别过滤"""
        # 记录不同级别的日志
        self.panel.log_tx(b'\x01', level=LOG_LEVEL_INFO)
        self.panel.log_tx(b'\x02', level=LOG_LEVEL_WARNING)
        self.panel.log_tx(b'\x03', level=LOG_LEVEL_ERROR)

        # 验证所有条目都被记录
        self.assertEqual(len(self.panel._all_entries), 3)

    def test_float_window_level_filter(self):
        """测试浮动窗口级别过滤"""
        self.panel.log_tx(b'\x01', level=LOG_LEVEL_INFO)
        self.panel.log_tx(b'\x02', level=LOG_LEVEL_WARNING)
        self.panel.log_tx(b'\x03', level=LOG_LEVEL_ERROR)

        wid = self.panel._create_new_float_window()
        fw = self.panel._float_windows[wid]

        # 默认显示所有级别
        content = fw._text_widget.get('1.0', tk.END)
        lines = [l for l in content.split('\n') if l.strip()]
        self.assertEqual(len(lines), 3)

    def test_no_detach_button(self):
        """测试已移除浮动按钮"""
        # 检查面板没有 _detach_btn 属性
        self.assertFalse(hasattr(self.panel, '_detach_btn'))
        # 检查面板没有 _detached 属性
        self.assertFalse(hasattr(self.panel, '_detached'))
        # 检查面板没有 _detach_window 属性
        self.assertFalse(hasattr(self.panel, '_detach_window'))


class TestFloatWindow(unittest.TestCase):
    """测试 FloatWindow 功能"""

    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.panel = LogPanel(self.root)
        self.wid = self.panel._create_new_float_window()
        self.fw = self.panel._float_windows[self.wid]

    def tearDown(self):
        self.panel.close_all_float_windows()
        self.panel.destroy()

    def test_window_creation(self):
        """测试窗口创建"""
        self.assertTrue(self.fw.is_alive())
        self.assertIsNotNone(self.fw.get_window())

    def test_window_title(self):
        """测试窗口标题"""
        self.assertIn(f'#{self.wid}', self.fw._window.title())

    def test_append_log(self):
        """测试追加日志"""
        self.fw.append_log('测试日志\n', 'info')
        content = self.fw._text_widget.get('1.0', tk.END)
        self.assertIn('测试日志', content)

    def test_clear_window(self):
        """测试清空窗口"""
        self.fw.append_log('测试日志\n', 'info')
        self.fw._clear_window()
        content = self.fw._text_widget.get('1.0', tk.END).strip()
        self.assertEqual(content, '')

    def test_summary_mode(self):
        """测试汇总模式切换"""
        # 默认不是汇总模式
        self.assertFalse(self.fw._summary_mode)
        # 切换
        self.fw._toggle_summary_mode()
        self.assertTrue(self.fw._summary_mode)
        # 再切换回来
        self.fw._toggle_summary_mode()
        self.assertFalse(self.fw._summary_mode)

    def test_level_filter_change(self):
        """测试级别过滤切换"""
        self.fw._level_filter_var.set('错误')
        self.fw._on_level_filter_change()
        # 过滤切换不应崩溃

    def test_display_mode_change(self):
        """测试显示模式切换"""
        self.fw._display_mode_var.set('ASCII')
        self.fw._on_mode_change()
        # 模式切换不应崩溃

    def test_minimize(self):
        """测试最小化"""
        # 无边框窗口(overrideredirect)无法iconify，改用withdraw测试
        self.fw._window.withdraw()
        self.assertEqual(self.fw._window.state(), 'withdrawn')
        self.fw._window.deiconify()
        self.assertEqual(self.fw._window.state(), 'normal')

    def test_context_menu(self):
        """测试右键菜单"""
        self.assertIsNotNone(self.fw._context_menu)

    def test_copy_selection(self):
        """测试复制"""
        self.fw._text_widget.configure(state=tk.NORMAL)
        self.fw._text_widget.insert(tk.END, '测试文本\n', 'info')
        self.fw._text_widget.configure(state=tk.DISABLED)
        # 选中并复制
        self.fw._text_widget.tag_add(tk.SEL, '1.0', '1.0 lineend')
        self.fw._copy_selection()
        # 复制不应崩溃

    def test_select_all(self):
        """测试全选"""
        self.fw._text_widget.configure(state=tk.NORMAL)
        self.fw._text_widget.insert(tk.END, '测试文本\n', 'info')
        self.fw._text_widget.configure(state=tk.DISABLED)
        self.fw._select_all()
        # 全选不应崩溃

    def test_snap_to_edge(self):
        """测试边缘吸附"""
        self.fw._snap_to_edge()
        # 吸附不应崩溃

    def test_drag_methods(self):
        """测试拖拽方法"""
        # 模拟拖拽事件
        class MockEvent:
            x_root = 100
            y_root = 100

        self.fw._on_drag_start(MockEvent())
        self.assertTrue(self.fw._is_dragging)
        self.fw._on_drag_motion(MockEvent())
        self.fw._on_drag_end(MockEvent())
        self.assertFalse(self.fw._is_dragging)


class TestLogEntry(unittest.TestCase):
    """测试 LogEntry 数据结构"""

    def test_entry_creation(self):
        """测试条目创建"""
        entry = LogEntry('12:00:00.000', '测试', 'tx', LOG_LEVEL_INFO, 'tx')
        self.assertEqual(entry.timestamp, '12:00:00.000')
        self.assertEqual(entry.text, '测试')
        self.assertEqual(entry.tag, 'tx')
        self.assertEqual(entry.level, LOG_LEVEL_INFO)
        self.assertEqual(entry.direction, 'tx')

    def test_entry_slots(self):
        """测试 __slots__ 优化"""
        entry = LogEntry('', '', '', '', '')
        with self.assertRaises(AttributeError):
            entry.invalid_attr = 'test'


if __name__ == '__main__':
    unittest.main()