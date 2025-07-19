#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
کلاس کارگر برای انجام مغایرت‌گیری در پس‌زمینه
"""

from PySide6.QtCore import QThread, Signal

from modules.reconciliation_logic import ReconciliationEngine
from modules.logger import get_logger

# ایجاد شیء لاگر
logger = get_logger(__name__)


class ReconciliationWorker(QThread):
    """
    کلاس کارگر برای انجام مغایرت‌گیری در پس‌زمینه
    """
    
    # سیگنال‌های مختلف برای اطلاع‌رسانی پیشرفت و نتیجه
    progress_updated = Signal(int, str)
    reconciliation_completed = Signal(bool, str)
    log_message = Signal(str, str)
    
    def __init__(self, reconciliation_engine: ReconciliationEngine):
        """
        مقداردهی اولیه کلاس ReconciliationWorker
        
        پارامترها:
            reconciliation_engine: نمونه‌ای از کلاس ReconciliationEngine
        """
        super().__init__()
        self.reconciliation_engine = reconciliation_engine
    
    def run(self):
        """
        اجرای عملیات مغایرت‌گیری
        """
        try:
            # شروع مغایرت‌گیری
            self.progress_updated.emit(10, "در حال شروع فرآیند مغایرت‌گیری...")
            self.log_message.emit("شروع فرآیند مغایرت‌گیری...", "blue")
            
            # فرض می‌کنیم بانک اول انتخاب شده (باید از UI دریافت شود)
            selected_bank_id = 1  # این مقدار باید از UI دریافت شود
            
            self.progress_updated.emit(50, "در حال انجام مغایرت‌گیری...")
            
            # انجام مغایرت‌گیری
            results = self.reconciliation_engine.start_reconciliation(selected_bank_id)
            
            # نمایش نتایج
            total_processed = results.get('total_processed', 0)
            successful_reconciliations = results.get('successful_reconciliations', 0)
            failed_reconciliations = results.get('failed_reconciliations', 0)
            
            self.log_message.emit(
                f"مغایرت‌گیری تکمیل شد: {total_processed} تراکنش پردازش شد، "
                f"{successful_reconciliations} موفق، {failed_reconciliations} ناموفق.",
                "green" if successful_reconciliations > 0 else "orange"
            )
            
            self.progress_updated.emit(100, "مغایرت‌گیری با موفقیت انجام شد.")
            self.log_message.emit(f"مغایرت‌گیری با موفقیت انجام شد. مجموعاً {successful_reconciliations} مورد تطبیق یافت شد.", "green")
            self.reconciliation_completed.emit(True, "مغایرت‌گیری با موفقیت انجام شد.")
            
        except Exception as e:
            logger.error(f"خطا در مغایرت‌گیری: {str(e)}")
            self.log_message.emit(f"خطا در مغایرت‌گیری: {str(e)}", "red")
            self.reconciliation_completed.emit(False, f"خطا در مغایرت‌گیری: {str(e)}")