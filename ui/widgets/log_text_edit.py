#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
کلاس سفارشی برای نمایش لاگ‌ها با رنگ‌های مختلف
"""

from datetime import datetime
from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QFont, QTextCursor


class LogTextEdit(QTextEdit):
    """
    کلاس سفارشی برای نمایش لاگ‌ها با رنگ‌های مختلف
    """
    
    def __init__(self, parent=None):
        """
        مقداردهی اولیه کلاس LogTextEdit
        
        پارامترها:
            parent: ویجت والد
        """
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
    
    def append_log(self, text: str, color: str = "black"):
        """
        افزودن متن لاگ با رنگ مشخص
        
        پارامترها:
            text: متن لاگ
            color: رنگ متن (نام رنگ یا کد هگزادسیمال)
        """
        self.moveCursor(QTextCursor.End)
        current_time = datetime.now().strftime("%H:%M:%S")
        formatted_text = f"[{current_time}] {text}"
        self.append(f"<span style='color: {color};'>{formatted_text}</span>")
        self.moveCursor(QTextCursor.End)
        # اسکرول به پایین
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())