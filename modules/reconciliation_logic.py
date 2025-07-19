#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول منطق مغایرت‌گیری
این ماژول مسئول انجام عملیات مغایرت‌گیری بین داده‌های بانک، پوز و حسابداری است.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable

from modules.database_manager import DatabaseManager
from modules.logger import get_logger

# ایجاد شیء لاگر
logger = get_logger(__name__)

def validate_persian_date(date_str: str) -> bool:
    """
    اعتبارسنجی تاریخ شمسی
    
    پارامترها:
        date_str: رشته تاریخ به فرمت YYYY/MM/DD
        
    خروجی:
        True اگر تاریخ معتبر باشد، در غیر این صورت False
    """
    try:
        if not date_str or not isinstance(date_str, str):
            return False
            
        # بررسی فرمت کلی
        if not re.match(r'^\d{4}/\d{2}/\d{2}$', date_str):
            return False
            
        parts = date_str.split('/')
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        
        # بررسی محدوده سال (1300-1500)
        if year < 1300 or year > 1500:
            return False
            
        # بررسی محدوده ماه (1-12)
        if month < 1 or month > 12:
            return False
            
        # تعداد روزهای هر ماه در تقویم شمسی
        days_in_month = {
            1: 31, 2: 31, 3: 31, 4: 31, 5: 31, 6: 31,  # بهار و تابستان
            7: 30, 8: 30, 9: 30, 10: 30, 11: 30,        # پاییز
            12: 29  # زمستان (اسفند)
        }
        
        # بررسی سال کبیسه برای ماه اسفند
        if month == 12:
            # در تقویم شمسی، سال کبیسه هر 4 سال یکبار است
            # اما قانون دقیق‌تر: سال % 33 در چرخه 128 ساله
            # برای سادگی از قانون ساده استفاده می‌کنیم
            if is_persian_leap_year(year):
                days_in_month[12] = 30
                
        # بررسی محدوده روز
        max_days = days_in_month.get(month, 31)
        if day < 1 or day > max_days:
            return False
            
        return True
        
    except (ValueError, IndexError):
        return False

def is_persian_leap_year(year: int) -> bool:
    """
    تشخیص سال کبیسه در تقویم شمسی
    
    پارامترها:
        year: سال شمسی
        
    خروجی:
        True اگر سال کبیسه باشد
    """
    # الگوریتم ساده برای تشخیص سال کبیسه شمسی
    # هر 4 سال یکبار کبیسه است، اما با استثناهایی
    cycle_year = year % 128
    leap_years_in_cycle = [1, 5, 9, 13, 17, 22, 26, 30, 34, 38, 42, 46, 50, 55, 59, 63, 67, 71, 75, 79, 83, 88, 92, 96, 100, 104, 108, 112, 116, 121, 125]
    return cycle_year in leap_years_in_cycle

def safe_parse_persian_date(date_str: str) -> Optional[datetime]:
    """
    پارس امن تاریخ شمسی با اعتبارسنجی
    
    پارامترها:
        date_str: رشته تاریخ
        
    خروجی:
        شیء datetime یا None در صورت خطا
    """
    if not validate_persian_date(date_str):
        logger.error(f"تاریخ شمسی نامعتبر: {date_str}")
        return None
        
    # تلاش برای پارس کردن تاریخ با فرمت‌های مختلف
    for date_format in ['%Y/%m/%d', '%Y-%m-%d', '%d/%m/%Y']:
        try:
            return datetime.strptime(str(date_str), date_format)
        except ValueError:
            continue
            
    logger.error(f"فرمت تاریخ نامعتبر: {date_str}")
    return None


