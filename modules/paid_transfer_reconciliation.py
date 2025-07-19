#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول مغایرت‌گیری انتقال پرداختی
این ماژول مسئول پردازش و مغایرت‌گیری تراکنش‌های انتقال پرداختی است.
"""

from typing import Dict, List, Optional, Any

from modules.database_manager import DatabaseManager
from modules.logger import get_logger

# ایجاد شیء لاگر
logger = get_logger(__name__)

class PaidTransferReconciliation:
    """
    کلاس مغایرت‌گیری انتقال پرداختی
    """
    
    def __init__(self):
        """
        سازنده کلاس
        """
        self.db_manager = DatabaseManager()
    
    def reconcile_transfer_payment(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
        """
        مغایرت‌گیری انتقال پرداختی
        
        پارامترها:
            bank_record: رکورد تراکنش بانکی
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            موفقیت عملیات
        """
        logger.info(f"📤 شروع مغایرت‌گیری انتقال پرداختی برای تراکنش {bank_record.get('id')}")
        
        bank_amount = float(bank_record.get('Withdrawal_Amount', 0))
        bank_date = bank_record.get('Date')
        
        # دریافت ورودی‌های حسابداری حواله/فیش پرداختنی
        accounting_entries = self._get_transfer_payment_accounting_entries(selected_bank_id)
        logger.info(f"📋 تعداد ورودی‌های حسابداری انتقال پرداختی: {len(accounting_entries)}")
        
        # جستجو برای تطبیق بر اساس تاریخ و مبلغ
        matching_entry = self._find_transfer_payment_match(accounting_entries, bank_date, bank_amount)
        
        if matching_entry:
            return self._record_transfer_payment_match(bank_record, matching_entry)
        else:
            logger.warning(f"تطابق انتقال پرداختی یافت نشد برای تراکنش {bank_record.get('id')}")
            self._mark_bank_record_reconciled(bank_record.get('id'), "تطابق انتقال پرداختی یافت نشد")
            return True
    
    def _get_transfer_payment_accounting_entries(self, selected_bank_id: int) -> List[Dict[str, Any]]:
        """
        دریافت ورودی‌های حسابداری مربوط به انتقال پرداختی
        
        پارامترها:
            selected_bank_id: شناسه بانک
            
        خروجی:
            لیست ورودی‌های حسابداری
        """
        all_entries = self.db_manager.get_unreconciled_accounting_entries(selected_bank_id)
        return [entry for entry in all_entries if entry.get('Entry_Type_Acc') == 'حواله/فيش پرداختني']
    
    def _find_transfer_payment_match(self, accounting_entries: List[Dict[str, Any]], 
                                   date: str, amount: float) -> Optional[Dict[str, Any]]:
        """
        یافتن تطبیق انتقال پرداختی
        
        پارامترها:
            accounting_entries: لیست ورودی‌های حسابداری
            date: تاریخ
            amount: مبلغ
            
        خروجی:
            ورودی منطبق یا None
        """
        for entry in accounting_entries:
            entry_amount = float(entry.get('Credit', 0))
            entry_date = entry.get('Due_Date')
            
            if (abs(amount - entry_amount) < 0.01 and entry_date == date):
                return entry
        
        return None
    
    def _record_transfer_payment_match(self, bank_record: Dict[str, Any], accounting_entry: Dict[str, Any]) -> bool:
        """
        ثبت تطبیق انتقال پرداختی
        
        پارامترها:
            bank_record: رکورد بانک
            accounting_entry: ورودی حسابداری
            
        خروجی:
            موفقیت عملیات
        """
        # علامت‌گذاری رکوردها به عنوان مغایرت‌گیری شده
        self.db_manager.update_reconciliation_status('BankTransactions', bank_record.get('id'), True)
        self.db_manager.update_reconciliation_status('AccountingEntries', accounting_entry.get('id'), True)
        
        # ثبت نتیجه مغایرت‌گیری
        success = self.db_manager.record_reconciliation_result(
            bank_id=bank_record.get('id'),
            pos_id=None,
            accounting_id=accounting_entry.get('id'),
            reconciliation_type="Transfer-Payment",
            notes=f"انتقال پرداختی - مبلغ: {bank_record.get('Withdrawal_Amount')}"
        )
        
        if success:
            logger.info(f"تطبیق موفق انتقال پرداختی: بانک ID {bank_record.get('id')}, حسابداری ID {accounting_entry.get('id')}")
        
        return success
    
    def _mark_bank_record_reconciled(self, bank_id: int, notes: str = None) -> bool:
        """
        علامت‌گذاری رکورد بانک به عنوان مغایرت‌گیری شده
        
        پارامترها:
            bank_id: شناسه رکورد بانک
            notes: یادداشت‌ها
            
        خروجی:
            موفقیت عملیات
        """
        success = self.db_manager.update_reconciliation_status('BankTransactions', bank_id, True)
        
        # ثبت نتیجه مغایرت‌گیری در جدول ReconciliationResults
        if success:
            self.db_manager.record_reconciliation_result(
                bank_id=bank_id,
                pos_id=None,
                accounting_id=None,
                reconciliation_type="Manual-Bank-Only",
                notes=notes or "علامت‌گذاری دستی رکورد بانک"
            )
            
        if success and notes:
            logger.info(f"رکورد بانک {bank_id} علامت‌گذاری شد: {notes}")
        return success