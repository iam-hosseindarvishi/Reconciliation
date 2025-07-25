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
# این callbackها توسط UI تنظیم می‌شوند تا موتور مغایرت‌گیری بتواند با کاربر تعامل کند.
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
    یک نمونه Singleton از ReconciliationEngine را ارائه می‌دهد.
    اگر نمونه وجود نداشته باشد، آن را با وابستگی‌های لازم ایجاد می‌کند.
    """
    global _reconciliation_engine_instance
    if _reconciliation_engine_instance is None:
        logger.debug("ایجاد نمونه جدید از ReconciliationEngine...")
        db_manager = DatabaseManager()
        _reconciliation_engine_instance = ReconciliationEngine(
            db_manager=db_manager,
            manual_reconciliation_callback=_ui_manual_reconciliation_callback,
            aggregate_confirmation_callback=_ui_aggregate_confirmation_callback
        )
        logger.info("نمونه ReconciliationEngine با موفقیت ایجاد شد.")
    return _reconciliation_engine_instance

# ----------------------------------------------------------------------------
# توابع عمومی مغایرت‌گیری (برای فراخوانی از UI)
# ----------------------------------------------------------------------------

def start_reconciliation(selected_bank_id: int, selected_reconciliation_types: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    نقطه ورود عمومی برای شروع فرآیند مغایرت‌گیری از UI.

    Args:
        selected_bank_id (int): شناسه بانک انتخاب شده.
        selected_reconciliation_types (Optional[List[str]]): لیست انواع مغایرت برای اجرا.

    Returns:
        Dict[str, Any]: نتیجه فرآیند مغایرت.
    """
    logger.info(f"شروع فرآیند مغایرت برای بانک ID: {selected_bank_id} و انواع: {selected_reconciliation_types}")
    try:
        engine = _get_reconciliation_engine_instance()
        result = engine.start_reconciliation(selected_bank_id, selected_reconciliation_types)
        logger.info("فرآیند مغایرت با موفقیت به پایان رسید.")
        return result
    except Exception as e:
        logger.error(f"خطا در حین فرآیند مغایرت: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

# ----------------------------------------------------------------------------
# توابع کمکی عمومی (برای فراخوانی از UI)
# این توابع تماس‌ها را به متدهای ReconciliationEngine یا DatabaseManager ارسال می‌کنند.
# ----------------------------------------------------------------------------

def handle_manual_selection(*args, **kwargs):
    """تماس را به متد handle_manual_selection در موتور مغایرت‌گیری ارسال می‌کند."""
    engine = _get_reconciliation_engine_instance()
    return engine.handle_manual_selection(*args, **kwargs)

def handle_aggregate_confirmation(*args, **kwargs):
    """تماس را به متد handle_aggregate_confirmation در موتور مغایرت‌گیری ارسال می‌کند."""
    engine = _get_reconciliation_engine_instance()
    return engine.handle_aggregate_confirmation(*args, **kwargs)

def get_unreconciled_bank_transactions(bank_id: int):
    """تراکنش‌های بانکی مغایرت‌نشده را از پایگاه داده بازیابی می‌کند."""
    db_manager = DatabaseManager()
    return db_manager.get_unreconciled_bank_transactions(bank_id)

def get_unreconciled_pos_transactions():
    """تراکنش‌های پوز مغایرت‌نشده را از پایگاه داده بازیابی می‌کند."""
    db_manager = DatabaseManager()
    return db_manager.get_unreconciled_pos_transactions()

def get_unreconciled_accounting_entries():
    """اسناد حسابداری مغایرت‌نشده را از پایگاه داده بازیابی می‌کند."""
    db_manager = DatabaseManager()
    return db_manager.get_unreconciled_accounting_entries()

def manual_reconcile(*args, **kwargs):
    """مغایرت دستی را از طریق مدیر پایگاه داده انجام می‌دهد."""
    db_manager = DatabaseManager()
    return db_manager.manual_reconcile(*args, **kwargs)

def get_reconciliation_statistics(bank_id: int):
    """آمار مغایرت را برای یک بانک خاص بازیابی می‌کند."""
    db_manager = DatabaseManager()
    return db_manager.get_reconciliation_statistics(bank_id)