"""
Data Manager Module
ماژول مدیریت داده‌ها - جدا شده از manual_reconciliation_tab.py
"""
import logging
import traceback
from tkinter import messagebox
from utils.helpers import gregorian_to_persian
from utils.constants import TransactionTypes
from database.banks_repository import get_all_banks
from database.bank_transaction_repository import get_unreconciled_transactions_by_bank as get_unreconciled_bank_records


class DataManager:
    """کلاس مدیریت داده‌ها و رکوردها"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.banks_dict = {}
        self.bank_records = []
        self.accounting_records = []
    
    def load_banks(self):
        """
        بارگذاری لیست بانک‌ها از پایگاه داده
        
        Returns:
            tuple: (list of bank names, dict mapping names to IDs)
        """
        try:
            banks = get_all_banks()
            bank_names = []
            self.banks_dict = {}
            
            if not banks:
                self.logger.warning("هیچ بانکی در سیستم ثبت نشده است")
                return [], {}
            
            for bank in banks:
                bank_id = bank[0]  # شناسه بانک
                bank_name = bank[1]  # نام بانک
                bank_names.append(bank_name)
                self.banks_dict[bank_name] = bank_id
            
            self.logger.info(f"تعداد {len(banks)} بانک بارگذاری شد")
            return bank_names, self.banks_dict
            
        except Exception as e:
            error_message = f"خطا در بارگذاری لیست بانک‌ها: {str(e)}"
            self.logger.error(f"{error_message}\\n{traceback.format_exc()}")
            messagebox.showerror("خطا", error_message)
            return [], {}
    
    def load_bank_records(self, bank_name, show_fees=False):
        """
        بارگذاری رکوردهای مغایرت‌گیری نشده بانک انتخاب شده
        
        Args:
            bank_name: نام بانک
            show_fees: نمایش کارمزدها یا خیر
            
        Returns:
            tuple: (list of records, str status message)
        """
        try:
            if not bank_name:
                return [], "لطفاً یک بانک را انتخاب کنید"
            
            # دریافت شناسه بانک از دیکشنری بانک‌ها
            bank_id = self.banks_dict.get(bank_name)
            
            if not bank_id:
                return [], "بانک انتخاب شده یافت نشد"
            
            # دریافت رکوردهای مغایرت‌گیری نشده بانک
            self.bank_records = get_unreconciled_bank_records(bank_id)
            
            # فیلتر کردن رکوردهای کارمزد اگر چک باکس فعال نباشد
            filtered_records = []
            hidden_fee_count = 0
            
            for record in self.bank_records:
                # اگر رکورد کارمزد است و چک باکس فعال نیست، آن را نمایش نده
                if not show_fees and self._is_fee_transaction(record):
                    hidden_fee_count += 1
                    continue
                filtered_records.append(record)
            
            # تولید پیام وضعیت
            status_message = self._generate_status_message(
                bank_name, filtered_records, hidden_fee_count
            )
            
            self.logger.info(f"تعداد {len(filtered_records)} رکورد بانک نمایش داده شد")
            return filtered_records, status_message
            
        except Exception as e:
            error_message = f"خطا در نمایش رکوردهای بانک: {str(e)}"
            self.logger.error(f"{error_message}\\n{traceback.format_exc()}")
            messagebox.showerror("خطا", error_message)
            return [], error_message
    
    def _is_fee_transaction(self, record):
        """بررسی اینکه آیا رکورد مربوط به کارمزد است یا خیر"""
        try:
            transaction_type = record.get('transaction_type', '')
            return transaction_type == TransactionTypes.BANK_FEES
        except:
            return False
    
    def _generate_status_message(self, bank_name, filtered_records, hidden_fee_count):
        """تولید پیام وضعیت برای نمایش تعداد رکوردها"""
        if not filtered_records:
            if not self.bank_records:
                return f"هیچ رکورد مغایرت‌گیری نشده‌ای برای بانک {bank_name} یافت نشد"
            else:
                return "هیچ رکورد مغایرت‌گیری نشده‌ای برای نمایش وجود ندارد (کارمزدها پنهان شده‌اند)"
        else:
            filtered_count = len(filtered_records)
            if hidden_fee_count > 0:
                return f"تعداد {filtered_count} رکورد نمایش داده شده ({hidden_fee_count} رکورد کارمزد پنهان شده است)"
            else:
                return f"تعداد {filtered_count} رکورد مغایرت‌گیری نشده برای بانک {bank_name} یافت شد"
    
    def format_bank_record_for_display(self, record):
        """
        فرمت کردن رکورد بانک برای نمایش در جدول
        
        Args:
            record: رکورد بانک
            
        Returns:
            tuple: مقادیر فرمت شده برای نمایش در جدول
        """
        try:
            # تبدیل تاریخ میلادی به شمسی
            shamsi_date = gregorian_to_persian(record['transaction_date'])
            
            # فرمت‌بندی مبلغ
            amount = f"{record['amount']:,}"
            
            # وضعیت
            status = "مغایرت‌گیری نشده"
            
            # نوع تراکنش
            transaction_type = record.get('transaction_type', '')
            
            return (
                record['id'],
                record.get('extracted_tracking_number', ''),
                shamsi_date,
                amount,
                record.get('description', ''),
                transaction_type,
                record.get('depositor_name', ''),
                status
            )
            
        except Exception as e:
            self.logger.error(f"خطا در فرمت کردن رکورد بانک: {str(e)}")
            return tuple(['خطا'] * 8)
    
    def format_accounting_record_for_display(self, record):
        """
        فرمت کردن رکورد حسابداری برای نمایش در جدول
        
        Args:
            record: رکورد حسابداری
            
        Returns:
            tuple: مقادیر فرمت شده برای نمایش در جدول
        """
        try:
            # تبدیل تاریخ میلادی به شمسی
            shamsi_date = gregorian_to_persian(
                record.get('due_date', record.get('transaction_date', ''))
            )
            
            # فرمت‌بندی مبلغ
            amount = f"{record.get('transaction_amount', 0):,}"
            
            # نوع تراکنش
            type_text = record.get('transaction_type', '')
            
            # نام بانک
            bank_id = record.get('bank_id')
            bank_name = self._get_bank_name_by_id(bank_id)
            
            # تبدیل مقدار is_new_system به متن
            system_text = "سیستم جدید" if record.get('is_new_system', 0) == 1 else "سیستم قدیم"
            
            return (
                record['id'],
                record.get('transaction_number', ''),
                shamsi_date,
                amount,
                record.get('description', ''),
                type_text,
                bank_name,
                system_text
            )
            
        except Exception as e:
            self.logger.error(f"خطا در فرمت کردن رکورد حسابداری: {str(e)}")
            return tuple(['خطا'] * 8)
    
    def _get_bank_name_by_id(self, bank_id):
        """دریافت نام بانک بر اساس شناسه"""
        try:
            for bank_name, bid in self.banks_dict.items():
                if bid == bank_id:
                    return bank_name
            return "نامشخص"
        except:
            return "نامشخص"
    
    def find_bank_record_by_id(self, record_id):
        """
        یافتن رکورد بانک بر اساس شناسه
        
        Args:
            record_id: شناسه رکورد
            
        Returns:
            dict: رکورد بانک یا None
        """
        try:
            return next((r for r in self.bank_records if r['id'] == record_id), None)
        except Exception as e:
            self.logger.error(f"خطا در یافتن رکورد بانک: {str(e)}")
            return None
    
    def find_accounting_record_by_id(self, record_id):
        """
        یافتن رکورد حسابداری بر اساس شناسه
        
        Args:
            record_id: شناسه رکورد
            
        Returns:
            dict: رکورد حسابداری یا None
        """
        try:
            return next((r for r in self.accounting_records if r['id'] == record_id), None)
        except Exception as e:
            self.logger.error(f"خطا در یافتن رکورد حسابداری: {str(e)}")
            return None
    
    def get_bank_id_by_name(self, bank_name):
        """دریافت شناسه بانک بر اساس نام"""
        return self.banks_dict.get(bank_name)
    
    def get_all_bank_names(self):
        """دریافت لیست نام تمام بانک‌ها"""
        return list(self.banks_dict.keys())
    
    def get_banks_dict(self):
        """دریافت دیکشنری بانک‌ها"""
        return self.banks_dict
    
    def clear_records(self):
        """پاک کردن تمام رکوردها از حافظه"""
        self.bank_records = []
        self.accounting_records = []
    
    def set_accounting_records(self, records):
        """تنظیم رکوردهای حسابداری"""
        self.accounting_records = records or []
    
    def get_bank_records_count(self):
        """دریافت تعداد رکوردهای بانک"""
        return len(self.bank_records)
    
    def get_accounting_records_count(self):
        """دریافت تعداد رکوردهای حسابداری"""
        return len(self.accounting_records)
    
    def validate_bank_selection(self, bank_name):
        """اعتبارسنجی انتخاب بانک"""
        if not bank_name:
            return False, "لطفاً یک بانک را انتخاب کنید"
        
        if bank_name not in self.banks_dict:
            return False, "بانک انتخاب شده نامعتبر است"
        
        return True, "بانک معتبر است"
    
    def get_transaction_summary(self):
        """دریافت خلاصه‌ای از تراکنش‌ها"""
        try:
            summary = {
                'total_bank_records': len(self.bank_records),
                'total_accounting_records': len(self.accounting_records),
                'bank_amount_sum': sum(record.get('amount', 0) for record in self.bank_records),
                'accounting_amount_sum': sum(
                    record.get('transaction_amount', 0) for record in self.accounting_records
                )
            }
            
            # محاسبه اختلاف
            summary['difference'] = summary['bank_amount_sum'] - summary['accounting_amount_sum']
            
            # تحلیل نوع تراکنش‌ها
            bank_transaction_types = {}
            for record in self.bank_records:
                t_type = record.get('transaction_type', 'نامشخص')
                bank_transaction_types[t_type] = bank_transaction_types.get(t_type, 0) + 1
            
            summary['bank_transaction_types'] = bank_transaction_types
            
            return summary
            
        except Exception as e:
            self.logger.error(f"خطا در تولید خلاصه تراکنش‌ها: {str(e)}")
            return {}
