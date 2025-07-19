#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول مغایرت‌گیری واریزهای پوز
این ماژول مسئول انجام مغایرت‌گیری تراکنش‌های واریز پوز است.
"""

from typing import List, Dict, Any, Optional, Tuple
from modules.logger import get_logger
from modules.database import DatabaseManager
from datetime import datetime

# ایجاد شیء لاگر
logger = get_logger(__name__)

class PosDepositReconciler:
    """
    کلاس مغایرت‌گیری واریزهای پوز
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        مقداردهی اولیه
        
        پارامترها:
            db_manager: مدیر پایگاه داده
        """
        self.db_manager = db_manager
        
    def reconcile(self, bank_record: Dict[str, Any]) -> bool:
        """
        انجام مغایرت‌گیری واریز پوز
        
        پارامترها:
            bank_record: رکورد بانکی
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            logger.info(f"شروع مغایرت‌گیری واریز پوز برای رکورد {bank_record.get('id')}")
            
            # بررسی وجود داده‌های ترمینال
            terminal_data = self._get_terminal_data(bank_record)
            if not terminal_data:
                logger.warning(f"داده‌های ترمینال برای رکورد {bank_record.get('id')} یافت نشد")
                return False
                
            # یافتن ورودی سرجمع حسابداری
            aggregate_entry = self._find_aggregate_accounting_entry(bank_record, terminal_data)
            
            if aggregate_entry:
                # پردازش مغایرت‌گیری سرجمع
                return self._process_aggregate_reconciliation(bank_record, aggregate_entry, terminal_data)
            else:
                # پردازش مغایرت‌گیری تفصیلی
                return self._process_detailed_pos_reconciliation(bank_record, terminal_data)
                
        except Exception as e:
            logger.error(f"خطا در مغایرت‌گیری واریز پوز: {str(e)}")
            return False
            
    def _get_terminal_data(self, bank_record: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        دریافت داده‌های ترمینال
        
        پارامترها:
            bank_record: رکورد بانکی
            
        خروجی:
            لیست داده‌های ترمینال یا None
        """
        try:
            # استخراج تاریخ از رکورد بانک
            bank_date = bank_record.get('Transaction_Date_Bank')
            if not bank_date:
                return None
                
            # جستجو در جدول داده‌های ترمینال
            query = """
                SELECT * FROM terminal_data 
                WHERE date = ? 
                ORDER BY terminal_id, transaction_time
            """
            
            result = self.db_manager.execute_query(query, (bank_date,))
            return result if result else None
            
        except Exception as e:
            logger.error(f"خطا در دریافت داده‌های ترمینال: {str(e)}")
            return None
            
    def _find_aggregate_accounting_entry(self, bank_record: Dict[str, Any], 
                                        terminal_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        یافتن ورودی سرجمع حسابداری
        
        پارامترها:
            bank_record: رکورد بانکی
            terminal_data: داده‌های ترمینال
            
        خروجی:
            ورودی حسابداری یا None
        """
        try:
            bank_amount = float(bank_record.get('Amount_Bank', 0))
            bank_date = bank_record.get('Transaction_Date_Bank')
            
            # محاسبه مجموع مبالغ ترمینال
            total_terminal_amount = sum(float(item.get('amount', 0)) for item in terminal_data)
            
            # جستجو برای ورودی سرجمع در حسابداری
            query = """
                SELECT * FROM accounting_entries 
                WHERE date = ? 
                AND ABS(amount - ?) < 0.01
                AND description LIKE '%سرجمع%'
                ORDER BY id
            """
            
            entries = self.db_manager.execute_query(query, (bank_date, bank_amount))
            
            if entries:
                logger.info(f"ورودی سرجمع حسابداری یافت شد: {entries[0].get('id')}")
                return entries[0]
                
            return None
            
        except Exception as e:
            logger.error(f"خطا در یافتن ورودی سرجمع حسابداری: {str(e)}")
            return None
            
    def _process_aggregate_reconciliation(self, bank_record: Dict[str, Any], 
                                        aggregate_entry: Dict[str, Any],
                                        terminal_data: List[Dict[str, Any]]) -> bool:
        """
        پردازش مغایرت‌گیری سرجمع
        
        پارامترها:
            bank_record: رکورد بانکی
            aggregate_entry: ورودی سرجمع حسابداری
            terminal_data: داده‌های ترمینال
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            # ثبت تطبیق سرجمع
            match_data = {
                'bank_record_id': bank_record.get('id'),
                'accounting_entry_id': aggregate_entry.get('id'),
                'match_type': 'aggregate_pos',
                'match_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'terminal_count': len(terminal_data),
                'total_terminal_amount': sum(float(item.get('amount', 0)) for item in terminal_data)
            }
            
            # ثبت در جدول تطبیق‌ها
            self._record_pos_match(match_data)
            
            # به‌روزرسانی وضعیت رکورد بانک
            self._mark_bank_record_reconciled(bank_record.get('id'))
            
            logger.info(f"مغایرت‌گیری سرجمع پوز با موفقیت انجام شد برای رکورد {bank_record.get('id')}")
            return True
            
        except Exception as e:
            logger.error(f"خطا در پردازش مغایرت‌گیری سرجمع: {str(e)}")
            return False
            
    def _process_detailed_pos_reconciliation(self, bank_record: Dict[str, Any], 
                                           terminal_data: List[Dict[str, Any]]) -> bool:
        """
        پردازش مغایرت‌گیری تفصیلی پوز
        
        پارامترها:
            bank_record: رکورد بانکی
            terminal_data: داده‌های ترمینال
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            # دریافت ورودی‌های حسابداری پوز
            accounting_entries = self._get_pos_accounting_entries(bank_record)
            
            if not accounting_entries:
                logger.warning(f"ورودی‌های حسابداری پوز برای رکورد {bank_record.get('id')} یافت نشد")
                return False
                
            # تلاش برای تطبیق تک تراکنش
            for entry in accounting_entries:
                if self._reconcile_single_pos_transaction(bank_record, entry):
                    return True
                    
            logger.warning(f"تطبیق تفصیلی پوز برای رکورد {bank_record.get('id')} یافت نشد")
            return False
            
        except Exception as e:
            logger.error(f"خطا در پردازش مغایرت‌گیری تفصیلی پوز: {str(e)}")
            return False
            
    def _get_pos_accounting_entries(self, bank_record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        دریافت ورودی‌های حسابداری پوز
        
        پارامترها:
            bank_record: رکورد بانکی
            
        خروجی:
            لیست ورودی‌های حسابداری
        """
        try:
            bank_date = bank_record.get('Transaction_Date_Bank')
            bank_amount = float(bank_record.get('Amount_Bank', 0))
            
            # جستجو در ورودی‌های حسابداری
            query = """
                SELECT * FROM accounting_entries 
                WHERE date = ? 
                AND ABS(amount - ?) < 0.01
                AND (description LIKE '%پوز%' OR description LIKE '%POS%')
                ORDER BY id
            """
            
            return self.db_manager.execute_query(query, (bank_date, bank_amount)) or []
            
        except Exception as e:
            logger.error(f"خطا در دریافت ورودی‌های حسابداری پوز: {str(e)}")
            return []
            
    def _reconcile_single_pos_transaction(self, bank_record: Dict[str, Any], 
                                         accounting_entry: Dict[str, Any]) -> bool:
        """
        مغایرت‌گیری یک تراکنش پوز
        
        پارامترها:
            bank_record: رکورد بانکی
            accounting_entry: ورودی حسابداری
            
        خروجی:
            True در صورت تطبیق
        """
        try:
            bank_amount = float(bank_record.get('Amount_Bank', 0))
            accounting_amount = float(accounting_entry.get('amount', 0))
            
            # بررسی تطابق مبلغ
            if abs(bank_amount - accounting_amount) < 0.01:
                # بررسی پسوند 5 یا 6 رقمی در توضیحات
                description = accounting_entry.get('description', '')
                if self._check_pos_suffix(description):
                    # ثبت تطبیق
                    match_data = {
                        'bank_record_id': bank_record.get('id'),
                        'accounting_entry_id': accounting_entry.get('id'),
                        'match_type': 'single_pos',
                        'match_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    self._record_pos_match(match_data)
                    self._mark_bank_record_reconciled(bank_record.get('id'))
                    
                    logger.info(f"تطبیق تک تراکنش پوز انجام شد: بانک {bank_record.get('id')} - حسابداری {accounting_entry.get('id')}")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"خطا در مغایرت‌گیری تک تراکنش پوز: {str(e)}")
            return False
            
    def _check_pos_suffix(self, description: str) -> bool:
        """
        بررسی وجود پسوند 5 یا 6 رقمی در توضیحات
        
        پارامترها:
            description: متن توضیحات
            
        خروجی:
            True اگر پسوند معتبر وجود داشته باشد
        """
        import re
        # جستجو برای عدد 5 یا 6 رقمی
        pattern = r'\b\d{5,6}\b'
        return bool(re.search(pattern, description))
        
    def _record_pos_match(self, match_data: Dict[str, Any]) -> bool:
        """
        ثبت تطبیق پوز
        
        پارامترها:
            match_data: داده‌های تطبیق
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            query = """
                INSERT INTO reconciliation_matches 
                (bank_record_id, accounting_entry_id, match_type, match_date, 
                 terminal_count, total_terminal_amount)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            
            params = (
                match_data.get('bank_record_id'),
                match_data.get('accounting_entry_id'),
                match_data.get('match_type'),
                match_data.get('match_date'),
                match_data.get('terminal_count'),
                match_data.get('total_terminal_amount')
            )
            
            self.db_manager.execute_query(query, params)
            logger.info(f"تطبیق پوز ثبت شد: {match_data.get('bank_record_id')}")
            return True
            
        except Exception as e:
            logger.error(f"خطا در ثبت تطبیق پوز: {str(e)}")
            return False
            
    def _mark_bank_record_reconciled(self, bank_record_id: int) -> bool:
        """
        علامت‌گذاری رکورد بانک به عنوان مغایرت‌گیری شده
        
        پارامترها:
            bank_record_id: شناسه رکورد بانک
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            query = """
                UPDATE bank_data 
                SET reconciliation_status = 'reconciled',
                    reconciliation_date = ?
                WHERE id = ?
            """
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.db_manager.execute_query(query, (current_time, bank_record_id))
            
            logger.info(f"رکورد بانک {bank_record_id} به عنوان مغایرت‌گیری شده علامت‌گذاری شد")
            return True
            
        except Exception as e:
            logger.error(f"خطا در علامت‌گذاری رکورد بانک: {str(e)}")
            return False