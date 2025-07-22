#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول منطق مغایرت‌گیری اصلی
این ماژول مسئول هماهنگی و مدیریت فرآیند مغایرت‌گیری است.
"""

from typing import Dict, List, Optional, Any, Callable

from modules.database_manager import DatabaseManager
from modules.logger import get_logger
from modules.reconciliation import ReconciliationEngine

# ایجاد شیء لاگر
logger = get_logger(__name__)


# برای سازگاری با کد موجود، کلاس ReconciliationEngine را از ماژول reconciliation وارد می‌کنیم
# تمام عملکردهای مغایرت‌گیری به ماژول‌های جداگانه منتقل شده‌اند

def create_reconciliation_engine() -> ReconciliationEngine:
    """
    ایجاد موتور مغایرت‌گیری
        
    خروجی:
        نمونه از موتور مغایرت‌گیری
    """
    db_manager = DatabaseManager()
    return ReconciliationEngine(db_manager)

# متدهای کمکی برای سازگاری با کد موجود
def start_reconciliation(selected_bank_id: int) -> Dict[str, Any]:
    """
    شروع فرآیند مغایرت‌گیری برای بانک انتخاب شده
    
    پارامترها:
        selected_bank_id: شناسه بانک انتخاب شده
        
    خروجی:
        دیکشنری حاوی نتایج مغایرت‌گیری
    """
    logger.info(f"شروع فرآیند مغایرت‌گیری برای بانک با شناسه {selected_bank_id}...")
    
    # ایجاد موتور مغایرت‌گیری
    db_manager = DatabaseManager()
    engine = ReconciliationEngine(db_manager)
    
    # شروع فرآیند مغایرت‌گیری
    return engine.start_reconciliation(selected_bank_id)

def get_unreconciled_bank_transactions(selected_bank_id: Optional[int] = None):
    """
    دریافت تراکنش‌های بانکی مغایرت‌گیری نشده
    
    پارامترها:
        selected_bank_id: شناسه بانک (اختیاری)
        
    خروجی:
        لیست تراکنش‌های بانکی
    """
    db_manager = DatabaseManager()
    if selected_bank_id:
        return db_manager.get_unreconciled_bank_transactions(selected_bank_id)
    else:
        return db_manager.get_unreconciled_bank_transactions()

def get_unreconciled_pos_transactions(selected_bank_id: int):
    """
    دریافت تراکنش‌های پوز مغایرت‌گیری نشده
    
    پارامترها:
        selected_bank_id: شناسه بانک
        
    خروجی:
        لیست تراکنش‌های پوز
    """
    engine = ReconciliationEngine()
    return engine.get_unreconciled_pos_transactions(selected_bank_id)

def get_unreconciled_accounting_entries(selected_bank_id: Optional[int] = None):
    """
    دریافت ورودی‌های حسابداری مغایرت‌گیری نشده
    
    پارامترها:
        selected_bank_id: شناسه بانک (اختیاری)
        
    خروجی:
        لیست ورودی‌های حسابداری
    """
    db_manager = DatabaseManager()
    if selected_bank_id:
        return db_manager.get_unreconciled_accounting_entries(selected_bank_id)
    else:
        return db_manager.get_unreconciled_accounting_entries()

def manual_reconcile(bank_id: int, pos_id: Optional[int] = None, 
                    accounting_id: Optional[int] = None, notes: str = None) -> bool:
    """
    انجام مغایرت‌گیری دستی
    
    پارامترها:
        bank_id: شناسه رکورد بانک
        pos_id: شناسه رکورد پوز (اختیاری)
        accounting_id: شناسه رکورد حسابداری (اختیاری)
        notes: یادداشت‌ها (اختیاری)
        
    خروجی:
        موفقیت عملیات
    """
    engine = ReconciliationEngine()
    return engine.manual_reconcile(bank_id, pos_id, accounting_id, notes)

def get_reconciliation_statistics(selected_bank_id: int):
    """
    دریافت آمار مغایرت‌گیری
    
    پارامترها:
        selected_bank_id: شناسه بانک
        
    خروجی:
        دیکشنری حاوی آمار
    """
    engine = ReconciliationEngine()
    return engine.get_reconciliation_statistics(selected_bank_id)