class ReconciliationEngine:
    """
    موتور مغایرت‌گیری برای تطبیق داده‌های بانک، پوز و حسابداری
    """
    
    def __init__(self, user_confirmation_callback: Optional[Callable] = None, 
                 manual_selection_callback: Optional[Callable] = None):
        """
        مقداردهی اولیه کلاس ReconciliationEngine
        
        پارامترها:
            user_confirmation_callback: تابع برای تأیید کاربر (اختیاری)
            manual_selection_callback: تابع برای انتخاب دستی کاربر (اختیاری)
        """
        self.db_manager = DatabaseManager()
        self.user_confirmation_callback = user_confirmation_callback
        self.manual_selection_callback = manual_selection_callback
        self.reconciliation_results = []
        
    def start_reconciliation(self, selected_bank_id: int) -> Dict[str, Any]:
        """
        شروع فرآیند مغایرت‌گیری برای بانک انتخاب شده
        
        پارامترها:
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            دیکشنری حاوی نتایج مغایرت‌گیری
        """
        logger.info(f"شروع فرآیند مغایرت‌گیری برای بانک با شناسه {selected_bank_id}...")
        
        # دریافت تراکنش‌های بانکی مغایرت‌گیری نشده برای بانک انتخاب شده
        bank_transactions = self.db_manager.get_unreconciled_bank_transactions(selected_bank_id)
        
        logger.info(f"تعداد تراکنش‌های بانکی مغایرت‌گیری نشده: {len(bank_transactions)}")
        
        # پردازش هر تراکنش بانکی
        processed_count = 0
        successful_reconciliations = 0
        
        logger.info(f"🔄 شروع پردازش {len(bank_transactions)} تراکنش بانکی")
        
        for i, bank_record in enumerate(bank_transactions, 1):
            try:
                transaction_type = bank_record.get('Transaction_Type_Bank')
                payer_receiver = bank_record.get('Payer_Receiver', '')
                
                logger.info(f"📊 تراکنش {i}/{len(bank_transactions)} - ID: {bank_record.get('id')}, نوع: {transaction_type}")
                logger.info(f"💰 مبلغ واریز: {bank_record.get('Deposit_Amount', 0)}, مبلغ برداشت: {bank_record.get('Withdrawal_Amount', 0)}")
                logger.info(f"👤 پرداخت‌کننده/دریافت‌کننده: {payer_receiver}")
                
                success = False
                
                # مغایرت‌گیری واریز پوز شاپرک
                if transaction_type == 'POS Deposit' or (payer_receiver and 'مرکزشاپرک' in payer_receiver):
                    logger.info(f"🏪 پردازش واریز پوز شاپرک")
                    success = self._reconcile_shaparak_pos_deposit(bank_record, selected_bank_id)
                
                # مغایرت‌گیری انتقال دریافتی
                elif transaction_type == 'Received Transfer':
                    logger.info(f"📥 پردازش انتقال دریافتی")
                    success = self._reconcile_transfer_deposit(bank_record, selected_bank_id)
                
                # مغایرت‌گیری چک دریافتی
                elif transaction_type == 'Received Check':
                    logger.info(f"💰 پردازش چک دریافتی")
                    success = self._reconcile_received_check(bank_record, selected_bank_id)
                
                # مغایرت‌گیری چک پرداختی
                elif transaction_type == 'Paid Check':
                    logger.info(f"💸 پردازش چک پرداختی")
                    success = self._reconcile_paid_check(bank_record, selected_bank_id)
                
                # مغایرت‌گیری انتقال پرداختی
                elif transaction_type == 'Paid Transfer':
                    logger.info(f"📤 پردازش انتقال پرداختی")
                    success = self._reconcile_transfer_payment(bank_record, selected_bank_id)
                
                # سایر انواع تراکنش‌ها
                else:
                    logger.warning(f"❓ نوع تراکنش {transaction_type} پشتیبانی نمی‌شود.")
                    success = False
                
                if success:
                    successful_reconciliations += 1
                    logger.info(f"مغایرت‌گیری موفق برای تراکنش شناسه {bank_record.get('id')}")
                else:
                    logger.warning(f"مغایرت‌گیری ناموفق برای تراکنش شناسه {bank_record.get('id')}")
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"خطا در پردازش تراکنش شناسه {bank_record.get('id')}: {str(e)}")
                continue
        
        # محاسبه آمار نهایی
        results = {
            "bank_id": selected_bank_id,
            "total_processed": processed_count,
            "successful_reconciliations": successful_reconciliations,
            "failed_reconciliations": processed_count - successful_reconciliations,
            "statistics": self.db_manager.get_reconciliation_statistics()
        }
        
        logger.info(f"فرآیند مغایرت‌گیری تکمیل شد. پردازش شده: {processed_count}, موفق: {successful_reconciliations}")
        return results
    
    def _reconcile_shaparak_pos_deposit(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
        """
        مغایرت‌گیری واریز پوز شاپرک
        
        پارامترها:
            bank_record: رکورد تراکنش بانکی
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            موفقیت عملیات
        """
        logger.info(f"شروع مغایرت‌گیری واریز پوز شاپرک برای تراکنش {bank_record.get('id')}")
        
        # استخراج شناسه ترمینال
        terminal_id = bank_record.get('Extracted_Shaparak_Terminal_ID')
        if not terminal_id:
            logger.warning(f"شناسه ترمینال یافت نشد برای تراکنش {bank_record.get('id')}")
            self._mark_bank_record_reconciled(bank_record.get('id'), "شناسه ترمینال یافت نشد")
            return True
        
        # مرحله 1: بررسی وجود داده‌های ترمینال
        pos_transactions = self.db_manager.get_pos_transactions_by_terminal(selected_bank_id, terminal_id)
        
        if not pos_transactions:
            logger.warning(f"⚠️ داده‌های پوز برای ترمینال {terminal_id} یافت نشد")
            self._mark_bank_record_reconciled(bank_record.get('id'), "داده‌های پوز موجود نیست")
            return True
        
        # مرحله 2: بررسی وجود سرجمع در حسابداری
        bank_date = bank_record.get('Date')
        aggregate_entry = self._find_aggregate_accounting_entry(selected_bank_id, terminal_id, bank_date)
        
        if aggregate_entry:
            # درخواست تأیید کاربر برای سرجمع
            if self.user_confirmation_callback:
                user_confirmed = self.user_confirmation_callback(
                    f"آیا این ترمینال ({terminal_id}) در تاریخ {bank_date} را به عنوان سرجمع علامت بزند؟"
                )
                
                if user_confirmed:
                    return self._process_aggregate_reconciliation(bank_record, selected_bank_id, terminal_id, aggregate_entry)
        
        # مرحله 3: مغایرت‌گیری تفصیلی پوز با حسابداری
        logger.info(f"🔄 شروع مغایرت‌گیری تفصیلی پوز با حسابداری")
        return self._process_detailed_pos_reconciliation(bank_record, selected_bank_id, terminal_id)
    
    def _find_aggregate_accounting_entry(self, selected_bank_id: int, terminal_id: str, bank_date: str) -> Optional[Dict[str, Any]]:
        """
        یافتن ورودی سرجمع حسابداری
        
        پارامترها:
            selected_bank_id: شناسه بانک
            terminal_id: شناسه ترمینال
            bank_date: تاریخ بانک
            
        خروجی:
            ورودی حسابداری سرجمع یا None
        """
        accounting_entries = self.db_manager.get_unreconciled_accounting_entries(selected_bank_id)
        
        for entry in accounting_entries:
            if (entry.get('Entry_Type_Acc') == 'پوز دریافتنی' and
                entry.get('Account_Reference_Suffix') == terminal_id and
                'سرجمع' in entry.get('Description_Notes_Acc', '')):
                return entry
        
        return None
    
    def _process_aggregate_reconciliation(self, bank_record: Dict[str, Any], selected_bank_id: int, 
                                        terminal_id: str, aggregate_entry: Dict[str, Any]) -> bool:
        """
        پردازش مغایرت‌گیری سرجمع
        
        پارامترها:
            bank_record: رکورد بانک
            selected_bank_id: شناسه بانک
            terminal_id: شناسه ترمینال
            aggregate_entry: ورودی سرجمع حسابداری
            
        خروجی:
            موفقیت عملیات
        """
        # محاسبه مجموع مبالغ پوز برای روز قبل
        try:
            date_str = bank_record.get('Date')
            if not date_str:
                logger.error("تاریخ بانک خالی است")
                return False
                
            # استفاده از تابع امن پارس تاریخ
            bank_date = safe_parse_persian_date(date_str)
            if not bank_date:
                logger.error(f"تاریخ بانک نامعتبر: {date_str}")
                return False
                
            pos_date = (bank_date - timedelta(days=1)).strftime('%Y/%m/%d')
        except Exception as e:
            logger.error(f"خطا در پردازش تاریخ بانک: {str(e)}")
            return False
        
        pos_transactions = self.db_manager.get_pos_transactions_by_terminal_date(selected_bank_id, terminal_id, pos_date)
        total_pos_amount = sum(float(tx.get('Transaction_Amount', 0)) for tx in pos_transactions)
        
        # مقایسه مبالغ
        aggregate_amount = float(aggregate_entry.get('Debit', 0) or aggregate_entry.get('Credit', 0))
        
        if abs(total_pos_amount - aggregate_amount) < 0.01:
            # علامت‌گذاری همه تراکنش‌های پوز و ورودی حسابداری به عنوان مغایرت‌گیری شده
            for pos_tx in pos_transactions:
                self.db_manager.update_reconciliation_status('PosTransactions', pos_tx.get('id'), True)
            
            self.db_manager.update_reconciliation_status('AccountingEntries', aggregate_entry.get('id'), True)
            
            # ثبت نتیجه مغایرت‌گیری
            self.db_manager.record_reconciliation_result(
                bank_id=bank_record.get('id'),
                pos_id=None,
                accounting_id=aggregate_entry.get('id'),
                reconciliation_type="Shaparak-POS-Aggregate",
                notes=f"سرجمع ترمینال {terminal_id} - مبلغ: {total_pos_amount}"
            )
            
            logger.info(f"مغایرت‌گیری سرجمع موفق - ترمینال: {terminal_id}, مبلغ: {total_pos_amount}")
        else:
            logger.warning(f"مبلغ سرجمع پوز همخوانی ندارد - پوز: {total_pos_amount}, حسابداری: {aggregate_amount}")
        
        # علامت‌گذاری رکورد بانک
        self._mark_bank_record_reconciled(bank_record.get('id'), "پردازش سرجمع انجام شد")
        return True
    
    def _process_detailed_pos_reconciliation(self, bank_record: Dict[str, Any], selected_bank_id: int, terminal_id: str) -> bool:
        """
        پردازش مغایرت‌گیری تفصیلی پوز
        
        پارامترها:
            bank_record: رکورد بانک
            selected_bank_id: شناسه بانک
            terminal_id: شناسه ترمینال
            
        خروجی:
            موفقیت عملیات
        """
        # محاسبه تاریخ پوز (یک روز قبل از تاریخ بانک)
        try:
            date_str = bank_record.get('Date')
            if not date_str:
                logger.error("تاریخ بانک خالی است")
                return False
                
            # استفاده از تابع امن پارس تاریخ
            bank_date = safe_parse_persian_date(date_str)
            if not bank_date:
                logger.error(f"تاریخ بانک نامعتبر: {date_str}")
                return False
                
            pos_date = (bank_date - timedelta(days=1)).strftime('%Y/%m/%d')
        except Exception as e:
            logger.error(f"خطا در پردازش تاریخ بانک: {str(e)}")
            return False
        
        # دریافت تراکنش‌های پوز برای ترمینال و تاریخ مشخص
        pos_transactions = self.db_manager.get_pos_transactions_by_terminal_date(selected_bank_id, terminal_id, pos_date)
        logger.info(f"📱 تعداد تراکنش‌های پوز برای ترمینال {terminal_id} در تاریخ {pos_date}: {len(pos_transactions)}")
        
        # دریافت ورودی‌های حسابداری پوز دریافتنی
        accounting_entries = self._get_pos_accounting_entries(selected_bank_id)
        logger.info(f"📋 تعداد ورودی‌های حسابداری پوز دریافتنی: {len(accounting_entries)}")
        
        reconciled_count = 0
        
        for pos_record in pos_transactions:
            if self._reconcile_single_pos_transaction(pos_record, accounting_entries):
                reconciled_count += 1
        
        # علامت‌گذاری رکورد بانک
        self._mark_bank_record_reconciled(bank_record.get('id'), f"پردازش تفصیلی - {reconciled_count} مورد تطبیق")
        
        logger.info(f"مغایرت‌گیری تفصیلی تکمیل شد - {reconciled_count} مورد از {len(pos_transactions)} تطبیق یافت")
        return True
    
    def _get_pos_accounting_entries(self, selected_bank_id: int) -> List[Dict[str, Any]]:
        """
        دریافت ورودی‌های حسابداری مربوط به پوز
        
        پارامترها:
            selected_bank_id: شناسه بانک
            
        خروجی:
            لیست ورودی‌های حسابداری
        """
        all_entries = self.db_manager.get_unreconciled_accounting_entries(selected_bank_id)
        return [entry for entry in all_entries if entry.get('Entry_Type_Acc') == 'پوز دریافتنی']
    
    def _reconcile_single_pos_transaction(self, pos_record: Dict[str, Any], accounting_entries: List[Dict[str, Any]]) -> bool:
        """
        مغایرت‌گیری یک تراکنش پوز با ورودی‌های حسابداری
        
        پارامترها:
            pos_record: رکورد پوز
            accounting_entries: لیست ورودی‌های حسابداری
            
        خروجی:
            موفقیت عملیات
        """
        pos_amount = float(pos_record.get('Transaction_Amount', 0))
        pos_tracking = pos_record.get('POS_Tracking_Number', '')
        
        # استخراج 6 و 5 رقم آخر شماره پیگیری
        last_6_digits = pos_tracking[-6:] if len(pos_tracking) >= 6 else ''
        last_5_digits = pos_tracking[-5:] if len(pos_tracking) >= 5 else ''
        
        matching_entries = []
        
        # جستجو برای ورودی‌های منطبق
        logger.info(f"🔍 جستجو برای تطبیق پوز - مبلغ: {pos_amount}, پیگیری: {pos_tracking}")
        logger.info(f"🔢 6 رقم آخر: {last_6_digits}, 5 رقم آخر: {last_5_digits}")
        
        for entry in accounting_entries:
            entry_amount = float(entry.get('Debit', 0) or entry.get('Credit', 0))
            entry_suffix = entry.get('Account_Reference_Suffix', '')
            
            # بررسی تطابق مبلغ و پسوند
            if (abs(pos_amount - entry_amount) < 0.01 and
                (entry_suffix == last_6_digits or entry_suffix == last_5_digits)):
                logger.info(f"✅ تطبیق یافت شد - ورودی ID: {entry.get('id')}, مبلغ: {entry_amount}, پسوند: {entry_suffix}")
                matching_entries.append(entry)
            else:
                logger.debug(f"❌ تطبیق نیافت - ورودی ID: {entry.get('id')}, مبلغ: {entry_amount}, پسوند: {entry_suffix}")
        
        # پردازش نتایج تطبیق
        logger.info(f"📊 تعداد تطبیق‌های یافت شده: {len(matching_entries)}")
        
        if len(matching_entries) == 1:
            # یک تطبیق یافت شد
            entry = matching_entries[0]
            logger.info(f"✅ یک تطبیق یافت شد - ثبت تطبیق پوز-حسابداری")
            return self._record_pos_accounting_match(pos_record, entry)
        
        elif len(matching_entries) > 1:
            # چندین تطبیق یافت شد - نیاز به انتخاب دستی
            logger.warning(f"⚠️ چندین تطبیق یافت شد ({len(matching_entries)} مورد)")
            if self.manual_selection_callback:
                selected_entry = self.manual_selection_callback(pos_record, matching_entries)
                if selected_entry:
                    logger.info(f"👤 کاربر ورودی انتخاب کرد - ثبت تطبیق")
                    return self._record_pos_accounting_match(pos_record, selected_entry)
            
            logger.warning(f"❌ چندین تطبیق برای پوز {pos_record.get('id')} یافت شد - نیاز به انتخاب دستی")
            return False
        
        else:
            # هیچ تطبیقی یافت نشد
            logger.warning(f"❌ تطابق پوز با حسابداری یافت نشد - پوز ID: {pos_record.get('id')}")
            return False
    
    def _record_pos_accounting_match(self, pos_record: Dict[str, Any], accounting_entry: Dict[str, Any]) -> bool:
        """
        ثبت تطبیق پوز با حسابداری
        
        پارامترها:
            pos_record: رکورد پوز
            accounting_entry: ورودی حسابداری
            
        خروجی:
            موفقیت عملیات
        """
        logger.info(f"💾 شروع ثبت تطبیق پوز-حسابداری")
        logger.info(f"📝 پوز ID: {pos_record.get('id')}, حسابداری ID: {accounting_entry.get('id')}")
        logger.info(f"💰 مبلغ پوز: {pos_record.get('Transaction_Amount')}, پیگیری: {pos_record.get('POS_Tracking_Number')}")
        
        # علامت‌گذاری رکوردها به عنوان مغایرت‌گیری شده
        logger.info(f"🏷️ علامت‌گذاری رکورد پوز {pos_record.get('id')} به عنوان مغایرت‌گیری شده")
        self.db_manager.update_reconciliation_status('PosTransactions', pos_record.get('id'), True)
        
        logger.info(f"🏷️ علامت‌گذاری رکورد حسابداری {accounting_entry.get('id')} به عنوان مغایرت‌گیری شده")
        self.db_manager.update_reconciliation_status('AccountingEntries', accounting_entry.get('id'), True)
        
        # ثبت نتیجه مغایرت‌گیری
        logger.info(f"📊 ثبت نتیجه مغایرت‌گیری در جدول ReconciliationResults")
        success = self.db_manager.record_reconciliation_result(
            bank_id=None,
            pos_id=pos_record.get('id'),
            accounting_id=accounting_entry.get('id'),
            reconciliation_type="POS-Accounting",
            notes=f"مبلغ: {pos_record.get('Transaction_Amount')}, پیگیری پوز: {pos_record.get('POS_Tracking_Number')}"
        )
        
        if success:
            logger.info(f"✅ تطبیق موفق پوز-حسابداری: پوز ID {pos_record.get('id')}, حسابداری ID {accounting_entry.get('id')}")
        else:
            logger.error(f"❌ خطا در ثبت تطبیق پوز-حسابداری: پوز ID {pos_record.get('id')}, حسابداری ID {accounting_entry.get('id')}")
        
        return success
    
    def _reconcile_transfer_deposit(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
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
    
    def _reconcile_received_check(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
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
    
    def _reconcile_paid_check(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
        """
        مغایرت‌گیری چک پرداختی
        
        پارامترها:
            bank_record: رکورد تراکنش بانکی
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            موفقیت عملیات
        """
        logger.info(f"شروع مغایرت‌گیری چک پرداختی برای تراکنش {bank_record.get('id')}")
        
        bank_amount = float(bank_record.get('Withdrawal_Amount', 0))
        bank_description = bank_record.get('Description_Bank', '')
        
        # دریافت ورودی‌های حسابداری چک پرداختنی
        accounting_entries = self._get_check_accounting_entries(selected_bank_id, 'پرداختنی')
        logger.info(f"📋 تعداد ورودی‌های حسابداری چک پرداختنی: {len(accounting_entries)}")
        
        # جستجو برای تطبیق بر اساس مبلغ و شماره چک
        matching_entry = self._find_check_match(accounting_entries, bank_amount, bank_description, 'Credit')
        
        if matching_entry:
            return self._record_check_match(bank_record, matching_entry, 'چک پرداختی')
        else:
            logger.warning(f"تطابق چک پرداختی یافت نشد برای تراکنش {bank_record.get('id')}")
            self._mark_bank_record_reconciled(bank_record.get('id'), "تطابق چک پرداختی یافت نشد")
            return True
    
    def _reconcile_transfer_payment(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
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
    
    # متدهای قدیمی برای سازگاری با کد موجود
    def get_unreconciled_bank_transactions(self):
        """دریافت تراکنش‌های بانکی مغایرت‌گیری نشده"""
        return self.db_manager.get_unreconciled_bank_transactions()
    
    def get_unreconciled_pos_transactions(self):
        """دریافت تراکنش‌های پوز مغایرت‌گیری نشده"""
        return self.db_manager.get_unreconciled_pos_transactions()
    
    def get_unreconciled_accounting_entries(self):
        """دریافت ورودی‌های حسابداری مغایرت‌گیری نشده"""
        return self.db_manager.get_unreconciled_accounting_entries()
    
    def manual_reconcile(self, reconciliation_type: str, bank_id: Optional[int] = None, 
                        pos_id: Optional[int] = None, accounting_id: Optional[int] = None, 
                        notes: str = None) -> bool:
        """
        انجام مغایرت‌گیری دستی
        
        پارامترها:
            reconciliation_type: نوع مغایرت‌گیری
            bank_id: شناسه رکورد بانک (اختیاری)
            pos_id: شناسه رکورد پوز (اختیاری)
            accounting_id: شناسه رکورد حسابداری (اختیاری)
            notes: یادداشت‌ها (اختیاری)
            
        خروجی:
            موفقیت عملیات
        """
        logger.info(f"انجام مغایرت‌گیری دستی از نوع {reconciliation_type}...")
        
        # بررسی اعتبار نوع مغایرت‌گیری
        valid_types = ["Shaparak-POS", "Check", "Transfer", "POS-Accounting", "Manual"]
        if reconciliation_type not in valid_types:
            logger.error(f"نوع مغایرت‌گیری نامعتبر: {reconciliation_type}")
            return False
        
        # بررسی وجود حداقل دو مورد برای مغایرت‌گیری
        records_count = sum(1 for x in [bank_id, pos_id, accounting_id] if x is not None)
        if records_count < 2:
            logger.error("برای مغایرت‌گیری دستی، حداقل دو مورد از بانک، پوز یا حسابداری باید مشخص شود.")
            return False
        
        # ثبت نتیجه مغایرت‌گیری
        success = self.db_manager.record_reconciliation_result(
            bank_id=bank_id,
            pos_id=pos_id,
            accounting_id=accounting_id,
            reconciliation_type=reconciliation_type,
            notes=notes or "مغایرت‌گیری دستی"
        )
        
        if success:
            # علامت‌گذاری رکوردها به عنوان مغایرت‌گیری شده
            if bank_id:
                self.db_manager.update_reconciliation_status('BankTransactions', bank_id, True)
            if pos_id:
                self.db_manager.update_reconciliation_status('PosTransactions', pos_id, True)
            if accounting_id:
                self.db_manager.update_reconciliation_status('AccountingEntries', accounting_id, True)
            
            logger.info(f"مغایرت‌گیری دستی با موفقیت انجام شد. نوع: {reconciliation_type}, بانک ID: {bank_id}, پوز ID: {pos_id}, حسابداری ID: {accounting_id}")
        else:
            logger.error("خطا در انجام مغایرت‌گیری دستی.")
        
        return success