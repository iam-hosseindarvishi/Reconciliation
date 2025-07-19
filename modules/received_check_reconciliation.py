#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول مغایرت‌گیری چک دریافتی
این ماژول مسئول پردازش و مغایرت‌گیری تراکنش‌های چک دریافتی است.
"""

from typing import Dict, List, Optional, Any

from modules.database_manager import DatabaseManager
from modules.logger import get_logger

# ایجاد شیء لاگر
logger = get_logger(__name__)

class ReceivedCheckReconciliation:
    """
    کلاس مغایرت‌گیری چک دریافتی
    """
    
    def __init__(self):
        """
        سازنده کلاس
        """
        self.db_manager = DatabaseManager()
    
    def reconcile_received_check(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
        """
        مغایرت‌گیری چک دریافتی
        
        پارامترها:
            bank_record: رکورد تراکنش بانکی
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            موفقیت عملیات
        """
        logger.info(f"شروع مغایرت‌گیری چک دریافتی برای تراکنش {bank_record.get('id')}")
        
        bank_amount = float(bank_record.get('Deposit_Amount', 0))
        bank_description = bank_record.get('Description_Bank', '')
        
        # دریافت ورودی‌های حسابداری چک دریافتنی
        accounting_entries = self._get_check_accounting_entries(selected_bank_id, 'دریافتنی')
        logger.info(f"📋 تعداد ورودی‌های حسابداری چک دریافتنی: {len(accounting_entries)}")
        
        # جستجو برای تطبیق بر اساس مبلغ و شماره چک
        matching_entry = self._find_check_match(accounting_entries, bank_amount, bank_description, 'Debit')
        
        if matching_entry:
            return self._record_check_match(bank_record, matching_entry, 'چک دریافتی')
        else:
            logger.warning(f"تطابق چک دریافتی یافت نشد برای تراکنش {bank_record.get('id')}")
            self._mark_bank_record_reconciled(bank_record.get('id'), "تطابق چک دریافتی یافت نشد")
            return True
    
    def _get_check_accounting_entries(self, selected_bank_id: int, check_type: str) -> List[Dict[str, Any]]:
        """
        دریافت ورودی‌های حسابداری مربوط به چک
        
        پارامترها:
            selected_bank_id: شناسه بانک
            check_type: نوع چک (دریافتنی/پرداختنی)
            
        خروجی:
            لیست ورودی‌های حسابداری
        """
        all_entries = self.db_manager.get_unreconciled_accounting_entries(selected_bank_id)
        return [entry for entry in all_entries if check_type in entry.get('Entry_Type_Acc', '')]
    
    def _find_check_match(self, accounting_entries: List[Dict[str, Any]], amount: float, 
                         description: str, amount_field: str) -> Optional[Dict[str, Any]]:
        """
        یافتن تطبیق چک
        
        پارامترها:
            accounting_entries: لیست ورودی‌های حسابداری
            amount: مبلغ
            description: توضیحات بانک
            amount_field: فیلد مبلغ (Debit/Credit)
            
        خروجی:
            ورودی منطبق یا None
        """
        for entry in accounting_entries:
            entry_amount = float(entry.get(amount_field, 0) or 0)
            entry_suffix = entry.get('Account_Reference_Suffix', '')
            
            if (abs(amount - entry_amount) < 0.01 and 
                entry_suffix and description and entry_suffix in description):
                return entry
        
        return None
    
    def _record_check_match(self, bank_record: Dict[str, Any], accounting_entry: Dict[str, Any], check_type: str) -> bool:
        """
        ثبت تطبیق چک
        
        پارامترها:
            bank_record: رکورد بانک
            accounting_entry: ورودی حسابداری
            check_type: نوع چک
            
        خروجی:
            موفقیت عملیات
        """
        # علامت‌گذاری رکوردها به عنوان مغایرت‌گیری شده
        self.db_manager.update_reconciliation_status('BankTransactions', bank_record.get('id'), True)
        self.db_manager.update_reconciliation_status('AccountingEntries', accounting_entry.get('id'), True)
        
        # ثبت نتیجه مغایرت‌گیری
        amount = bank_record.get('Deposit_Amount') or bank_record.get('Withdrawal_Amount')
        success = self.db_manager.record_reconciliation_result(
            bank_id=bank_record.get('id'),
            pos_id=None,
            accounting_id=accounting_entry.get('id'),
            reconciliation_type="Check",
            notes=f"{check_type} - مبلغ: {amount}"
        )
        
        if success:
            logger.info(f"تطبیق موفق چک: بانک ID {bank_record.get('id')}, حسابداری ID {accounting_entry.get('id')}")
        
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