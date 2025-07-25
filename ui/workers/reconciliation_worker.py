#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
کلاس کارگر برای انجام مغایرت‌گیری در پس‌زمینه
"""

from PySide6.QtCore import QThread, Signal
from typing import Callable

from modules.logger import get_logger

# ایجاد شیء لاگر
logger = get_logger(__name__)


class ReconciliationWorker(QThread):
    """
    کلاس کارگر برای انجام یک تابع در پس‌زمینه و ارسال نتایج.
    """
    
    finished = Signal(object)  # سیگنال برای نتیجه موفق
    error = Signal(str)  # سیگنال برای خطا
    progress = Signal(int, str) # سیگنال برای گزارش پیشرفت

    def __init__(self, function: Callable, *args, **kwargs):
        """
        مقداردهی اولیه کارگر.

        پارامترها:
            function: تابعی که باید در پس‌زمینه اجرا شود.
            *args: آرگومان‌های موقعیتی برای تابع.
            **kwargs: آرگومان‌های کلیدواژه‌ای برای تابع.
        """
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        """
        تابع را اجرا کرده و نتیجه یا خطا را ارسال می‌کند.
        """
        try:
            self.progress.emit(10, "شروع عملیات...")
            result = self.function(*self.args, **self.kwargs)
            self.progress.emit(100, "عملیات با موفقیت انجام شد.")
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"خطا در اجرای تابع پس‌زمینه: {e}", exc_info=True)
            self.error.emit(str(e))