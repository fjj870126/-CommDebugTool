#!/usr/bin/env python3
"""通信调试工具 - 支持TCP/UDP/串口通信，组包发送，自动校验"""

import sys
import os

# 确保可以找到模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow


def main():
    app = MainWindow()
    app.run()


if __name__ == '__main__':
    main()
