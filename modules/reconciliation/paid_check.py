#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول مغایرت‌گیری چک‌های پرداختی
این ماژول مسئول انجام مغایرت‌گیری تراکنش‌های چک پرداختی است.
"""

from typing import List, Dict, Any, Optional
from modules.logger import get_logger
from modules.database_manager import DatabaseManager
from datetime import datetime

# ایجاد شیء لاگر
logger = get_logger(__name__)

class PaidCheckReconciler:
    """
    کلاس مغایرت‌گیری چک‌های پرداختی
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
        انجام مغایرت‌گیری چک پرداختی
        
        پارامترها:
            bank_record: رکورد بانکی
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            logger.info(f"شروع مغایرت‌گیری چک پرداختی برای رکورد {bank_record.get('id')}")
            
            # دریافت ورودی‌های حسابداری چک
            accounting_entries = self._get_check_accounting_entries(bank_record, 'paid')
            
            if not accounting_entries:
                logger.warning(f"ورودی‌های حسابداری چک پرداختی برای رکورد {bank_record.get('id')} یافت نشد")
                return False
                
            # تلاش برای تطبیق چک
            for entry in accounting_entries:
                check_match = self._find_check_match(bank_record, entry, 'paid')
                if check_match:
                    return self._record_check_match(bank_record, entry, check_match, 'paid')
                    
            logger.warning(f"تطبیق چک پرداختی برای رکورد {bank_record.get('id')} یافت نشد")
            return False
            
        except Exception as e:
            logger.error(f"خطا در مغایرت‌گیری چک پرداختی: {str(e)}")
            return False
            
    def _get_check_accounting_entries(self, bank_record: Dict[str, Any], 
                                    check_type: str) -> List[Dict[str, Any]]:
        """
        دریافت ورودی‌های حسابداری چک
        
        پارامترها:
            bank_record: رکورد بانکی
            check_type: نوع چک (received/paid)
            
        خروجی:
            لیست ورودی‌های حسابداری
        """
        try:
            bank_date = bank_record.get('Transaction_Date_Bank')
            bank_amount = abs(float(bank_record.get('Amount_Bank', 0)))  # مبلغ مثبت برای مقایسه
            
            # تعیین شرط مبلغ بر اساس نوع چک
            amount_condition = "amount > 0" if check_type == 'received' else "amount < 0"
            
            # جستجو در ورودی‌های حسابداری
            query = f"""
                SELECT * FROM accounting_entries 
                WHERE date = ? 
                AND ABS(ABS(amount) - ?) < 0.01
                AND (description LIKE '%چک%' OR description LIKE '%check%')
                AND {amount_condition}
                ORDER BY id
            """
            
            return self.db_manager.execute_query(query, (bank_date, bank_amount)) or []
            
        except Exception as e:
            logger.error(f"خطا در دریافت ورودی‌های حسابداری چک: {str(e)}")
            return []
            
    def _find_check_match(self, bank_record: Dict[str, Any], 
                         accounting_entry: Dict[str, Any],
                         check_type: str) -> Optional[Dict[str, Any]]:
        """
        یافتن تطبیق چک
        
        پارامترها:
            bank_record: رکورد بانکی
            accounting_entry: ورودی حسابداری
            check_type: نوع چک
            
        خروجی:
            رکورد چک یا None
        """
        try:
            bank_amount = abs(float(bank_record.get('Amount_Bank', 0)))
            bank_date = bank_record.get('Transaction_Date_Bank')
            description = accounting_entry.get('description', '')
            
            # جستجو در جدول چک‌ها
            query = """
                SELECT * FROM checks 
                WHERE date = ? 
                AND ABS(amount - ?) < 0.01
                AND type = ?
                AND reconciliation_status IS NULL
                ORDER BY id
                LIMIT 1
            """
            
            result = self.db_manager.execute_query(query, (bank_date, bank_amount, check_type))
            
            if result:
                logger.info(f"چک {check_type} با تاریخ و مبلغ یافت شد: {result[0].get('id')}")
                return result[0]
                
            # اگر تطبیق مستقیم یافت نشد، جستجو بر اساس شماره چک در توضیحات
            check_number = self._extract_check_number(description)
            if check_number:
                query = """
                    SELECT * FROM checks 
                    WHERE check_number = ? 
                    AND ABS(amount - ?) < 0.01
                    AND type = ?
                    AND reconciliation_status IS NULL
                    ORDER BY id
                    LIMIT 1
                """
                
                result = self.db_manager.execute_query(query, (check_number, bank_amount, check_type))
                
                if result:
                    logger.info(f"چک {check_type} با شماره چک {check_number} یافت شد: {result[0].get('id')}")
                    return result[0]
                    
            return None
            
        except Exception as e:
            logger.error(f"خطا در یافتن تطبیق چک: {str(e)}")
            return None
            
    def _extract_check_number(self, description: str) -> Optional[str]:
        """
        استخراج شماره چک از توضیحات
        
        پارامترها:
            description: متن توضیحات
            
        خروجی:
            شماره چک یا None
        """
        import re
        
        # الگوهای مختلف برای شماره چک
        patterns = [
            r'چک\s*شماره[:\s]*(\d+)',
            r'شماره\s*چک[:\s]*(\d+)',
            r'check\s*number[:\s]*(\d+)',
            r'چک[:\s]*(\d{6,})',  # شماره چک معمولاً حداقل 6 رقم است
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1)
                
        return None
        
    def _record_check_match(self, bank_record: Dict[str, Any], 
                          accounting_entry: Dict[str, Any],
                          check_record: Dict[str, Any],
                          check_type: str) -> bool:
        """
        ثبت تطبیق چک
        
        پارامترها:
            bank_record: رکورد بانکی
            accounting_entry: ورودی حسابداری
            check_record: رکورد چک
            check_type: نوع چک
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            # ثبت تطبیق در جدول تطبیق‌ها
            match_query = """
                INSERT INTO reconciliation_matches 
                (bank_record_id, accounting_entry_id, check_id, match_type, match_date)
                VALUES (?, ?, ?, ?, ?)
            """
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.db_manager.execute_query(match_query, (
                bank_record.get('id'),
                accounting_entry.get('id'),
                check_record.get('id'),
                f'{check_type}_check',
                current_time
            ))
            
            # به‌روزرسانی وضعیت رکورد بانک
            self._mark_bank_record_reconciled(bank_record.get('id'))
            
            # به‌روزرسانی وضعیت چک
            self._mark_check_reconciled(check_record.get('id'))
            
            logger.info(f"تطبیق چک {check_type} ثبت شد: بانک {bank_record.get('id')} - چک {check_record.get('id')}")
            return True
            
        except Exception as e:
            logger.error(f"خطا در ثبت تطبیق چک: {str(e)}")
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
            
            return True
            
        except Exception as e:
            logger.error(f"خطا در علامت‌گذاری رکورد بانک: {str(e)}")
            return False
            
    def _mark_check_reconciled(self, check_id: int) -> bool:
        """
        علامت‌گذاری چک به عنوان مغایرت‌گیری شده
        
        پارامترها:
            check_id: شناسه چک
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            query = """
                UPDATE checks 
                SET reconciliation_status = 'reconciled',
                    reconciliation_date = ?
                WHERE id = ?
            """
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.db_manager.execute_query(query, (current_time, check_id))
            
            return True
            
        except Exception as e:
            logger.error(f"خطا در علامت‌گذاری چک: {str(e)}")
            return False