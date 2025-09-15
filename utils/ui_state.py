# -*- coding: utf-8 -*-
"""
ماژول مدیریت وضعیت رابط کاربری
این ماژول برای نگهداری و مدیریت وضعیت‌های مختلف رابط کاربری استفاده می‌شود
تا بتوان از هر جای برنامه به این وضعیت‌ها دسترسی داشت.
"""

import logging
from utils.logger_config import setup_logger

# راه‌اندازی لاگر
logger = setup_logger('utils.ui_state')

# متغیرهای وضعیت پیش‌فرض
_show_manual_reconciliation = True

# تابع‌های دسترسی به وضعیت نمایش مغایرت‌گیری دستی
def set_show_manual_reconciliation(value):
    """
    تنظیم وضعیت نمایش مغایرت‌گیری دستی
    
    Args:
        value (bool): آیا دیالوگ مغایرت‌گیری دستی نمایش داده شود یا خیر
    """
    global _show_manual_reconciliation
    _show_manual_reconciliation = value
    logger.info(f"Show manual reconciliation set to: {value}")

def get_show_manual_reconciliation():
    """
    دریافت وضعیت نمایش مغایرت‌گیری دستی
    
    Returns:
        bool: وضعیت نمایش مغایرت‌گیری دستی
    """
    return _show_manual_reconciliation