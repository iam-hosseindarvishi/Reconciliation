#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول مغایرت‌گیری انتقال دریافتی
این ماژول مسئول پردازش و مغایرت‌گیری تراکنش‌های انتقال دریافتی است.
"""

import re
from typing import Dict, List, Optional, Any

from modules.database_manager import DatabaseManager
from modules.logger import get_logger

# ایجاد شیء لاگر
logger = get_logger(__name__)

class ReceivedTransferReconciliation:
    """
    کلاس مغایرت‌گیری انتقال دریافتی
    """
    
    def __init__(self):
        """
        سازنده کلاس
        """
        self.db_manager = DatabaseManager()
    
    def reconcile_transfer_deposit(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
        """
        مغایرت‌گیری انتقال دریافتی
        
        پارامترها:
            bank_record: رکورد تراکنش بانکی
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            موفقیت عملیات
        """
        logger.info(f"شروع مغایرت‌گیری انتقال دریافتی برای تراکنش {bank_record.get('id')}")
        
        bank_description = bank_record.get('Description_Bank', '')
        bank_amount = float(bank_record.get('Deposit_Amount', 0))
        bank_date = bank_record.get('Date')
        
        # دریافت ورودی‌های حسابداری حواله/فیش دریافتنی
        accounting_entries = self._get_transfer_accounting_entries(selected_bank_id)
        logger.info(f"📋 تعداد ورودی‌های حسابداری انتقال دریافتی: {len(accounting_entries)}")
        
        matching_entry = None
        
        # بررسی وجود شماره پیگیری سوئیچ
        if bank_description and 'شماره پیگیری سوئیچ' in bank_description:
            switch_tracking = self._extract_switch_tracking_number(bank_description)
            if switch_tracking:
                matching_entry = self._find_transfer_by_tracking(accounting_entries, switch_tracking, bank_amount)
        
        # جستجوی عمومی بر اساس تاریخ و مبلغ
        if not matching_entry:
            matching_entry = self._find_transfer_by_date_amount(accounting_entries, bank_date, bank_amount)
        
        if matching_entry:
            return self._record_transfer_match(bank_record, matching_entry)
        else:
            logger.warning(f"تطابق انتقال دریافتی یافت نشد برای تراکنش {bank_record.get('id')}")
            self._mark_bank_record_reconciled(bank_record.get('id'), "تطابق انتقال یافت نشد")
            return True
    
    def _get_transfer_accounting_entries(self, selected_bank_id: int) -> List[Dict[str, Any]]:
        """
        دریافت ورودی‌های حسابداری مربوط به انتقال
        
        پارامترها:
            selected_bank_id: شناسه بانک
            
        خروجی:
            لیست ورودی‌های حسابداری
        """
        all_entries = self.db_manager.get_unreconciled_accounting_entries(selected_bank_id)
        return [entry for entry in all_entries if entry.get('Entry_Type_Acc') == 'حواله/فيش دريافتني']
    
    def _extract_switch_tracking_number(self, description: str) -> Optional[str]:
        """
        استخراج شماره پیگیری سوئیچ از توضیحات
        
        پارامترها:
            description: متن توضیحات
            
        خروجی:
            شماره پیگیری یا None
        """
        # جستجو برای عدد بعد از عبارت "شماره پیگیری سوئیچ"
        pattern = r'شماره پیگیری سوئیچ[:\s]*(\d+)'
        match = re.search(pattern, description)
        return match.group(1) if match else None
    
    def _find_transfer_by_tracking(self, accounting_entries: List[Dict[str, Any]], 
                                 tracking_number: str, amount: float) -> Optional[Dict[str, Any]]:
        """
        یافتن انتقال بر اساس شماره پیگیری
        
        پارامترها:
            accounting_entries: لیست ورودی‌های حسابداری
            tracking_number: شماره پیگیری
            amount: مبلغ
            
        خروجی:
            ورودی منطبق یا None
        """
        for entry in accounting_entries:
            entry_amount = float(entry.get('Debit', 0) or entry.get('Credit', 0))
            entry_suffix = entry.get('Account_Reference_Suffix', '')
            
            if (abs(amount - entry_amount) < 0.01 and entry_suffix == tracking_number):
                return entry
        
        return None
    
    def _find_transfer_by_date_amount(self, accounting_entries: List[Dict[str, Any]], 
                                    date: str, amount: float) -> Optional[Dict[str, Any]]:
        """
        یافتن انتقال بر اساس تاریخ و مبلغ
        
        پارامترها:
            accounting_entries: لیست ورودی‌های حسابداری
            date: تاریخ
            amount: مبلغ
            
        خروجی:
            ورودی منطبق یا None
        """
        for entry in accounting_entries:
            entry_amount = float(entry.get('Debit', 0) or entry.get('Credit', 0))
            entry_date = entry.get('Due_Date')
            
            if (abs(amount - entry_amount) < 0.01 and entry_date == date):
                return entry
        
        return None
    
    def _record_transfer_match(self, bank_record: Dict[str, Any], accounting_entry: Dict[str, Any]) -> bool:
        """
        ثبت تطبیق انتقال
        
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
            reconciliation_type="Transfer",
            notes=f"انتقال دریافتی - مبلغ: {bank_record.get('Deposit_Amount')}"
        )
        
        if success:
            logger.info(f"تطبیق موفق انتقال: بانک ID {bank_record.get('id')}, حسابداری ID {accounting_entry.get('id')}")
        
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