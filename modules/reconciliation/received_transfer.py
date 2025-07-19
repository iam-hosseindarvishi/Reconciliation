#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول مغایرت‌گیری انتقال‌های دریافتی
این ماژول مسئول انجام مغایرت‌گیری تراکنش‌های انتقال دریافتی است.
"""

from typing import List, Dict, Any, Optional
from modules.logger import get_logger
from modules.database import DatabaseManager
from datetime import datetime
from .utils import extract_switch_tracking_number

# ایجاد شیء لاگر
logger = get_logger(__name__)

class ReceivedTransferReconciler:
    """
    کلاس مغایرت‌گیری انتقال‌های دریافتی
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
        انجام مغایرت‌گیری انتقال دریافتی
        
        پارامترها:
            bank_record: رکورد بانکی
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            logger.info(f"شروع مغایرت‌گیری انتقال دریافتی برای رکورد {bank_record.get('id')}")
            
            # دریافت ورودی‌های حسابداری انتقال
            accounting_entries = self._get_transfer_accounting_entries(bank_record)
            
            if not accounting_entries:
                logger.warning(f"ورودی‌های حسابداری انتقال برای رکورد {bank_record.get('id')} یافت نشد")
                return False
                
            # تلاش برای تطبیق بر اساس شماره پیگیری
            for entry in accounting_entries:
                tracking_number = extract_switch_tracking_number(entry.get('description', ''))
                if tracking_number:
                    transfer_match = self._find_transfer_by_tracking(tracking_number, bank_record)
                    if transfer_match:
                        return self._record_transfer_match(bank_record, entry, transfer_match, 'tracking')
                        
            # تلاش برای تطبیق بر اساس تاریخ و مبلغ
            for entry in accounting_entries:
                transfer_match = self._find_transfer_by_date_amount(bank_record, entry)
                if transfer_match:
                    return self._record_transfer_match(bank_record, entry, transfer_match, 'date_amount')
                    
            logger.warning(f"تطبیق انتقال دریافتی برای رکورد {bank_record.get('id')} یافت نشد")
            return False
            
        except Exception as e:
            logger.error(f"خطا در مغایرت‌گیری انتقال دریافتی: {str(e)}")
            return False
            
    def _get_transfer_accounting_entries(self, bank_record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        دریافت ورودی‌های حسابداری انتقال
        
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
                AND (description LIKE '%انتقال%' OR description LIKE '%واریز%' 
                     OR description LIKE '%transfer%' OR description LIKE '%deposit%')
                AND amount > 0
                ORDER BY id
            """
            
            return self.db_manager.execute_query(query, (bank_date, bank_amount)) or []
            
        except Exception as e:
            logger.error(f"خطا در دریافت ورودی‌های حسابداری انتقال: {str(e)}")
            return []
            
    def _find_transfer_by_tracking(self, tracking_number: str, 
                                 bank_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        یافتن انتقال بر اساس شماره پیگیری
        
        پارامترها:
            tracking_number: شماره پیگیری
            bank_record: رکورد بانکی
            
        خروجی:
            رکورد انتقال یا None
        """
        try:
            bank_amount = float(bank_record.get('Amount_Bank', 0))
            bank_date = bank_record.get('Transaction_Date_Bank')
            
            # جستجو در جدول انتقال‌ها
            query = """
                SELECT * FROM transfers 
                WHERE tracking_number = ? 
                AND ABS(amount - ?) < 0.01
                AND date = ?
                AND type = 'received'
                ORDER BY id
                LIMIT 1
            """
            
            result = self.db_manager.execute_query(query, (tracking_number, bank_amount, bank_date))
            
            if result:
                logger.info(f"انتقال با شماره پیگیری {tracking_number} یافت شد")
                return result[0]
                
            return None
            
        except Exception as e:
            logger.error(f"خطا در یافتن انتقال بر اساس شماره پیگیری: {str(e)}")
            return None
            
    def _find_transfer_by_date_amount(self, bank_record: Dict[str, Any], 
                                    accounting_entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        یافتن انتقال بر اساس تاریخ و مبلغ
        
        پارامترها:
            bank_record: رکورد بانکی
            accounting_entry: ورودی حسابداری
            
        خروجی:
            رکورد انتقال یا None
        """
        try:
            bank_amount = float(bank_record.get('Amount_Bank', 0))
            bank_date = bank_record.get('Transaction_Date_Bank')
            
            # جستجو در جدول انتقال‌ها
            query = """
                SELECT * FROM transfers 
                WHERE date = ? 
                AND ABS(amount - ?) < 0.01
                AND type = 'received'
                AND reconciliation_status IS NULL
                ORDER BY id
                LIMIT 1
            """
            
            result = self.db_manager.execute_query(query, (bank_date, bank_amount))
            
            if result:
                logger.info(f"انتقال با تاریخ و مبلغ یافت شد: {result[0].get('id')}")
                return result[0]
                
            return None
            
        except Exception as e:
            logger.error(f"خطا در یافتن انتقال بر اساس تاریخ و مبلغ: {str(e)}")
            return None
            
    def _record_transfer_match(self, bank_record: Dict[str, Any], 
                             accounting_entry: Dict[str, Any],
                             transfer_record: Dict[str, Any],
                             match_method: str) -> bool:
        """
        ثبت تطبیق انتقال
        
        پارامترها:
            bank_record: رکورد بانکی
            accounting_entry: ورودی حسابداری
            transfer_record: رکورد انتقال
            match_method: روش تطبیق
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            # ثبت تطبیق در جدول تطبیق‌ها
            match_query = """
                INSERT INTO reconciliation_matches 
                (bank_record_id, accounting_entry_id, transfer_id, match_type, 
                 match_method, match_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.db_manager.execute_query(match_query, (
                bank_record.get('id'),
                accounting_entry.get('id'),
                transfer_record.get('id'),
                'received_transfer',
                match_method,
                current_time
            ))
            
            # به‌روزرسانی وضعیت رکورد بانک
            self._mark_bank_record_reconciled(bank_record.get('id'))
            
            # به‌روزرسانی وضعیت انتقال
            self._mark_transfer_reconciled(transfer_record.get('id'))
            
            logger.info(f"تطبیق انتقال دریافتی ثبت شد: بانک {bank_record.get('id')} - انتقال {transfer_record.get('id')} - روش {match_method}")
            return True
            
        except Exception as e:
            logger.error(f"خطا در ثبت تطبیق انتقال: {str(e)}")
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
            
    def _mark_transfer_reconciled(self, transfer_id: int) -> bool:
        """
        علامت‌گذاری انتقال به عنوان مغایرت‌گیری شده
        
        پارامترها:
            transfer_id: شناسه انتقال
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            query = """
                UPDATE transfers 
                SET reconciliation_status = 'reconciled',
                    reconciliation_date = ?
                WHERE id = ?
            """
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.db_manager.execute_query(query, (current_time, transfer_id))
            
            return True
            
        except Exception as e:
            logger.error(f"خطا در علامت‌گذاری انتقال: {str(e)}")
            return False