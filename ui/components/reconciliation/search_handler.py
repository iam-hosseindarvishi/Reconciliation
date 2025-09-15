"""
Search Handler Module
ماژول مدیریت جستجو - جدا شده از manual_reconciliation_tab.py
"""
import logging
from datetime import datetime, timedelta
from tkinter import messagebox
from utils.helpers import persian_to_gregorian
from utils.constants import TransactionTypes
from database.accounting_repository import (
    get_transactions_by_date_and_type as get_unreconciled_accounting_records_by_date,
    get_transactions_advanced_search
)


class SearchHandler:
    """کلاس مدیریت جستجوی رکوردها"""
    
    def __init__(self, banks_dict, logger=None):
        self.banks_dict = banks_dict
        self.logger = logger or logging.getLogger(__name__)
    
    def search_accounting_records(self, selected_bank_record=None, advanced_search_params=None):
        """
        جستجوی رکوردهای حسابداری مرتبط با رکورد بانک انتخاب شده یا بر اساس پارامترهای پیشرفته
        
        Args:
            selected_bank_record: رکورد بانک انتخاب شده
            advanced_search_params: پارامترهای جستجوی پیشرفته
            
        Returns:
            list: لیست رکوردهای حسابداری یافت شده
        """
        try:
            if advanced_search_params:
                return self._advanced_search(advanced_search_params, selected_bank_record)
            elif selected_bank_record:
                return self._standard_search(selected_bank_record)
            else:
                raise ValueError("پارامترهای جستجو مشخص نشده است")
                
        except Exception as e:
            error_message = f"خطا در جستجوی رکوردهای حسابداری: {str(e)}"
            self.logger.error(error_message)
            messagebox.showerror("خطا", error_message)
            return []
    
    def _standard_search(self, selected_bank_record):
        """جستجوی استاندارد بر اساس رکورد بانک انتخاب شده"""
        try:
            # دریافت تاریخ رکورد بانک
            bank_date = selected_bank_record['transaction_date']
            
            # دریافت نوع تراکنش بانک بر اساس نوع تراکنش موجود در رکورد بانک
            bank_transaction_type = selected_bank_record.get('transaction_type', '')
            
            # تبدیل نوع تراکنش بانک به نوع تراکنش حسابداری
            transaction_type = self._convert_bank_transaction_type(bank_transaction_type)
            
            if transaction_type == 'Unknown':
                self.logger.warning(f"نوع تراکنش بانک ناشناس: {bank_transaction_type}")
            
            # اگر نوع تراکنش POS است، تاریخ را یک روز کاهش می‌دهیم
            search_date = bank_date
            if transaction_type == 'Pos':
                date_obj = datetime.strptime(bank_date, '%Y-%m-%d')
                prev_date_obj = date_obj - timedelta(days=1)
                search_date = prev_date_obj.strftime('%Y-%m-%d')
                self.logger.info(f"تاریخ جستجو برای تراکنش POS از {bank_date} به {search_date} تغییر کرد")
            
            # دریافت شناسه بانک (فرض می‌کنیم bank_id در دسترس است)
            bank_id = selected_bank_record.get('bank_id')
            if not bank_id:
                # اگر bank_id مستقیم در دسترس نیست، باید از جای دیگری دریافت کنیم
                raise ValueError("شناسه بانک در رکورد موجود نیست")
            
            try:
                # دریافت رکوردهای حسابداری مغایرت‌گیری نشده در تاریخ رکورد بانک
                accounting_records = get_unreconciled_accounting_records_by_date(
                    bank_id=bank_id,
                    start_date=search_date,
                    end_date=search_date,
                    transaction_type=transaction_type
                )
                
                self.logger.info(f"تعداد {len(accounting_records)} رکورد حسابداری با جستجوی استاندارد یافت شد")
                return accounting_records
                
            except TypeError as e:
                # اگر خطای پارامتر رخ داد، با روش دیگری امتحان کنیم
                self.logger.warning(f"خطا در فراخوانی تابع با پارامترهای نام‌گذاری شده: {str(e)}")
                try:
                    if bank_id is None:
                        raise ValueError("شناسه بانک نمی‌تواند خالی باشد")
                    
                    accounting_records = get_unreconciled_accounting_records_by_date(
                        bank_id, search_date, search_date, transaction_type
                    )
                    return accounting_records
                    
                except Exception as e2:
                    self.logger.error(f"خطا در جستجوی رکوردهای حسابداری: {str(e2)}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"خطا در جستجوی استاندارد: {str(e)}")
            return []
    
    def _advanced_search(self, advanced_params, selected_bank_record=None):
        """جستجوی پیشرفته با پارامترهای سفارشی"""
        try:
            search_params = {}
            
            # اگر تاریخ سفارشی وارد شده باشد
            custom_date = advanced_params.get('custom_date', '').strip()
            if custom_date:
                try:
                    # تبدیل تاریخ شمسی به میلادی
                    search_params['custom_date'] = persian_to_gregorian(custom_date)
                except Exception as e:
                    messagebox.showerror("خطا", f"فرمت تاریخ نامعتبر است: {str(e)}")
                    return []
            
            # اگر بانک انتخاب شده باشد
            selected_search_bank = advanced_params.get('bank_name')
            if selected_search_bank and selected_search_bank in self.banks_dict:
                search_params['bank_id'] = self.banks_dict[selected_search_bank]
            elif selected_bank_record:
                # استفاده از بانک رکورد انتخاب شده
                search_params['bank_id'] = selected_bank_record.get('bank_id')
            
            # اگر نوع تراکنش انتخاب شده باشد
            selected_transaction_type = advanced_params.get('transaction_type')
            if selected_transaction_type:
                search_params['transaction_type'] = selected_transaction_type
            elif selected_bank_record:
                # استفاده از نوع تراکنش رکورد بانک انتخاب شده
                bank_transaction_type = selected_bank_record.get('transaction_type', '')
                search_params['transaction_type'] = self._convert_bank_transaction_type(bank_transaction_type)
            
            # اگر رکورد بانک انتخاب شده باشد، مبلغ و شماره پیگیری را هم اضافه کنیم
            if selected_bank_record:
                search_params['amount'] = selected_bank_record.get('amount')
                search_params['tracking_number'] = selected_bank_record.get('extracted_tracking_number')
            
            # استفاده از تابع جستجوی پیشرفته
            accounting_records = get_transactions_advanced_search(search_params)
            
            self.logger.info(f"تعداد {len(accounting_records)} رکورد حسابداری با جستجوی پیشرفته یافت شد")
            return accounting_records
            
        except Exception as e:
            self.logger.error(f"خطا در جستجوی پیشرفته: {str(e)}")
            return []
    
    def _convert_bank_transaction_type(self, bank_transaction_type):
        """تبدیل نوع تراکنش بانک به نوع تراکنش حسابداری"""
        try:
            # استفاده از constants جدید
            conversion_map = {
                # POS transactions
                TransactionTypes.RECEIVED_POS: 'Pos',
                'received_pos': 'Pos',
                
                # Transfer transactions
                TransactionTypes.PAID_TRANSFER: 'Paid Transfer',
                'paid_transfer': 'Paid Transfer',
                TransactionTypes.RECEIVED_TRANSFER: 'Received Transfer',
                'received_transfer': 'Received Transfer',
                
                # Check transactions
                TransactionTypes.RECEIVED_CHECK: 'Received Check',
                'received_check': 'Received Check',
                TransactionTypes.PAID_CHECK: 'Paid Check',
                'paid_check': 'Paid Check',
                
                # Bank fees
                TransactionTypes.BANK_FEES: 'Bank Fees',
                'bank_fee': 'Bank Fees'
            }
            
            return conversion_map.get(bank_transaction_type, 'Unknown')
            
        except Exception as e:
            self.logger.error(f"خطا در تبدیل نوع تراکنش: {str(e)}")
            return 'Unknown'
    
    def validate_search_params(self, advanced_params):
        """اعتبارسنجی پارامترهای جستجوی پیشرفته"""
        try:
            errors = []
            
            # بررسی تاریخ سفارشی
            custom_date = advanced_params.get('custom_date', '').strip()
            if custom_date:
                try:
                    persian_to_gregorian(custom_date)
                except Exception:
                    errors.append("فرمت تاریخ نامعتبر است")
            
            # بررسی بانک انتخاب شده
            selected_bank = advanced_params.get('bank_name')
            if selected_bank and selected_bank not in self.banks_dict:
                errors.append("بانک انتخاب شده نامعتبر است")
            
            # بررسی نوع تراکنش
            valid_transaction_types = [
                'Pos', 'Received Transfer', 'Paid Transfer', 
                'Received Check', 'Paid Check', 'Bank Fees'
            ]
            selected_type = advanced_params.get('transaction_type')
            if selected_type and selected_type not in valid_transaction_types:
                errors.append("نوع تراکنش انتخاب شده نامعتبر است")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            self.logger.error(f"خطا در اعتبارسنجی پارامترهای جستجو: {str(e)}")
            return False, [f"خطا در اعتبارسنجی: {str(e)}"]
    
    def get_search_suggestions(self, bank_record):
        """دریافت پیشنهادات جستجو بر اساس رکورد بانک"""
        try:
            if not bank_record:
                return {}
            
            suggestions = {
                'recommended_date': bank_record.get('transaction_date'),
                'recommended_type': self._convert_bank_transaction_type(
                    bank_record.get('transaction_type', '')
                ),
                'amount_range': {
                    'min': float(bank_record.get('amount', 0)) * 0.9,  # 10% tolerance
                    'max': float(bank_record.get('amount', 0)) * 1.1
                },
                'tracking_number': bank_record.get('extracted_tracking_number', ''),
                'search_tips': self._get_search_tips(bank_record)
            }
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"خطا در تولید پیشنهادات جستجو: {str(e)}")
            return {}
    
    def _get_search_tips(self, bank_record):
        """دریافت نکات جستجو بر اساس رکورد بانک"""
        tips = []
        
        transaction_type = bank_record.get('transaction_type', '')
        
        if 'pos' in transaction_type.lower():
            tips.append("برای تراکنش‌های POS، تاریخ جستجو یک روز قبل از تاریخ بانک تنظیم شده است")
        
        if bank_record.get('amount', 0) > 1000000:  # مبالغ بالا
            tips.append("برای مبالغ بالا، احتمال وجود کارمزد را در نظر بگیرید")
        
        if not bank_record.get('extracted_tracking_number'):
            tips.append("شماره پیگیری این رکورد خالی است، جستجو بر اساس مبلغ و تاریخ انجام می‌شود")
        
        return tips
