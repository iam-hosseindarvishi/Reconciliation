#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول مغایرت‌گیری واریز پوز شاپرک
این ماژول مسئول پردازش و مغایرت‌گیری تراکنش‌های واریز پوز شاپرک است.
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta

from modules.database_manager import DatabaseManager
from modules.logger import get_logger
from modules.reconciliation.utils import safe_parse_persian_date

# ایجاد شیء لاگر
logger = get_logger(__name__)

class PosDepositReconciliation:
    """
    کلاس مغایرت‌گیری واریز پوز شاپرک
    """
    
    def __init__(self, user_confirmation_callback: Optional[Callable] = None, 
                 manual_selection_callback: Optional[Callable] = None):
        """
        سازنده کلاس
        
        پارامترها:
            user_confirmation_callback: تابع برای تأیید کاربر (اختیاری)
            manual_selection_callback: تابع برای انتخاب دستی کاربر (اختیاری)
        """
        self.db_manager = DatabaseManager()
        self.user_confirmation_callback = user_confirmation_callback
        self.manual_selection_callback = manual_selection_callback
    
    def reconcile_shaparak_pos_deposit(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
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