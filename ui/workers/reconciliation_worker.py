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
            # مغایرت‌گیری شاپرک (پوز)
            self.progress_updated.emit(10, "در حال مغایرت‌گیری تراکنش‌های شاپرک (پوز)...")
            self.log_message.emit("شروع مغایرت‌گیری تراکنش‌های شاپرک (پوز)...", "blue")
            
            shaparak_results = self.reconciliation_engine.reconcile_shaparak_pos()
            self.log_message.emit(
                f"مغایرت‌گیری شاپرک (پوز): {shaparak_results['matched']} مورد تطبیق، "
                f"{shaparak_results['unmatched']} مورد عدم تطبیق.",
                "green" if shaparak_results['matched'] > 0 else "orange"
            )
            
            # مغایرت‌گیری چک‌ها
            self.progress_updated.emit(30, "در حال مغایرت‌گیری چک‌ها...")
            self.log_message.emit("شروع مغایرت‌گیری چک‌ها...", "blue")
            
            checks_results = self.reconciliation_engine.reconcile_checks()
            self.log_message.emit(
                f"مغایرت‌گیری چک‌ها: {checks_results['matched']} مورد تطبیق، "
                f"{checks_results['unmatched']} مورد عدم تطبیق.",
                "green" if checks_results['matched'] > 0 else "orange"
            )
            
            # مغایرت‌گیری انتقال‌ها
            self.progress_updated.emit(50, "در حال مغایرت‌گیری انتقال‌ها...")
            self.log_message.emit("شروع مغایرت‌گیری انتقال‌ها...", "blue")
            
            transfers_results = self.reconciliation_engine.reconcile_transfers()
            self.log_message.emit(
                f"مغایرت‌گیری انتقال‌ها: {transfers_results['matched']} مورد تطبیق، "
                f"{transfers_results['unmatched']} مورد عدم تطبیق.",
                "green" if transfers_results['matched'] > 0 else "orange"
            )
            
            # مغایرت‌گیری پوز با حسابداری
            self.progress_updated.emit(70, "در حال مغایرت‌گیری پوز با حسابداری...")
            self.log_message.emit("شروع مغایرت‌گیری پوز با حسابداری...", "blue")
            
            pos_acc_results = self.reconciliation_engine.reconcile_pos_accounting()
            self.log_message.emit(
                f"مغایرت‌گیری پوز با حسابداری: {pos_acc_results['matched']} مورد تطبیق، "
                f"{pos_acc_results['unmatched']} مورد عدم تطبیق.",
                "green" if pos_acc_results['matched'] > 0 else "orange"
            )
            
            # پیشنهاد بر اساس پسوند کارت
            self.progress_updated.emit(90, "در حال یافتن پیشنهادات بر اساس پسوند کارت...")
            self.log_message.emit("شروع یافتن پیشنهادات بر اساس پسوند کارت...", "blue")
            
            card_suffix_hints = self.reconciliation_engine.find_card_suffix_hints()
            self.log_message.emit(
                f"{len(card_suffix_hints['results'])} پیشنهاد بر اساس پسوند کارت یافت شد.",
                "green" if len(card_suffix_hints['results']) > 0 else "orange"
            )
            
            # نمایش نتایج کلی
            total_matched = (
                shaparak_results['matched'] + 
                checks_results['matched'] + 
                transfers_results['matched'] + 
                pos_acc_results['matched']
            )
            
            self.progress_updated.emit(100, "مغایرت‌گیری با موفقیت انجام شد.")
            self.log_message.emit(f"مغایرت‌گیری با موفقیت انجام شد. مجموعاً {total_matched} مورد تطبیق یافت شد.", "green")
            self.reconciliation_completed.emit(True, "مغایرت‌گیری با موفقیت انجام شد.")
            
        except Exception as e:
            logger.error(f"خطا در مغایرت‌گیری: {str(e)}")
            self.log_message.emit(f"خطا در مغایرت‌گیری: {str(e)}", "red")
            self.reconciliation_completed.emit(False, f"خطا در مغایرت‌گیری: {str(e)}")