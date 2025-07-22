#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
موتور اصلی مغایرت‌گیری
این ماژول مسئول دریافت اطلاعات بانک و هدایت به ماژول‌های مناسب است.
"""

from typing import List, Dict, Any, Optional
from modules.logger import get_logger
from modules.database_manager import DatabaseManager
from datetime import datetime

# وارد کردن ماژول‌های مغایرت‌گیری
from .pos_deposit import PosDepositReconciler
from .received_transfer import ReceivedTransferReconciler
from .paid_transfer import PaidTransferReconciler
from .received_check import ReceivedCheckReconciler
from .paid_check import PaidCheckReconciler
from .utils import validate_persian_date, safe_parse_persian_date
from modules.utils import date_utils

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
        
    def start_reconciliation(self, selected_bank_id: int = None, date_from: str = None, date_to: str = None) -> Dict[str, Any]:
        """
        شروع فرآیند مغایرت‌گیری
        
        پارامترها:
            selected_bank_id: شناسه بانک انتخاب شده (اختیاری)
            date_from: تاریخ شروع (اختیاری)
            date_to: تاریخ پایان (اختیاری)
            
        خروجی:
            نتایج مغایرت‌گیری
        """
        try:
            logger.info(f"شروع فرآیند مغایرت‌گیری برای بانک {selected_bank_id or 'همه بانک‌ها'}")
            
            # اعتبارسنجی تاریخ‌ها
            if date_from and not validate_persian_date(date_from):
                logger.error(f"تاریخ شروع نامعتبر: {date_from}")
                return {'success': False, 'error': 'تاریخ شروع نامعتبر'}
                
            if date_to and not validate_persian_date(date_to):
                logger.error(f"تاریخ پایان نامعتبر: {date_to}")
                return {'success': False, 'error': 'تاریخ پایان نامعتبر'}
                
            # دریافت رکوردهای بانکی مغایرت‌گیری نشده
            bank_records = self._get_unreconciled_bank_records(selected_bank_id, date_from, date_to)
            
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
            
    def start_reconciliation_selective(self, selected_bank_id: int, selected_types: list, 
                                      date_from: str = None, date_to: str = None) -> Dict[str, Any]:
        """
        شروع فرآیند مغایرت‌گیری انتخابی برای انواع خاص
        
        پارامترها:
            selected_bank_id: شناسه بانک انتخاب شده
            selected_types: لیست انواع مغایرت‌گیری انتخاب شده
            date_from: تاریخ شروع (اختیاری)
            date_to: تاریخ پایان (اختیاری)
            
        خروجی:
            نتایج مغایرت‌گیری
        """
        try:
            logger.info(f"شروع فرآیند مغایرت‌گیری انتخابی برای بانک {selected_bank_id} - انواع: {selected_types}")
            
            # اعتبارسنجی تاریخ‌ها
            if date_from and not validate_persian_date(date_from):
                logger.error(f"تاریخ شروع نامعتبر: {date_from}")
                return {'success': False, 'error': 'تاریخ شروع نامعتبر'}
                
            if date_to and not validate_persian_date(date_to):
                logger.error(f"تاریخ پایان نامعتبر: {date_to}")
                return {'success': False, 'error': 'تاریخ پایان نامعتبر'}
                
            # دریافت رکوردهای بانکی مغایرت‌گیری نشده
            bank_records = self._get_unreconciled_bank_records(selected_bank_id, date_from, date_to)
            
            if not bank_records:
                logger.info("هیچ رکورد بانکی مغایرت‌گیری نشده‌ای یافت نشد")
                return {
                    'success': True,
                    'message': 'هیچ رکورد بانکی مغایرت‌گیری نشده‌ای یافت نشد',
                    'stats': self.stats
                }
                
            # فیلتر کردن رکوردها بر اساس انواع انتخاب شده
            filtered_records = self._filter_records_by_type(bank_records, selected_types)
            
            if not filtered_records:
                logger.info("هیچ رکورد بانکی با انواع انتخاب شده یافت نشد")
                return {
                    'success': True,
                    'message': 'هیچ رکورد بانکی با انواع انتخاب شده یافت نشد',
                    'stats': self.stats
                }
                
            logger.info(f"تعداد {len(filtered_records)} رکورد بانکی با انواع انتخاب شده برای مغایرت‌گیری یافت شد")
            
            # پردازش هر رکورد بانکی
            for bank_record in filtered_records:
                self._process_bank_record_selective(bank_record, selected_types)
                
            # تولید گزارش نهایی
            return self._generate_final_report()
            
        except Exception as e:
            logger.error(f"خطا در فرآیند مغایرت‌گیری انتخابی: {str(e)}")
            return {'success': False, 'error': str(e)}
            
    def _get_unreconciled_bank_records(self, selected_bank_id: int = None, date_from: str = None, 
                                     date_to: str = None) -> List[Dict[str, Any]]:
        """
        دریافت رکوردهای بانکی مغایرت‌گیری نشده
        
        پارامترها:
            selected_bank_id: شناسه بانک انتخاب شده
            date_from: تاریخ شروع
            date_to: تاریخ پایان
            
        خروجی:
            لیست رکوردهای بانکی
        """
        try:
            # ساخت کوئری بر اساس تاریخ‌ها و بانک
            base_query = """
                SELECT * FROM bank_data 
                WHERE (reconciliation_status IS NULL OR reconciliation_status != 'reconciled')
            """
            
            params = []
            
            if selected_bank_id:
                base_query += " AND BankID = ?"
                params.append(selected_bank_id)
            
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
                    
            elif transaction_type in ['Received Transfer', 'Paid Transfer']:
                # استفاده از متد جدید _reconcile_transfers برای مدیریت حواله‌ها
                success = self._process_single_transfer(bank_record, bank_record.get('BankID'))
                if success:
                    if transaction_type == 'Received Transfer':
                        self.stats['received_transfers'] += 1
                    else:
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
            
    def _filter_records_by_type(self, bank_records: List[Dict[str, Any]], selected_types: list) -> List[Dict[str, Any]]:
        """
        فیلتر کردن رکوردهای بانکی بر اساس انواع انتخاب شده
        
        پارامترها:
            bank_records: لیست رکوردهای بانکی
            selected_types: لیست انواع انتخاب شده
            
        خروجی:
            لیست رکوردهای فیلتر شده
        """
        try:
            # نقشه‌برداری انواع فارسی به انگلیسی
            type_mapping = {
                'حواله / فیش': ['Received Transfer', 'Paid Transfer'],
                'پوزها': ['POS Deposit'],
                'چک‌ها': ['Received Check', 'Paid Check']
            }
            
            # تبدیل انواع انتخاب شده به انواع پایگاه داده
            allowed_types = []
            for selected_type in selected_types:
                if selected_type in type_mapping:
                    allowed_types.extend(type_mapping[selected_type])
                    
            if not allowed_types:
                return bank_records  # اگر نوع خاصی انتخاب نشده، همه را برگردان
                
            # فیلتر کردن رکوردها
            filtered_records = []
            for record in bank_records:
                transaction_type = record.get('Transaction_Type_Bank', '').strip()
                if transaction_type in allowed_types:
                    filtered_records.append(record)
                    
            logger.info(f"از {len(bank_records)} رکورد، {len(filtered_records)} رکورد با انواع انتخاب شده فیلتر شد")
            return filtered_records
            
        except Exception as e:
            logger.error(f"خطا در فیلتر کردن رکوردها: {str(e)}")
            return bank_records
            
    def _process_bank_record_selective(self, bank_record: Dict[str, Any], selected_types: list) -> bool:
        """
        پردازش انتخابی یک رکورد بانکی بر اساس انواع انتخاب شده
        
        پارامترها:
            bank_record: رکورد بانکی
            selected_types: لیست انواع انتخاب شده
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            self.stats['total_processed'] += 1
            
            bank_id = bank_record.get('id')
            transaction_type = bank_record.get('Transaction_Type_Bank', '').strip()
            amount = float(bank_record.get('Amount_Bank', 0))
            
            logger.info(f"پردازش انتخابی رکورد بانک {bank_id} - نوع: {transaction_type} - مبلغ: {amount}")
            
            # نقشه‌برداری انواع فارسی به انگلیسی
            type_mapping = {
                'حواله / فیش': ['Received Transfer', 'Paid Transfer'],
                'پوزها': ['POS Deposit'],
                'چک‌ها': ['Received Check', 'Paid Check']
            }
            
            # بررسی اینکه آیا این نوع تراکنش در انواع انتخاب شده است
            should_process = False
            for selected_type in selected_types:
                if selected_type in type_mapping:
                    if transaction_type in type_mapping[selected_type]:
                        should_process = True
                        break
                        
            if not should_process:
                logger.info(f"رکورد {bank_id} با نوع {transaction_type} در انواع انتخاب شده نیست")
                return False
                
            # تشخیص نوع تراکنش و هدایت به ماژول مناسب
            success = False
            
            if transaction_type == 'POS Deposit' and 'پوزها' in selected_types:
                success = self.pos_reconciler.reconcile(bank_record)
                if success:
                    self.stats['pos_deposits'] += 1
                    
            elif (transaction_type in ['Received Transfer', 'Paid Transfer'] and 'حواله / فیش' in selected_types):
                # استفاده از متد جدید _reconcile_transfers برای مدیریت حواله‌ها
                success = self._process_single_transfer(bank_record, bank_record.get('BankID'))
                if success:
                    if transaction_type == 'Received Transfer':
                        self.stats['received_transfers'] += 1
                    else:
                        self.stats['paid_transfers'] += 1
                    
            elif transaction_type == 'Received Check' and 'چک‌ها' in selected_types:
                success = self.received_check_reconciler.reconcile(bank_record)
                if success:
                    self.stats['received_checks'] += 1
                    
            elif transaction_type == 'Paid Check' and 'چک‌ها' in selected_types:
                success = self.paid_check_reconciler.reconcile(bank_record)
                if success:
                    self.stats['paid_checks'] += 1
                    
            else:
                logger.warning(f"نوع تراکنش {transaction_type} برای رکورد {bank_id} پردازش نشد")
                
            # به‌روزرسانی آمار
            if success:
                self.stats['successful_matches'] += 1
                logger.info(f"مغایرت‌گیری انتخابی رکورد {bank_id} با موفقیت انجام شد")
            else:
                self.stats['failed_matches'] += 1
                logger.warning(f"مغایرت‌گیری انتخابی رکورد {bank_id} ناموفق بود")
                
            return success
            
        except Exception as e:
            logger.error(f"خطا در پردازش انتخابی رکورد بانک {bank_record.get('id')}: {str(e)}")
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
            
    def _reconcile_transfers(self, selected_bank_id: int) -> bool:
        """
        مغایرت‌گیری حواله‌ها (بانک به حسابداری)
        
        پارامترها:
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            logger.info(f"شروع مغایرت‌گیری حواله‌ها برای بانک {selected_bank_id}")
            
            # 1. واکشی حواله‌های بانکی مغایرت‌گیری نشده
            unreconciled_transfers = self._get_unreconciled_bank_transfers(selected_bank_id)
            
            if not unreconciled_transfers:
                logger.info("هیچ حواله مغایرت‌گیری نشده‌ای یافت نشد")
                return True
                
            logger.info(f"تعداد {len(unreconciled_transfers)} حواله برای مغایرت‌گیری یافت شد")
            
            # 2. پردازش هر رکورد بانکی
            for bank_record in unreconciled_transfers:
                self._process_single_transfer(bank_record, selected_bank_id)
                
            logger.info("مغایرت‌گیری حواله‌ها تکمیل شد")
            return True
            
        except Exception as e:
            logger.error(f"خطا در مغایرت‌گیری حواله‌ها: {str(e)}")
            return False
            
    def _get_unreconciled_bank_transfers(self, selected_bank_id: int) -> List[Dict]:
        """
        دریافت حواله‌های بانکی مغایرت‌گیری نشده
        
        پارامترها:
            selected_bank_id: شناسه بانک
            
        خروجی:
            لیست حواله‌های مغایرت‌گیری نشده
        """
        try:
            return self.db_manager.get_unreconciled_bank_transfers(selected_bank_id)
            
        except Exception as e:
            logger.error(f"خطا در دریافت حواله‌های مغایرت‌گیری نشده: {str(e)}")
            return []
            
    def _process_single_transfer(self, bank_record: Dict, selected_bank_id: int) -> bool:
        """
        پردازش یک حواله بانکی
        
        پارامترها:
            bank_record: رکورد بانکی
            selected_bank_id: شناسه بانک
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            # تعیین جزئیات هدف
            target_amount, target_acc_entry_type = self._determine_transfer_target_details(bank_record)
            
            # نرمال‌سازی تاریخ بانکی
            normalized_date = date_utils.convert_bank_date_to_accounting_format(bank_record['Date'])
            
            # جستجوی اولیه در ورودی‌های حسابداری
            found_acc_records = self._search_accounting_entries_for_transfer(
                selected_bank_id, normalized_date, target_amount, target_acc_entry_type
            )
            
            # ارزیابی نتایج جستجو و مدیریت سناریوها
            return self._handle_transfer_search_results(bank_record, found_acc_records)
            
        except Exception as e:
            logger.error(f"خطا در پردازش حواله {bank_record.get('id')}: {str(e)}")
            return False
            
    def _determine_transfer_target_details(self, bank_record: Dict) -> tuple:
        """
        تعیین جزئیات هدف برای حواله
        
        پارامترها:
            bank_record: رکورد بانکی
            
        خروجی:
            tuple شامل (مبلغ هدف، نوع ورودی حسابداری)
        """
        if bank_record['Transaction_Type_Bank'] == 'Received Transfer':
            target_amount = bank_record['Deposit_Amount']
            target_acc_entry_type = 'حواله/فيش دريافتني'
        else:  # Paid Transfer
            target_amount = bank_record['Withdrawal_Amount']
            target_acc_entry_type = 'حواله/فیش پرداختني'
            
        return target_amount, target_acc_entry_type
        
    def _search_accounting_entries_for_transfer(self, selected_bank_id: int, 
                                              normalized_date: str, target_amount: float, 
                                              target_acc_entry_type: str) -> List[Dict]:
        """
        جستجوی ورودی‌های حسابداری برای حواله
        
        پارامترها:
            selected_bank_id: شناسه بانک
            normalized_date: تاریخ نرمال‌سازی شده
            target_amount: مبلغ هدف
            target_acc_entry_type: نوع ورودی حسابداری
            
        خروجی:
            لیست ورودی‌های حسابداری یافت شده
        """
        try:
            return self.db_manager.search_accounting_entries_for_transfer(
                selected_bank_id, normalized_date, target_amount, target_acc_entry_type
            )
            
        except Exception as e:
            logger.error(f"خطا در جستجوی ورودی‌های حسابداری: {str(e)}")
            return []
            
    def _handle_transfer_search_results(self, bank_record: Dict, found_acc_records: List[Dict]) -> bool:
        """
        مدیریت نتایج جستجوی حواله
        
        پارامترها:
            bank_record: رکورد بانکی
            found_acc_records: ورودی‌های حسابداری یافت شده
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            if len(found_acc_records) == 1:
                # سناریو 1: تطابق یکتا
                return self._handle_unique_transfer_match(bank_record, found_acc_records[0])
                
            elif len(found_acc_records) > 1:
                # سناریو 2: تطابق چندگانه - جستجوی ثانویه
                return self._handle_multiple_transfer_matches(bank_record, found_acc_records)
                
            else:
                # هیچ تطابقی یافت نشد
                logger.warning(f"هیچ تطابقی برای حواله {bank_record['id']} یافت نشد")
                return False
                
        except Exception as e:
            logger.error(f"خطا در مدیریت نتایج جستجوی حواله: {str(e)}")
            return False
            
    def _handle_unique_transfer_match(self, bank_record: Dict, matching_acc_record: Dict) -> bool:
        """
        مدیریت تطابق یکتا حواله
        
        پارامترها:
            bank_record: رکورد بانکی
            matching_acc_record: رکورد حسابداری تطبیق یافته
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            # به‌روزرسانی وضعیت مغایرت‌گیری
            self.db_manager.update_bank_transaction_reconciled_status(bank_record['id'], 1)
            self.db_manager.update_accounting_entry_reconciled_status(matching_acc_record['id'], 1)
            
            # درج در نتایج مغایرت‌گیری
            self.db_manager.insert_reconciliation_result(
                bank_transaction_id=bank_record['id'],
                accounting_entry_id=matching_acc_record['id'],
                pos_transaction_id=None,
                reconciliation_type="Match",
                reconciliation_date=date_utils.get_current_persian_date(),
                notes="حواله / فیش: تطابق یکتا بر اساس تاریخ و مبلغ."
            )
            
            logger.info(f"تطابق یکتا حواله {bank_record['id']} با موفقیت انجام شد")
            return True
            
        except Exception as e:
            logger.error(f"خطا در مدیریت تطابق یکتا حواله: {str(e)}")
            return False
            
    def _handle_multiple_transfer_matches(self, bank_record: Dict, found_acc_records: List[Dict]) -> bool:
        """
        مدیریت تطابق چندگانه حواله
        
        پارامترها:
            bank_record: رکورد بانکی
            found_acc_records: ورودی‌های حسابداری یافت شده
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            # جستجوی ثانویه بر اساس شماره پیگیری
            potential_matches = self._secondary_search_by_tracking_number(bank_record, found_acc_records)
            
            if len(potential_matches) == 1:
                # تطابق چندگانه حل شده با شماره پیگیری
                return self._handle_resolved_multiple_match(bank_record, potential_matches[0])
                
            else:
                # نیاز به مغایرت‌گیری دستی
                return self._trigger_manual_reconciliation_ui(bank_record, found_acc_records, 'transfer')
                
        except Exception as e:
            logger.error(f"خطا در مدیریت تطابق چندگانه حواله: {str(e)}")
            return False
            
    def _secondary_search_by_tracking_number(self, bank_record: Dict, found_acc_records: List[Dict]) -> List[Dict]:
        """
        جستجوی ثانویه بر اساس شماره پیگیری
        
        پارامترها:
            bank_record: رکورد بانکی
            found_acc_records: ورودی‌های حسابداری یافت شده
            
        خروجی:
            لیست تطابق‌های احتمالی
        """
        potential_matches = []
        
        for acc_record in found_acc_records:
            if (acc_record.get('Account_Reference_Suffix') and 
                bank_record.get('Description_Bank') and 
                acc_record['Account_Reference_Suffix'] in bank_record['Description_Bank']):
                potential_matches.append(acc_record)
                
        return potential_matches
        
    def _handle_resolved_multiple_match(self, bank_record: Dict, final_matching_acc_record: Dict) -> bool:
        """
        مدیریت تطابق چندگانه حل شده
        
        پارامترها:
            bank_record: رکورد بانکی
            final_matching_acc_record: رکورد حسابداری نهایی تطبیق یافته
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            # به‌روزرسانی وضعیت مغایرت‌گیری
            self.db_manager.update_bank_transaction_reconciled_status(bank_record['id'], 1)
            self.db_manager.update_accounting_entry_reconciled_status(final_matching_acc_record['id'], 1)
            
            # درج در نتایج مغایرت‌گیری
            self.db_manager.insert_reconciliation_result(
                bank_transaction_id=bank_record['id'],
                accounting_entry_id=final_matching_acc_record['id'],
                pos_transaction_id=None,
                reconciliation_type="Match",
                reconciliation_date=date_utils.get_current_persian_date(),
                notes="حواله / فیش: تطابق چندگانه حل شده با شماره پیگیری."
            )
            
            logger.info(f"تطابق چندگانه حواله {bank_record['id']} با شماره پیگیری حل شد")
            return True
            
        except Exception as e:
            logger.error(f"خطا در مدیریت تطابق چندگانه حل شده: {str(e)}")
            return False
            
    def _trigger_manual_reconciliation_ui(self, bank_record: Dict, found_acc_records: List[Dict], reconciliation_type: str) -> bool:
        """
        فعال‌سازی رابط کاربری برای مغایرت‌گیری دستی
        
        پارامترها:
            bank_record: رکورد بانکی
            found_acc_records: ورودی‌های حسابداری یافت شده
            reconciliation_type: نوع مغایرت‌گیری
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            # فراخوانی callback برای UI دستی
            if hasattr(self, 'ui_callback_manual_reconciliation_needed'):
                self.ui_callback_manual_reconciliation_needed(bank_record, found_acc_records, reconciliation_type)
                logger.info(f"درخواست مغایرت‌گیری دستی برای حواله {bank_record['id']} ارسال شد")
                return True
            else:
                logger.warning(f"callback مغایرت‌گیری دستی تعریف نشده - حواله {bank_record['id']} نادیده گرفته شد")
                return False
                
        except Exception as e:
            logger.error(f"خطا در فعال‌سازی مغایرت‌گیری دستی: {str(e)}")
            return False
            
    def handle_manual_selection(self, bank_record_id: int, selected_acc_id: int, reconciliation_type: str) -> bool:
        """
        مدیریت انتخاب دستی کاربر
        
        پارامترها:
            bank_record_id: شناسه رکورد بانکی
            selected_acc_id: شناسه ورودی حسابداری انتخاب شده
            reconciliation_type: نوع مغایرت‌گیری
            
        خروجی:
            True در صورت موفقیت
        """
        try:
            # به‌روزرسانی وضعیت مغایرت‌گیری
            self.db_manager.update_bank_transaction_reconciled_status(bank_record_id, 1)
            self.db_manager.update_accounting_entry_reconciled_status(selected_acc_id, 1)
            
            # درج در نتایج مغایرت‌گیری
            self.db_manager.insert_reconciliation_result(
                bank_transaction_id=bank_record_id,
                accounting_entry_id=selected_acc_id,
                pos_transaction_id=None,
                reconciliation_type="Manual Match",
                reconciliation_date=date_utils.get_current_persian_date(),
                notes=f"مغایرت‌گیری دستی {reconciliation_type}"
            )
            
            logger.info(f"انتخاب دستی برای رکورد {bank_record_id} با موفقیت ثبت شد")
            return True
            
        except Exception as e:
            logger.error(f"خطا در مدیریت انتخاب دستی: {str(e)}")
            return False

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