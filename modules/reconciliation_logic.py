# -*- coding: utf-8 -*-
"""
ماژول واسط برای منطق مغایرت‌گیری، جهت اتصال به رابط کاربری.

این ماژول به عنوان یک لایه واسط (wrapper) عمل می‌کند تا فراخوانی‌های UI به موتور اصلی مغایرت‌گیری 
و مدیر پایگاه داده را تسهیل کند. همچنین، مکانیزم‌های callback برای تعاملات کاربر (مانند مغایرت دستی)
را مدیریت می‌کند.
"""

import logging
from typing import Optional, Callable, List, Dict, Any

from .database_manager import DatabaseManager
from .reconciliation import ReconciliationEngine

# راه‌اندازی لاگر
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# تعریف Callback های UI
# ----------------------------------------------------------------------------

_ui_manual_reconciliation_callback: Optional[Callable] = None
"""Callback برای نمایش دیالوگ مغایرت دستی به کاربر."""

_ui_aggregate_confirmation_callback: Optional[Callable] = None
"""Callback برای تأیید مغایرت تجمعی از کاربر."""

def set_ui_manual_reconciliation_callback(callback: Callable):
    """تابع عمومی برای تنظیم callback مغایرت دستی از UI."""
    global _ui_manual_reconciliation_callback
    _ui_manual_reconciliation_callback = callback
    logger.info("Callback مغایرت دستی UI با موفقیت تنظیم شد.")

def set_ui_aggregate_confirmation_callback(callback: Callable):
    """تابع عمومی برای تنظیم callback تأیید تجمعی از UI."""
    global _ui_aggregate_confirmation_callback
    _ui_aggregate_confirmation_callback = callback
    logger.info("Callback تأیید تجمعی UI با موفقیت تنظیم شد.")

# ----------------------------------------------------------------------------
# مدیریت نمونه موتور مغایرت‌گیری (Singleton)
# ----------------------------------------------------------------------------

_reconciliation_engine_instance: Optional[ReconciliationEngine] = None
"""نمونه Singleton از موتور مغایرت‌گیری."""

def _get_reconciliation_engine_instance() -> ReconciliationEngine:
    """
    یک نمونه تکی از ReconciliationEngine را فراهم می‌کند (الگوی Singleton).
    
    اگر نمونه وجود نداشته باشد، یک نمونه جدید با callbackهای UI ایجاد می‌کند.
    """
    global _reconciliation_engine_instance
    if _reconciliation_engine_instance is None:
        logger.info("ایجاد نمونه جدید از ReconciliationEngine...")
        db_manager = DatabaseManager()
        _reconciliation_engine_instance = ReconciliationEngine(
            db_manager=db_manager,
            ui_callback_manual_reconciliation_needed=_ui_manual_reconciliation_callback,
            ui_callback_aggregate_confirmation=_ui_aggregate_confirmation_callback
        )
    return _reconciliation_engine_instance

# ----------------------------------------------------------------------------
# توابع عمومی مغایرت‌گیری (برای فراخوانی از UI)
# ----------------------------------------------------------------------------

def start_reconciliation(selected_bank_id: int, selected_reconciliation_types: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    نقطه ورود عمومی برای UI جهت شروع فرآیند مغایرت‌گیری.
    """
    logger.info(f"شروع فرآیند مغایرت‌گیری از طریق UI برای بانک ID: {selected_bank_id} و انواع: {selected_reconciliation_types}")
    engine = _get_reconciliation_engine_instance()
    
    try:
        # منطق انتخاب بین مغایرت کلی و انتخابی
        if not selected_reconciliation_types or 'All' in selected_reconciliation_types:
            results = engine.start_reconciliation(selected_bank_id)
        else:
            results = engine.start_reconciliation_selective(selected_bank_id, selected_reconciliation_types)
        logger.info("فرآیند مغایرت‌گیری با موفقیت به پایان رسید.")
        return results
    except Exception as e:
        logger.error(f"خطای بحرانی در حین فرآیند مغایرت‌گیری: {e}", exc_info=True)
        return {"error": str(e)}

# ----------------------------------------------------------------------------
# توابع کمکی عمومی (برای فراخوانی از UI)
# ----------------------------------------------------------------------------

def handle_manual_selection(*args, **kwargs):
    """تماس را به متد handle_manual_selection در موتور مغایرت‌گیری ارسال می‌کند."""
    engine = _get_reconciliation_engine_instance()
    return engine.handle_manual_selection(*args, **kwargs)

def handle_aggregate_confirmation(*args, **kwargs):
    """تماس را به متد handle_aggregate_confirmation در موتور مغایرت‌گیری ارسال می‌کند."""
    engine = _get_reconciliation_engine_instance()
    return engine.handle_aggregate_confirmation(*args, **kwargs)

def get_unreconciled_bank_transactions(*args, **kwargs):
    """فراخوانی برای دریافت تراکنش‌های بانکی مغایرت نشده."""
    engine = _get_reconciliation_engine_instance()
    return engine.db_manager.get_unreconciled_bank_transactions(*args, **kwargs)

def get_unreconciled_pos_transactions(*args, **kwargs):
    """فراخوانی برای دریافت تراکنش‌های پوز مغایرت نشده."""
    engine = _get_reconciliation_engine_instance()
    return engine.db_manager.get_unreconciled_pos_transactions(*args, **kwargs)

def get_unreconciled_accounting_entries(*args, **kwargs):
    """فراخوانی برای دریافت رکوردهای حسابداری مغایرت نشده."""
    engine = _get_reconciliation_engine_instance()
    return engine.db_manager.get_unreconciled_accounting_entries(*args, **kwargs)

def manual_reconcile(*args, **kwargs):
    """فراخوانی برای انجام مغایرت دستی."""
    engine = _get_reconciliation_engine_instance()
    return engine.manual_reconcile(*args, **kwargs)

def get_reconciliation_statistics(*args, **kwargs):
    """فراخوانی برای دریافت آمار مغایرت."""
    engine = _get_reconciliation_engine_instance()
    return engine.db_manager.get_reconciliation_statistics(*args, **kwargs)