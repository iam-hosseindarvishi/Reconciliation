#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
موتور اصلی مغایرت‌گیری
این ماژول مسئول دریافت اطلاعات بانک و هدایت به ماژول‌های مناسب است.
"""

from typing import List, Dict, Any, Optional
from modules.logger import get_logger
from modules.database import DatabaseManager
from datetime import datetime

# وارد کردن ماژول‌های مغایرت‌گیری
from .pos_deposit import PosDepositReconciler
from .received_transfer import ReceivedTransferReconciler
from .paid_transfer import PaidTransferReconciler
from .received_check import ReceivedCheckReconciler
from .paid_check import PaidCheckReconciler
from .utils import validate_persian_date, safe_parse_persian_date

# ایجاد شیء لاگر
logger = get_logger(__name__)

class ReconciliationEngine:
    """
    موتور اصلی مغایرت‌گیری
    این کلاس مسئول هماهنگی و مدیریت فرآیند مغایرت‌گیری است.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        مقداردهی اولیه
        
        پارامترها:
            db_manager: مدیر پایگاه داده
        """
        self.db_manager = db_manager
        
        # ایجاد نمونه‌های ماژول‌های مغایرت‌گیری
        self.pos_reconciler = PosDepositReconciler(db_manager)
        self.received_transfer_reconciler = ReceivedTransferReconciler(db_manager)
        self.paid_transfer_reconciler = PaidTransferReconciler(db_manager)
        self.received_check_reconciler = ReceivedCheckReconciler(db_manager)
        self.paid_check_reconciler = PaidCheckReconciler(db_manager)
        
        # آمار مغایرت‌گیری
        self.stats = {
            'total_processed': 0,
            'successful_matches': 0,
            'failed_matches': 0,
            'pos_deposits': 0,
            'received_transfers': 0,
            'paid_transfers': 0,
            'received_checks': 0,
            'paid_checks': 0
        }
        
    def start_reconciliation(self, date_from: str = None, date_to: str = None) -> Dict[str, Any]:
        """
        شروع فرآیند مغایرت‌گیری
        
        پارامترها:
            date_from: تاریخ شروع (اختیاری)
            date_to: تاریخ پایان (اختیاری)
            
        خروجی:
            نتایج مغایرت‌گیری
        """
        try:
            logger.info("شروع فرآیند مغایرت‌گیری")
            
            # اعتبارسنجی تاریخ‌ها
            if date_from and not validate_persian_date(date_from):
                logger.error(f"تاریخ شروع نامعتبر: {date_from}")
                return {'success': False, 'error': 'تاریخ شروع نامعتبر'}
                
            if date_to and not validate_persian_date(date_to):
                logger.error(f"تاریخ پایان نامعتبر: {date_to}")
                return {'success': False, 'error': 'تاریخ پایان نامعتبر'}
                
            # دریافت رکوردهای بانکی مغایرت‌گیری نشده
            bank_records = self._get_unreconciled_bank_records(date_from, date_to)
            
            if not bank_records:
                logger.info("هیچ رکورد بانکی مغایرت‌گیری نشده‌ای یافت نشد")
                return {
                    'success': True,
                    'message': 'هیچ رکورد بانکی مغایرت‌گیری نشده‌ای یافت نشد',
                    'stats': self.stats
                }
                
            logger.info(f"تعداد {len(bank_records)} رکورد بانکی برای مغایرت‌گیری یافت شد")
            
            # پردازش هر رکورد بانکی
            for bank_record in bank_records:
                self._process_bank_record(bank_record)
                
            # تولید گزارش نهایی
            return self._generate_final_report()
            
        except Exception as e:
            logger.error(f"خطا در فرآیند مغایرت‌گیری: {str(e)}")
            return {'success': False, 'error': str(e)}
            
    def _get_unreconciled_bank_records(self, date_from: str = None, 
                                     date_to: str = None) -> List[Dict[str, Any]]:
        """
        دریافت رکوردهای بانکی مغایرت‌گیری نشده
        
        پارامترها:
            date_from: تاریخ شروع
            date_to: تاریخ پایان
            
        خروجی:
            لیست رکوردهای بانکی
        """
        try:
            # ساخت کوئری بر اساس تاریخ‌ها
            base_query = """
                SELECT * FROM bank_data 
                WHERE (reconciliation_status IS NULL OR reconciliation_status != 'reconciled')
            """
            
            params = []
            
            if date_from:
                base_query += " AND Transaction_Date_Bank >= ?"
                params.append(date_from)
                
            if date_to:
                base_query += " AND Transaction_Date_Bank <= ?"
                params.append(date_to)
                
            base_query += " ORDER BY Transaction_Date_Bank, id"
            
            return self.db_manager.execute_query(base_query, params) or []
            
        except Exception as e:
            logger.error(f"خطا در دریافت رکوردهای بانکی: {str(e)}")
            return []
            
    def _process_bank_record(self, bank_record: Dict[str, Any]) -> bool:
        """
        پردازش یک رکورد بانکی
        
        پارامترها:
            bank_record: رکورد بانکی
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            self.stats['total_processed'] += 1
            
            bank_id = bank_record.get('id')
            transaction_type = bank_record.get('Transaction_Type_Bank', '').strip()
            amount = float(bank_record.get('Amount_Bank', 0))
            
            logger.info(f"پردازش رکورد بانک {bank_id} - نوع: {transaction_type} - مبلغ: {amount}")
            
            # تشخیص نوع تراکنش و هدایت به ماژول مناسب
            success = False
            
            if transaction_type == 'POS Deposit':
                success = self.pos_reconciler.reconcile(bank_record)
                if success:
                    self.stats['pos_deposits'] += 1
                    
            elif transaction_type == 'Received Transfer':
                success = self.received_transfer_reconciler.reconcile(bank_record)
                if success:
                    self.stats['received_transfers'] += 1
                    
            elif transaction_type == 'Paid Transfer':
                success = self.paid_transfer_reconciler.reconcile(bank_record)
                if success:
                    self.stats['paid_transfers'] += 1
                    
            elif transaction_type == 'Received Check':
                success = self.received_check_reconciler.reconcile(bank_record)
                if success:
                    self.stats['received_checks'] += 1
                    
            elif transaction_type == 'Paid Check':
                success = self.paid_check_reconciler.reconcile(bank_record)
                if success:
                    self.stats['paid_checks'] += 1
                    
            else:
                logger.warning(f"نوع تراکنش ناشناخته: {transaction_type} برای رکورد {bank_id}")
                
            # به‌روزرسانی آمار
            if success:
                self.stats['successful_matches'] += 1
                logger.info(f"مغایرت‌گیری رکورد {bank_id} با موفقیت انجام شد")
            else:
                self.stats['failed_matches'] += 1
                logger.warning(f"مغایرت‌گیری رکورد {bank_id} ناموفق بود")
                
            return success
            
        except Exception as e:
            logger.error(f"خطا در پردازش رکورد بانک {bank_record.get('id')}: {str(e)}")
            self.stats['failed_matches'] += 1
            return False
            
    def _generate_final_report(self) -> Dict[str, Any]:
        """
        تولید گزارش نهایی
        
        خروجی:
            گزارش نهایی مغایرت‌گیری
        """
        try:
            success_rate = 0
            if self.stats['total_processed'] > 0:
                success_rate = (self.stats['successful_matches'] / self.stats['total_processed']) * 100
                
            report = {
                'success': True,
                'completion_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'stats': self.stats.copy(),
                'success_rate': round(success_rate, 2),
                'summary': {
                    'total_records': self.stats['total_processed'],
                    'successful_matches': self.stats['successful_matches'],
                    'failed_matches': self.stats['failed_matches'],
                    'breakdown': {
                        'POS Deposits': self.stats['pos_deposits'],
                        'Received Transfers': self.stats['received_transfers'],
                        'Paid Transfers': self.stats['paid_transfers'],
                        'Received Checks': self.stats['received_checks'],
                        'Paid Checks': self.stats['paid_checks']
                    }
                }
            }
            
            logger.info(f"مغایرت‌گیری کامل شد - نرخ موفقیت: {success_rate:.2f}%")
            logger.info(f"تعداد کل: {self.stats['total_processed']}, موفق: {self.stats['successful_matches']}, ناموفق: {self.stats['failed_matches']}")
            
            return report
            
        except Exception as e:
            logger.error(f"خطا در تولید گزارش نهایی: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'stats': self.stats
            }
            
    def manual_reconcile(self, bank_record_id: int, accounting_entry_id: int = None, 
                        transfer_id: int = None, check_id: int = None) -> bool:
        """
        انجام مغایرت‌گیری دستی
        
        پارامترها:
            bank_record_id: شناسه رکورد بانک
            accounting_entry_id: شناسه ورودی حسابداری (اختیاری)
            transfer_id: شناسه انتقال (اختیاری)
            check_id: شناسه چک (اختیاری)
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            logger.info(f"شروع مغایرت‌گیری دستی برای رکورد بانک {bank_record_id}")
            
            # ثبت تطبیق دستی
            match_query = """
                INSERT INTO reconciliation_matches 
                (bank_record_id, accounting_entry_id, transfer_id, check_id, 
                 match_type, match_date, is_manual)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.db_manager.execute_query(match_query, (
                bank_record_id,
                accounting_entry_id,
                transfer_id,
                check_id,
                'manual',
                current_time,
                True
            ))
            
            # علامت‌گذاری رکورد بانک به عنوان مغایرت‌گیری شده
            update_query = """
                UPDATE bank_data 
                SET reconciliation_status = 'reconciled',
                    reconciliation_date = ?
                WHERE id = ?
            """
            
            self.db_manager.execute_query(update_query, (current_time, bank_record_id))
            
            logger.info(f"مغایرت‌گیری دستی رکورد {bank_record_id} با موفقیت انجام شد")
            return True
            
        except Exception as e:
            logger.error(f"خطا در مغایرت‌گیری دستی: {str(e)}")
            return False
            
    def get_reconciliation_status(self, date_from: str = None, 
                                date_to: str = None) -> Dict[str, Any]:
        """
        دریافت وضعیت مغایرت‌گیری
        
        پارامترها:
            date_from: تاریخ شروع
            date_to: تاریخ پایان
            
        خروجی:
            وضعیت مغایرت‌گیری
        """
        try:
            # آمار کلی
            total_query = "SELECT COUNT(*) as total FROM bank_data"
            reconciled_query = "SELECT COUNT(*) as reconciled FROM bank_data WHERE reconciliation_status = 'reconciled'"
            
            params = []
            if date_from or date_to:
                date_condition = ""
                if date_from:
                    date_condition += " AND Transaction_Date_Bank >= ?"
                    params.append(date_from)
                if date_to:
                    date_condition += " AND Transaction_Date_Bank <= ?"
                    params.append(date_to)
                    
                total_query += " WHERE 1=1" + date_condition
                reconciled_query += date_condition
                
            total_result = self.db_manager.execute_query(total_query, params)
            reconciled_result = self.db_manager.execute_query(reconciled_query, params)
            
            total_count = total_result[0]['total'] if total_result else 0
            reconciled_count = reconciled_result[0]['reconciled'] if reconciled_result else 0
            pending_count = total_count - reconciled_count
            
            reconciliation_rate = 0
            if total_count > 0:
                reconciliation_rate = (reconciled_count / total_count) * 100
                
            return {
                'total_records': total_count,
                'reconciled_records': reconciled_count,
                'pending_records': pending_count,
                'reconciliation_rate': round(reconciliation_rate, 2)
            }
            
        except Exception as e:
            logger.error(f"خطا در دریافت وضعیت مغایرت‌گیری: {str(e)}")
            return {
                'error': str(e)
            }