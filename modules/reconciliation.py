#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول اصلی مغایرت‌گیری
این ماژول کلاس ReconciliationEngine را شامل می‌شود که تمام عملیات مغایرت‌گیری را هماهنگ می‌کند.
الگوریتم بازنویسی شده بر اساس مراحل آماده‌سازی، پردازش تکراری، نرمال‌سازی تاریخ و انواع مغایرت‌گیری
"""

from typing import Dict, List, Optional, Any

from modules.database_manager import DatabaseManager
from modules.logger import get_logger
import modules.utils as utils

# ایجاد شیء لاگر
logger = get_logger(__name__)

class ReconciliationEngine:
    def __init__(self, db_manager, ui_callbacks=None):
        self.db_manager = db_manager
        if ui_callbacks:
            self.ui_callback_manual_reconciliation_needed = ui_callbacks.get('manual_reconciliation')
            self.ui_callback_aggregate_confirmation = ui_callbacks.get('aggregate_confirmation')

    def start_reconciliation(self, selected_bank_id: int, transaction_types: Optional[List[str]] = None):
        """
        شروع فرآیند مغایرت‌گیری برای یک بانک مشخص
        """
        logger.info(f"شروع مغایرت‌گیری خودکار برای بانک {selected_bank_id}...")
        unreconciled_transactions = self.db_manager.get_unreconciled_bank_transactions(selected_bank_id, transaction_types)

        for bank_record in unreconciled_transactions:
            self._process_transaction_by_type(bank_record, selected_bank_id)

        logger.info("پایان مغایرت‌گیری خودکار.")

    def _process_transaction_by_type(self, bank_record: Dict[str, Any], selected_bank_id: int):
        """
        پردازش تراکنش بر اساس نوع آن
        """
        transaction_type = bank_record.get('Transaction_Type_Bank', '')
        
        if transaction_type in ['Electronic Transfer', 'Internal Transfer', 'Incoming/Outgoing Receipt']:
            self._reconcile_transfers(bank_record, selected_bank_id)
        elif transaction_type in ['Received Check', 'Paid Check']:
            self._reconcile_checks(bank_record, selected_bank_id)
        elif transaction_type == 'POS Deposit':
            self._reconcile_pos_deposits(bank_record, selected_bank_id)
        else:
            logger.warning(f"نوع تراکنش ناشناخته: {transaction_type} برای رکورد {bank_record.get('id')}")

    def _reconcile_transfers(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
        """
        مغایرت‌گیری حواله‌ها و رسیدهای بانکی
        """
        transaction_id = bank_record.get('id')
        logger.info(f"🔄 مغایرت‌گیری حواله/رسید {transaction_id}")

        bank_date = bank_record.get('Date', '')
        normalized_bank_date = utils.convert_date_format(bank_date, 'YYYY/MM/DD', 'YYYYMMDD')

        if not normalized_bank_date:
            logger.warning(f"⚠️ تاریخ تراکنش {transaction_id} قابل تبدیل نیست: {bank_date}")
            self._finalize_discrepancy(transaction_id, None, None, "Discrepancy - Transfer", "تاریخ نامعتبر")
            return False

        target_amount = bank_record.get('Deposit_Amount') or bank_record.get('Withdrawal_Amount')
        target_acc_entry_type = 'حواله/رسید دریافتنی' if bank_record.get('Deposit_Amount') else 'حواله/رسید پرداختنی'

        if not target_amount:
            logger.warning(f"⚠️ مبلغ تراکنش {transaction_id} موجود نیست")
            self._finalize_discrepancy(transaction_id, None, None, "Discrepancy - Transfer", "مبلغ ناموجود")
            return False

        with self.db_manager as db:
            found_acc_records = db.get_matching_accounting_entries_for_transfer(
                selected_bank_id, normalized_bank_date, target_amount, target_acc_entry_type
            )

        if len(found_acc_records) == 1:
            matching_acc_record = found_acc_records[0]
            self._finalize_reconciliation(
                transaction_id, matching_acc_record['id'], None, "Match - Transfer", "حواله/رسید: تطابق یکتا"
            )
            logger.info(f"✅ تطابق یکتا برای تراکنش حواله {transaction_id}")
            return True
        elif len(found_acc_records) > 1:
            # ... (منطق برای چندین تطابق و فیلتر شماره پیگیری)
            pass
        else:
            self._finalize_discrepancy(
                transaction_id, None, None, "Discrepancy - Transfer", "حواله/رسید: در حسابداری یافت نشد"
            )
            logger.warning(f"⚠️ هیچ تطابقی برای تراکنش حواله {transaction_id} یافت نشد")
            return False
        return False

    def _reconcile_checks(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
        """
        مغایرت‌گیری چک‌ها
        """
        transaction_id = bank_record.get('id')
        logger.info(f"🔄 مغایرت‌گیری چک {transaction_id}")

        date_of_receipt = bank_record.get('Date_Of_Receipt', '') # فرض بر اینکه تاریخ وصول در دیتای بانک است
        normalized_date_of_receipt = utils.convert_date_format(date_of_receipt, 'YYYY/MM/DD', 'YYYYMMDD')

        if not normalized_date_of_receipt:
             logger.warning(f"⚠️ تاریخ وصول چک {transaction_id} قابل تبدیل نیست: {date_of_receipt}")
             self._finalize_discrepancy(transaction_id, None, None, "Discrepancy - Check", "تاریخ وصول نامعتبر")
             return False

        amount = bank_record.get('Deposit_Amount') or bank_record.get('Withdrawal_Amount')
        acc_type = 'چک دريافتني' if bank_record.get('Deposit_Amount') else 'چک پرداختني'

        if not amount:
            logger.warning(f"⚠️ مبلغ تراکنش چک {transaction_id} موجود نیست")
            self._finalize_discrepancy(transaction_id, None, None, "Discrepancy - Check", "مبلغ ناموجود")
            return False

        with self.db_manager as db:
            found_acc_records = db.get_matching_accounting_entries_for_check(
                selected_bank_id, normalized_date_of_receipt, amount, acc_type
            )
        
        # ... (منطق فیلتر بر اساس شماره چک)
        if found_acc_records:
             # ...
             pass
        
        return False

    def _reconcile_pos_deposits(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
        """
        مغایرت‌گیری واریزهای پوز
        """
        transaction_id = bank_record.get('id')
        terminal_id = bank_record.get('Extracted_Shaparak_Terminal_ID')
        logger.info(f"🔄 مغایرت‌گیری پوز {transaction_id} - ترمینال: {terminal_id}")

        if not terminal_id:
            logger.warning(f"⚠️ شناسه ترمینال برای تراکنش پوز {transaction_id} موجود نیست")
            self._finalize_discrepancy(transaction_id, None, None, "Discrepancy - POS", "شناسه ترمینال ناموجود")
            return False
        
        bank_date = bank_record.get('Date', '')
        norm_bank_date = utils.convert_date_format(bank_date, 'YYYY/MM/DD', 'YYYYMMDD')

        with self.db_manager as db:
            # 1. بررسی وجود ورودی سرجمع
            aggregate_entry = db.get_accounting_aggregate_pos_entry(selected_bank_id, terminal_id, norm_bank_date)
            if aggregate_entry:
                #... (منطق تایید کاربر)
                pass
            
            # 2. مغایرت با تراکنش‌های تکی پوز
            pos_transactions = db.get_pos_transactions_by_terminal_and_date(selected_bank_id, terminal_id, norm_bank_date)
            # ... (منطق تطبیق تکی)

        return False

    def _finalize_reconciliation(self, bank_id, acc_id, pos_id, type_note, notes):
        with self.db_manager as db:
            db.record_reconciliation_result(bank_id, acc_id, pos_id, type_note, notes)
            if bank_id:
                db.update_bank_transaction_reconciled_status(bank_id, 1)
            if acc_id:
                db.update_accounting_entry_reconciled_status(acc_id, 1)
            if pos_id:
                db.update_pos_transaction_reconciled_status(pos_id, 1)
        logger.info(f"Finalized reconciliation for bank_id: {bank_id}")

    def _finalize_discrepancy(self, bank_id, acc_id, pos_id, type_note, notes):
        with self.db_manager as db:
            db.record_reconciliation_result(bank_id, acc_id, pos_id, type_note, notes)
        logger.warning(f"Finalized discrepancy for bank_id: {bank_id}")
    """
    موتور اصلی مغایرت‌گیری
    این کلاس تمام عملیات مغایرت‌گیری را هماهنگ می‌کند
    """
    
    def __init__(self):
        """
        سازنده کلاس
        """
        self.db_manager = DatabaseManager()
        
        # Callback برای مغایرت‌گیری دستی
        self.ui_callback_manual_reconciliation_needed = None
        
        logger.info("موتور مغایرت‌گیری راه‌اندازی شد")
    
    def start_reconciliation(self, selected_bank_id: int) -> Dict[str, Any]:
        """
        شروع فرآیند مغایرت‌گیری بر اساس الگوریتم جدید
        
        پارامترها:
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            نتایج مغایرت‌گیری
        """
        logger.info(f"🚀 شروع فرآیند مغایرت‌گیری برای بانک {selected_bank_id}")
        
        # مرحله آماده‌سازی: دریافت تراکنش‌های مغایرت‌گیری نشده بانک
        bank_transactions = self.db_manager.get_unreconciled_bank_transactions(selected_bank_id)
        logger.info(f"📊 تعداد تراکنش‌های بانکی مغایرت‌گیری نشده: {len(bank_transactions)}")
        
        if not bank_transactions:
            logger.info("هیچ تراکنش بانکی مغایرت‌گیری نشده‌ای یافت نشد")
            return {"message": "هیچ تراکنش بانکی مغایرت‌گیری نشده‌ای یافت نشد"}
        
        # آمار پردازش
        processed_count = 0
        successful_matches = 0
        
        # پردازش تکراری: هر تراکنش بانکی به صورت جداگانه پردازش می‌شود
        for bank_record in bank_transactions:
            transaction_type = bank_record.get('Transaction_Type_Bank', '')
            transaction_id = bank_record.get('id')
            
            logger.info(f"🔄 پردازش تراکنش {transaction_id} - نوع: {transaction_type}")
            
            try:
                success = self._process_transaction_by_type(bank_record, transaction_type, selected_bank_id)
                
                if success:
                    successful_matches += 1
                    logger.info(f"✅ تراکنش {transaction_id} با موفقیت پردازش شد")
                else:
                    logger.warning(f"⚠️ تراکنش {transaction_id} پردازش نشد")
                    
                processed_count += 1
                
            except Exception as e:
                logger.error(f"❌ خطا در پردازش تراکنش {transaction_id}: {str(e)}")
                # علامت‌گذاری به عنوان پردازش شده حتی در صورت خطا
                self._mark_bank_record_reconciled(transaction_id, f"خطا در پردازش: {str(e)}")
                processed_count += 1
                continue
        
        # گزارش نهایی
        result = {
            "total_transactions": len(bank_transactions),
            "processed_count": processed_count,
            "successful_matches": successful_matches,
            "failed_count": processed_count - successful_matches,
            "message": f"پردازش کامل شد. {successful_matches} از {processed_count} تراکنش با موفقیت مغایرت‌گیری شدند."
        }
        
        logger.info(f"📈 نتایج نهایی مغایرت‌گیری: {result}")
        return result
    
    def _process_transaction_by_type(self, bank_record: Dict[str, Any], transaction_type: str, selected_bank_id: int) -> bool:
        """
        پردازش تراکنش بر اساس نوع آن
        
        پارامترها:
            bank_record: رکورد تراکنش بانکی
            transaction_type: نوع تراکنش
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            موفقیت عملیات
        """
        transaction_type = transaction_type.strip()
        
        if transaction_type in ["Received Transfer", "Paid Transfer"]:
            # حواله‌ها/رسیدها
            return self._reconcile_transfers(bank_record, selected_bank_id)
            
        elif transaction_type in ["Received Check", "Paid Check"]:
            # چک‌ها
            return self._reconcile_checks(bank_record, selected_bank_id)
            
        elif transaction_type == "Pos Deposit":
            # واریزهای پوز
            return self._reconcile_pos_deposits(bank_record, selected_bank_id)
            
        else:
            logger.warning(f"نوع تراکنش ناشناخته: {transaction_type}")
            # علامت‌گذاری به عنوان پردازش شده با یادداشت
            self._mark_bank_record_reconciled(
                bank_record.get('id'), 
                f"نوع تراکنش ناشناخته: {transaction_type}"
            )
            return True
    
    def _reconcile_transfers(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
        """
        مغایرت‌گیری حواله‌ها/رسیدها
        
        پارامترها:
            bank_record: رکورد تراکنش بانکی
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            موفقیت عملیات
        """
        transaction_type = bank_record.get('Transaction_Type_Bank', '')
        transaction_id = bank_record.get('id')
        
        logger.info(f"🔄 مغایرت‌گیری حواله {transaction_id} - نوع: {transaction_type}")
        
        # تعیین مبلغ هدف و نوع ورودی حسابداری
        if transaction_type == 'Received Transfer':
            target_amount = bank_record.get('Deposit_Amount')
            target_acc_entry_type = 'حواله/فيش دريافتني'
        elif transaction_type == 'Paid Transfer':
            target_amount = bank_record.get('Withdrawal_Amount')
            target_acc_entry_type = 'حواله/فیش پرداختني'
        else:
            logger.warning(f"⚠️ نوع تراکنش حواله ناشناخته: {transaction_type}")
            return False
            
        if not target_amount:
            logger.warning(f"⚠️ مبلغ تراکنش حواله {transaction_id} موجود نیست")
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - Transfer", 
                "حواله/رسید: مبلغ تراکنش موجود نیست"
            )
            return False
            
        # نرمال‌سازی تاریخ بانک
        bank_date = bank_record.get('Date', '')
        normalized_bank_date = utils.convert_date_format(bank_date, 'YYYY/MM/DD', 'YYYYMMDD')
        
        if not normalized_bank_date:
            logger.warning(f"⚠️ تاریخ تراکنش حواله {transaction_id} قابل تبدیل نیست: {bank_date}")
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - Transfer", 
                "حواله/رسید: تاریخ تراکنش قابل تبدیل نیست"
            )
            return False
            
        # جستجوی اولیه در ورودی‌های حسابداری
        found_acc_records = self._search_accounting_entries_for_transfer(
            selected_bank_id, normalized_bank_date, target_amount, target_acc_entry_type
        )
        
        # پردازش بر اساس تعداد نتایج یافت شده
        if len(found_acc_records) == 1:
            # تطابق یکتا
            matching_acc_record = found_acc_records[0]
            self._finalize_reconciliation(
                bank_record['id'], 
                matching_acc_record['id'], 
                None, 
                "Match - Transfer", 
                "حواله/رسید: تطابق یکتا"
            )
            logger.info(f"✅ تطابق یکتا برای تراکنش حواله {transaction_id}")
            return True
            
        elif len(found_acc_records) > 1:
            # چندین تطابق - فیلتر ثانویه بر اساس شماره پیگیری
            filtered_records = self._filter_by_tracking_number(bank_record, found_acc_records)
            
            if len(filtered_records) == 1:
                # تطابق یکتا پس از فیلتر
                matching_acc_record = filtered_records[0]
                self._finalize_reconciliation(
                    bank_record['id'], 
                    matching_acc_record['id'], 
                    None, 
                    "Match - Transfer (Filtered)", 
                    "حواله/رسید: تطابق پس از فیلتر شماره پیگیری"
                )
                logger.info(f"✅ تطابق پس از فیلتر برای تراکنش حواله {transaction_id}")
                return True
                
            else:
                # نیاز به مغایرت‌گیری دستی یا ثبت مغایرت
                if (hasattr(self, 'ui_callback_manual_reconciliation_needed') and 
                    self.ui_callback_manual_reconciliation_needed):
                    self.ui_callback_manual_reconciliation_needed(bank_record, found_acc_records, 'transfer')
                    logger.info(f"🔧 ارسال به مغایرت‌گیری دستی برای تراکنش حواله {transaction_id}")
                    return True  # منتظر انتخاب کاربر
                else:
                    self._finalize_discrepancy(
                        bank_record['id'], None, None, 
                        "Discrepancy - Transfer", 
                        f"حواله/رسید: چندین تطابق ({len(found_acc_records)}) یافت شد"
                    )
                    logger.warning(f"⚠️ چندین تطابق برای تراکنش حواله {transaction_id}")
                    return False
                    
        else:
            # هیچ تطابقی یافت نشد
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - Transfer", 
                "حواله/رسید: در حسابداری یافت نشد"
            )
            logger.warning(f"⚠️ هیچ تطابقی برای تراکنش حواله {transaction_id} یافت نشد")
            return False
    
    def _reconcile_checks(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
        """
        مغایرت‌گیری چک‌ها
        
        پارامترها:
            bank_record: رکورد تراکنش بانکی
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            موفقیت عملیات
        """
        transaction_type = bank_record.get('Transaction_Type_Bank', '')
        transaction_id = bank_record.get('id')
        
        logger.info(f"🔄 مغایرت‌گیری چک {transaction_id} - نوع: {transaction_type}")
        
        # تعیین مبلغ هدف و نوع ورودی حسابداری
        if transaction_type == 'Received Check':
            target_amount = bank_record.get('Deposit_Amount')
            target_acc_entry_type = 'چک دريافتني'
        elif transaction_type == 'Paid Check':
            target_amount = bank_record.get('Withdrawal_Amount')
            target_acc_entry_type = 'چک پرداختني'
        else:
            logger.warning(f"⚠️ نوع تراکنش چک ناشناخته: {transaction_type}")
            return False
            
        if not target_amount:
            logger.warning(f"⚠️ مبلغ تراکنش چک {transaction_id} موجود نیست")
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - Check", 
                "چک: مبلغ تراکنش موجود نیست"
            )
            return False
            
        # نرمال‌سازی تاریخ بانک
        bank_date = bank_record.get('Date', '')
        normalized_bank_date = utils.convert_date_format(bank_date, 'YYYY/MM/DD', 'YYYYMMDD')
        
        if not normalized_bank_date:
            logger.warning(f"⚠️ تاریخ تراکنش چک {transaction_id} قابل تبدیل نیست: {bank_date}")
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - Check", 
                "چک: تاریخ تراکنش قابل تبدیل نیست"
            )
            return False
            
        # جستجوی اولیه در ورودی‌های حسابداری (بر اساس Date_Of_Receipt)
        found_acc_records = self._search_accounting_entries_for_check(
            selected_bank_id, normalized_bank_date, target_amount, target_acc_entry_type
        )
        
        # فیلتر بر اساس شماره چک
        if found_acc_records:
            filtered_records = self._filter_by_check_number(bank_record, found_acc_records)
        else:
            filtered_records = []
        
        # پردازش بر اساس تعداد نتایج یافت شده
        if len(filtered_records) == 1:
            # تطابق یکتا
            matching_acc_record = filtered_records[0]
            self._finalize_reconciliation(
                bank_record['id'], 
                matching_acc_record['id'], 
                None, 
                "Match - Check", 
                "چک: تطابق یکتا"
            )
            logger.info(f"✅ تطابق یکتا برای تراکنش چک {transaction_id}")
            return True
            
        elif len(filtered_records) > 1:
            # چندین تطابق - نیاز به مغایرت‌گیری دستی
            if (hasattr(self, 'ui_callback_manual_reconciliation_needed') and 
                self.ui_callback_manual_reconciliation_needed):
                self.ui_callback_manual_reconciliation_needed(bank_record, filtered_records, 'check')
                logger.info(f"🔧 ارسال به مغایرت‌گیری دستی برای تراکنش چک {transaction_id}")
                return True  # منتظر انتخاب کاربر
            else:
                self._finalize_discrepancy(
                    bank_record['id'], None, None, 
                    "Discrepancy - Check", 
                    f"چک: چندین تطابق ({len(filtered_records)}) یافت شد"
                )
                logger.warning(f"⚠️ چندین تطابق برای تراکنش چک {transaction_id}")
                return False
                
        else:
            # هیچ تطابقی یافت نشد
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - Check", 
                "چک: در حسابداری یافت نشد"
            )
            logger.warning(f"⚠️ هیچ تطابقی برای تراکنش چک {transaction_id} یافت نشد")
            return False
    
    def _reconcile_pos_deposits(self, bank_record: Dict[str, Any], selected_bank_id: int) -> bool:
        """
        مغایرت‌گیری واریزهای پوز
        
        پارامترها:
            bank_record: رکورد تراکنش بانکی
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            موفقیت عملیات
        """
        transaction_id = bank_record.get('id')
        terminal_id = bank_record.get('Extracted_Shaparak_Terminal_ID')
        
        logger.info(f"🔄 مغایرت‌گیری پوز {transaction_id} - ترمینال: {terminal_id}")
        
        if not terminal_id:
            logger.warning(f"⚠️ شناسه ترمینال برای تراکنش پوز {transaction_id} موجود نیست")
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - POS", 
                "پوز: شناسه ترمینال موجود نیست"
            )
            return False
        
        # مرحله 1: بررسی وجود داده‌های پوز برای این ترمینال
        pos_transactions = self._get_pos_transactions_for_terminal(terminal_id, selected_bank_id)
        
        if not pos_transactions:
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - POS", 
                f"پوز: داده‌های پوز برای ترمینال {terminal_id} موجود نیست"
            )
            logger.warning(f"⚠️ داده‌های پوز برای ترمینال {terminal_id} موجود نیست")
            return False
        
        # نرمال‌سازی تاریخ بانک
        bank_date = bank_record.get('Date', '')
        normalized_bank_date = utils.convert_date_format(bank_date, 'YYYY/MM/DD', 'YYYYMMDD')
        
        if not normalized_bank_date:
            logger.warning(f"⚠️ تاریخ تراکنش پوز {transaction_id} قابل تبدیل نیست: {bank_date}")
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - POS", 
                "پوز: تاریخ تراکنش قابل تبدیل نیست"
            )
            return False
        
        # مرحله 2: بررسی وجود ورودی سرجمع (اختیاری)
        aggregate_entry = self._check_aggregate_pos_entry(
            selected_bank_id, terminal_id, normalized_bank_date
        )
        
        if aggregate_entry:
            # اگر ورودی سرجمع وجود دارد، از کاربر تأیید بگیریم
            if (hasattr(self, 'ui_callback_aggregate_confirmation') and 
                self.ui_callback_aggregate_confirmation):
                # ارسال به UI برای تأیید
                self.ui_callback_aggregate_confirmation(bank_record, aggregate_entry, 'pos_aggregate')
                logger.info(f"🔧 ارسال به تأیید سرجمع برای تراکنش پوز {transaction_id}")
                return True  # منتظر تأیید کاربر
            else:
                # اگر callback موجود نیست، به صورت خودکار سرجمع را پردازش کن
                return self._process_aggregate_pos_reconciliation(
                    bank_record, aggregate_entry, terminal_id, normalized_bank_date, selected_bank_id
                )
        
        # مرحله 3: مغایرت‌گیری جزئی پوز
        return self._process_detailed_pos_reconciliation(
            bank_record, terminal_id, normalized_bank_date, selected_bank_id
        )
    
    def _search_accounting_entries_for_transfer(self, bank_id: int, normalized_date: str, 
                                              amount: float, entry_type: str) -> List[Dict[str, Any]]:
        """
        جستجوی ورودی‌های حسابداری برای حواله‌ها
        """
        try:
            self.db_manager.connect()
            
            self.db_manager.cursor.execute('''
                SELECT * FROM AccountingEntries 
                WHERE is_reconciled = 0 
                AND BankID = ? 
                AND Due_Date = ? 
                AND Price = ? 
                AND Entry_Type_Acc = ?
            ''', (bank_id, normalized_date, amount, entry_type))
            
            columns = [desc[0] for desc in self.db_manager.cursor.description]
            result = [dict(zip(columns, row)) for row in self.db_manager.cursor.fetchall()]
            
            logger.info(f"جستجوی حسابداری برای حواله: {len(result)} نتیجه یافت شد")
            return result
            
        except Exception as e:
            logger.error(f"خطا در جستجوی ورودی‌های حسابداری برای حواله: {str(e)}")
            return []
        finally:
            self.db_manager.disconnect()
    
    def _search_accounting_entries_for_check(self, bank_id: int, normalized_date: str, 
                                           amount: float, entry_type: str) -> List[Dict[str, Any]]:
        """
        جستجوی ورودی‌های حسابداری برای چک‌ها (بر اساس Date_Of_Receipt)
        """
        try:
            self.db_manager.connect()
            
            self.db_manager.cursor.execute('''
                SELECT * FROM AccountingEntries 
                WHERE is_reconciled = 0 
                AND BankID = ? 
                AND Date_Of_Receipt = ? 
                AND Price = ? 
                AND Entry_Type_Acc = ?
            ''', (bank_id, normalized_date, amount, entry_type))
            
            columns = [desc[0] for desc in self.db_manager.cursor.description]
            result = [dict(zip(columns, row)) for row in self.db_manager.cursor.fetchall()]
            
            logger.info(f"جستجوی حسابداری برای چک: {len(result)} نتیجه یافت شد")
            return result
            
        except Exception as e:
            logger.error(f"خطا در جستجوی ورودی‌های حسابداری برای چک: {str(e)}")
            return []
        finally:
            self.db_manager.disconnect()
    
    def _get_pos_transactions_for_terminal(self, terminal_id: str, bank_id: int) -> List[Dict[str, Any]]:
        """
        دریافت تراکنش‌های پوز برای ترمینال مشخص
        """
        try:
            self.db_manager.connect()
            
            self.db_manager.cursor.execute('''
                SELECT * FROM PosTransactions 
                WHERE Terminal_ID = ? 
                AND BankID = ?
                ORDER BY Transaction_Date
            ''', (terminal_id, bank_id))
            
            columns = [desc[0] for desc in self.db_manager.cursor.description]
            result = [dict(zip(columns, row)) for row in self.db_manager.cursor.fetchall()]
            
            logger.info(f"تراکنش‌های پوز برای ترمینال {terminal_id}: {len(result)} تراکنش")
            return result
            
        except Exception as e:
            logger.error(f"خطا در دریافت تراکنش‌های پوز: {str(e)}")
            return []
        finally:
            self.db_manager.disconnect()
    
    def _check_aggregate_pos_entry(self, bank_id: int, terminal_id: str, date: str) -> Optional[Dict[str, Any]]:
        """
        بررسی وجود ورودی سرجمع پوز
        """
        try:
            self.db_manager.connect()
            
            self.db_manager.cursor.execute('''
                SELECT * FROM AccountingEntries 
                WHERE is_reconciled = 0 
                AND BankID = ? 
                AND Entry_Type_Acc = 'پوز دریافتنی' 
                AND Account_Reference_Suffix = ? 
                AND Description_Notes_Acc LIKE '%سرجمع%' 
                AND Due_Date = ?
            ''', (bank_id, terminal_id, date))
            
            columns = [desc[0] for desc in self.db_manager.cursor.description]
            rows = self.db_manager.cursor.fetchall()
            
            if rows:
                result = dict(zip(columns, rows[0]))
                logger.info(f"ورودی سرجمع پوز یافت شد برای ترمینال {terminal_id}")
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"خطا در بررسی ورودی سرجمع پوز: {str(e)}")
            return None
        finally:
            self.db_manager.disconnect()
    
    def _process_aggregate_pos_reconciliation(self, bank_record: Dict[str, Any], 
                                            aggregate_entry: Dict[str, Any], 
                                            terminal_id: str, date: str, bank_id: int) -> bool:
        """
        پردازش مغایرت‌گیری سرجمع پوز
        """
        # محاسبه مجموع تراکنش‌های پوز برای روز قبل
        previous_date = self._get_previous_date(date)
        # تبدیل تاریخ به فرمت YYYY/MM/DD
        formatted_date = utils.convert_date_format(previous_date, 'YYYYMMDD', 'YYYY/MM/DD')
        pos_sum = self.db_manager.calculate_pos_sum_for_date(terminal_id, formatted_date, bank_id)
        
        aggregate_amount = aggregate_entry.get('Price', 0)
        
        if abs(pos_sum - aggregate_amount) < 0.01:  # تطابق مبالغ
            # مغایرت‌گیری موفق - علامت‌گذاری همه تراکنش‌های مربوطه
            formatted_date = utils.convert_date_format(previous_date, 'YYYYMMDD', 'YYYY/MM/DD')
            self.db_manager.reconcile_all_pos_for_date(terminal_id, formatted_date, bank_id)
            
            self._finalize_reconciliation(
                bank_record['id'], 
                aggregate_entry['id'], 
                None, 
                "Match - POS Aggregate", 
                f"پوز سرجمع: تطابق موفق - مبلغ: {aggregate_amount}"
            )
            
            logger.info(f"✅ مغایرت‌گیری سرجمع پوز موفق - ترمینال: {terminal_id}")
            return True
        else:
            # عدم تطابق مبالغ
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - POS Aggregate", 
                f"پوز سرجمع: عدم تطابق مبالغ - بانک: {aggregate_amount}, پوز: {pos_sum}"
            )
            
            logger.warning(f"⚠️ عدم تطابق مبالغ سرجمع پوز - ترمینال: {terminal_id}")
            return False
    
    def _process_detailed_pos_reconciliation(self, bank_record: Dict[str, Any], 
                                           terminal_id: str, date: str, bank_id: int) -> bool:
        """
        پردازش مغایرت‌گیری جزئی پوز
        """
        # دریافت تراکنش‌های پوز برای روز قبل
        previous_date = self._get_previous_date(date)
        # تبدیل تاریخ به فرمت YYYY/MM/DD
        formatted_date = utils.convert_date_format(previous_date, 'YYYYMMDD', 'YYYY/MM/DD')
        pos_transactions = self.db_manager.get_pos_transactions_for_date(terminal_id, formatted_date, bank_id)
        
        if not pos_transactions:
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - POS", 
                f"پوز: تراکنش‌های پوز برای تاریخ {previous_date} یافت نشد"
            )
            return False
        
        successful_matches = 0
        
        # پردازش هر تراکنش پوز
        for pos_record in pos_transactions:
            if self._reconcile_single_pos_transaction(pos_record, bank_id):
                successful_matches += 1
        
        # اگر همه تراکنش‌های پوز مغایرت‌گیری شدند، بانک را نیز علامت‌گذاری کن
        if successful_matches == len(pos_transactions):
            self._mark_bank_record_reconciled(
                bank_record['id'], 
                f"پوز جزئی: {successful_matches} تراکنش پوز مغایرت‌گیری شد"
            )
            logger.info(f"✅ مغایرت‌گیری جزئی پوز موفق - ترمینال: {terminal_id}")
            return True
        else:
            self._finalize_discrepancy(
                bank_record['id'], None, None, 
                "Discrepancy - POS", 
                f"پوز جزئی: {successful_matches} از {len(pos_transactions)} تراکنش مغایرت‌گیری شد"
            )
            logger.warning(f"⚠️ مغایرت‌گیری جزئی پوز ناقص - ترمینال: {terminal_id}")
            return False
    
    def _reconcile_single_pos_transaction(self, pos_record: Dict[str, Any], bank_id: int) -> bool:
        """
        مغایرت‌گیری یک تراکنش پوز
        """
        pos_amount = pos_record.get('Transaction_Amount', 0)
        pos_date = pos_record.get('Transaction_Date', '')
        pos_tracking = pos_record.get('POS_Tracking_Number', '')
        
        # نرمال‌سازی تاریخ پوز
        normalized_pos_date = utils.convert_date_format(pos_date, 'YYYY/MM/DD', 'YYYYMMDD')
        
        if not normalized_pos_date:
            logger.warning(f"تاریخ تراکنش پوز قابل تبدیل نیست: {pos_date}")
            return False
        
        # جستجوی ورودی حسابداری مطابق
        matching_acc = self._search_accounting_entry_for_pos(
            bank_id, normalized_pos_date, pos_amount, pos_tracking
        )
        
        if matching_acc:
            # مغایرت‌گیری موفق
            self._finalize_reconciliation(
                None, 
                matching_acc['id'], 
                pos_record['id'], 
                "Match - POS Detail", 
                f"پوز جزئی: تطابق موفق - مبلغ: {pos_amount}"
            )
            return True
        else:
            # ثبت مغایرت برای این تراکنش پوز
            self._finalize_discrepancy(
                None, None, pos_record['id'], 
                "Discrepancy - POS Detail", 
                f"پوز جزئی: ورودی حسابداری یافت نشد - مبلغ: {pos_amount}"
            )
            return False
    
    def _search_accounting_entry_for_pos(self, bank_id: int, date: str, amount: float, 
                                       tracking_number: str) -> Optional[Dict[str, Any]]:
        """
        جستجوی ورودی حسابداری برای تراکنش پوز
        """
        try:
            self.db_manager.connect()
            
            # استخراج 5 یا 6 رقم آخر شماره پیگیری
            tracking_suffix_6 = tracking_number[-6:] if len(tracking_number) >= 6 else tracking_number
            tracking_suffix_5 = tracking_number[-5:] if len(tracking_number) >= 5 else tracking_number
            
            # جستجو با 6 رقم آخر
            self.db_manager.cursor.execute('''
                SELECT * FROM AccountingEntries 
                WHERE is_reconciled = 0 
                AND BankID = ? 
                AND Entry_Type_Acc = 'پوز دریافتنی' 
                AND Price = ? 
                AND Due_Date = ? 
                AND Account_Reference_Suffix = ?
            ''', (bank_id, amount, date, tracking_suffix_6))
            
            columns = [desc[0] for desc in self.db_manager.cursor.description]
            rows = self.db_manager.cursor.fetchall()
            
            if rows:
                return dict(zip(columns, rows[0]))
            
            # اگر با 6 رقم یافت نشد، با 5 رقم جستجو کن
            self.db_manager.cursor.execute('''
                SELECT * FROM AccountingEntries 
                WHERE is_reconciled = 0 
                AND BankID = ? 
                AND Entry_Type_Acc = 'پوز دریافتنی' 
                AND Price = ? 
                AND Due_Date = ? 
                AND Account_Reference_Suffix = ?
            ''', (bank_id, amount, date, tracking_suffix_5))
            
            rows = self.db_manager.cursor.fetchall()
            
            if rows:
                return dict(zip(columns, rows[0]))
            
            return None
            
        except Exception as e:
            logger.error(f"خطا در جستجوی ورودی حسابداری برای پوز: {str(e)}")
            return None
        finally:
            self.db_manager.disconnect()
    
    def _filter_by_tracking_number(self, bank_record: Dict[str, Any], 
                                 acc_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        فیلتر ورودی‌های حسابداری بر اساس شماره پیگیری
        """
        bank_description = bank_record.get('Description_Bank', '')
        
        if not bank_description:
            return acc_records
            
        filtered_records = []
        
        for acc_record in acc_records:
            tracking_suffix = acc_record.get('Account_Reference_Suffix', '')
            
            if tracking_suffix and tracking_suffix in bank_description:
                filtered_records.append(acc_record)
                
        logger.info(f"فیلتر شماره پیگیری: {len(acc_records)} -> {len(filtered_records)}")
        return filtered_records
    
    def _filter_by_check_number(self, bank_record: Dict[str, Any], 
                               acc_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        فیلتر ورودی‌های حسابداری بر اساس شماره چک
        """
        bank_description = bank_record.get('Description_Bank', '')
        
        if not bank_description:
            return acc_records
            
        filtered_records = []
        
        for acc_record in acc_records:
            check_number = acc_record.get('Account_Reference_Suffix', '')
            
            if check_number and check_number in bank_description:
                filtered_records.append(acc_record)
                
        logger.info(f"فیلتر شماره چک: {len(acc_records)} -> {len(filtered_records)}")
        return filtered_records
    
    def _get_previous_date(self, date_str: str) -> str:
        """
        دریافت تاریخ روز قبل
        """
        try:
            from datetime import datetime, timedelta
            
            # تبدیل YYYYMMDD به datetime
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            previous_date_obj = date_obj - timedelta(days=1)
            
            return previous_date_obj.strftime('%Y%m%d')
            
        except Exception as e:
            logger.error(f"خطا در محاسبه تاریخ قبل: {str(e)}")
            return date_str
    

    

    

    
    def _finalize_reconciliation(self, bank_id: Optional[int], acc_id: Optional[int], 
                               pos_id: Optional[int], rec_type: str, notes: str):
        """
        نهایی‌سازی مغایرت‌گیری موفق
        """
        try:
            # به‌روزرسانی وضعیت مغایرت‌گیری رکوردها
            if bank_id:
                self.db_manager.update_reconciliation_status('BankTransactions', bank_id, True)
                
            if acc_id:
                self.db_manager.update_reconciliation_status('AccountingEntries', acc_id, True)
                
            if pos_id:
                self.db_manager.update_reconciliation_status('PosTransactions', pos_id, True)
                
            # درج نتیجه مغایرت‌گیری
            success = self.db_manager.record_reconciliation_result(
                bank_id=bank_id,
                pos_id=pos_id,
                accounting_id=acc_id,
                reconciliation_type=rec_type,
                notes=notes
            )
            
            if success:
                logger.info(f"✅ مغایرت‌گیری موفق - بانک: {bank_id}, حسابداری: {acc_id}, پوز: {pos_id}")
            else:
                logger.error(f"❌ خطا در ثبت نتیجه مغایرت‌گیری")
                
        except Exception as e:
            logger.error(f"❌ خطا در نهایی‌سازی مغایرت‌گیری: {str(e)}")
    
    def _finalize_discrepancy(self, bank_id: Optional[int], acc_id: Optional[int], 
                            pos_id: Optional[int], rec_type: str, notes: str):
        """
        نهایی‌سازی مغایرت
        """
        try:
            # علامت‌گذاری رکوردها به عنوان پردازش شده
            if bank_id:
                self.db_manager.update_reconciliation_status('BankTransactions', bank_id, True)
                
            if acc_id:
                self.db_manager.update_reconciliation_status('AccountingEntries', acc_id, True)
                
            if pos_id:
                self.db_manager.update_reconciliation_status('PosTransactions', pos_id, True)
            
            # درج مغایرت در جدول نتایج
            success = self.db_manager.record_reconciliation_result(
                bank_id=bank_id,
                pos_id=pos_id,
                accounting_id=acc_id,
                reconciliation_type=rec_type,
                notes=notes
            )
            
            if success:
                logger.warning(f"⚠️ مغایرت ثبت شد - بانک: {bank_id}, نوع: {rec_type}")
            else:
                logger.error(f"❌ خطا در ثبت مغایرت")
                
        except Exception as e:
            logger.error(f"❌ خطا در نهایی‌سازی مغایرت: {str(e)}")
    
    def _mark_bank_record_reconciled(self, bank_id: int, notes: str = None) -> bool:
        """
        علامت‌گذاری رکورد بانک به عنوان مغایرت‌گیری شده
        """
        success = self.db_manager.update_reconciliation_status('BankTransactions', bank_id, True)
        
        # ثبت نتیجه مغایرت‌گیری در جدول ReconciliationResults
        if success:
            self.db_manager.record_reconciliation_result(
                bank_id=bank_id,
                pos_id=None,
                accounting_id=None,
                reconciliation_type="Processed",
                notes=notes or "رکورد بانک پردازش شد"
            )
            
        if success and notes:
            logger.info(f"رکورد بانک {bank_id} علامت‌گذاری شد: {notes}")
        return success
    
    # متدهای کمکی برای UI
    def handle_manual_selection(self, bank_record_id: int, selected_acc_id: int, reconciliation_type: str):
        """
        مدیریت انتخاب دستی کاربر
        """
        try:
            if reconciliation_type == 'transfer':
                rec_type = "Manual - Transfer"
                notes = "حواله/رسید: انتخاب دستی کاربر"
            elif reconciliation_type == 'check':
                rec_type = "Manual - Check"
                notes = "چک: انتخاب دستی کاربر"
            else:
                rec_type = "Manual"
                notes = "انتخاب دستی کاربر"
            
            self._finalize_reconciliation(
                bank_record_id, 
                selected_acc_id, 
                None, 
                rec_type, 
                notes
            )
            
            logger.info(f"✅ انتخاب دستی - بانک: {bank_record_id}, حسابداری: {selected_acc_id}")
            
        except Exception as e:
            logger.error(f"❌ خطا در انتخاب دستی: {str(e)}")
    
    def handle_aggregate_confirmation(self, bank_record_id: int, aggregate_entry_id: int, 
                                    terminal_id: str, date: str, bank_id: int, confirmed: bool):
        """
        مدیریت تأیید سرجمع پوز
        """
        try:
            if confirmed:
                # پردازش سرجمع
                bank_record = {'id': bank_record_id}
                aggregate_entry = {'id': aggregate_entry_id, 'Price': 0}  # مبلغ باید از دیتابیس گرفته شود
                
                # دریافت مبلغ سرجمع از دیتابیس
                aggregate_entry = self._get_accounting_entry_by_id(aggregate_entry_id)
                
                if aggregate_entry:
                    self._process_aggregate_pos_reconciliation(
                        bank_record, aggregate_entry, terminal_id, date, bank_id
                    )
                else:
                    logger.error(f"ورودی سرجمع {aggregate_entry_id} یافت نشد")
            else:
                # پردازش جزئی
                bank_record = {'id': bank_record_id}
                self._process_detailed_pos_reconciliation(
                    bank_record, terminal_id, date, bank_id
                )
                
        except Exception as e:
            logger.error(f"❌ خطا در تأیید سرجمع: {str(e)}")
    
    def _get_accounting_entry_by_id(self, entry_id: int) -> Optional[Dict[str, Any]]:
        """
        دریافت ورودی حسابداری بر اساس شناسه
        """
        try:
            self.db_manager.connect()
            
            self.db_manager.cursor.execute('''
                SELECT * FROM AccountingEntries WHERE id = ?
            ''', (entry_id,))
            
            columns = [desc[0] for desc in self.db_manager.cursor.description]
            row = self.db_manager.cursor.fetchone()
            
            if row:
                return dict(zip(columns, row))
            
            return None
            
        except Exception as e:
            logger.error(f"خطا در دریافت ورودی حسابداری: {str(e)}")
            return None
        finally:
            self.db_manager.disconnect()
    
    # متدهای عمومی برای UI
    def get_unreconciled_bank_transactions(self, selected_bank_id: int) -> List[Dict[str, Any]]:
        """
        دریافت تراکنش‌های بانکی مغایرت‌گیری نشده
        """
        return self.db_manager.get_unreconciled_bank_transactions(selected_bank_id)
    
    def get_unreconciled_pos_transactions(self, selected_bank_id: int) -> List[Dict[str, Any]]:
        """
        دریافت تراکنش‌های پوز مغایرت‌گیری نشده
        """
        return self.db_manager.get_unreconciled_pos_transactions(selected_bank_id)
    
    def get_unreconciled_accounting_entries(self, selected_bank_id: int) -> List[Dict[str, Any]]:
        """
        دریافت ورودی‌های حسابداری مغایرت‌گیری نشده
        """
        return self.db_manager.get_unreconciled_accounting_entries(selected_bank_id)
    
    def manual_reconcile(self, bank_id: int, pos_id: int = None, accounting_id: int = None, notes: str = None) -> bool:
        """
        مغایرت‌گیری دستی
        """
        logger.info(f"شروع مغایرت‌گیری دستی - بانک: {bank_id}, پوز: {pos_id}, حسابداری: {accounting_id}")
        
        try:
            # علامت‌گذاری رکوردها به عنوان مغایرت‌گیری شده
            self.db_manager.update_reconciliation_status('BankTransactions', bank_id, True)
            
            if pos_id:
                self.db_manager.update_reconciliation_status('PosTransactions', pos_id, True)
            
            if accounting_id:
                self.db_manager.update_reconciliation_status('AccountingEntries', accounting_id, True)
            
            # ثبت نتیجه مغایرت‌گیری
            success = self.db_manager.record_reconciliation_result(
                bank_id=bank_id,
                pos_id=pos_id,
                accounting_id=accounting_id,
                reconciliation_type="Manual",
                notes=notes or "مغایرت‌گیری دستی"
            )
            
            if success:
                logger.info(f"مغایرت‌گیری دستی موفق - بانک: {bank_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"خطا در مغایرت‌گیری دستی: {str(e)}")
            return False
    
    def get_reconciliation_statistics(self, selected_bank_id: int) -> Dict[str, Any]:
        """
        دریافت آمار مغایرت‌گیری
        """
        try:
            # تعداد کل تراکنش‌های بانکی
            total_bank = self.db_manager.get_total_bank_transactions(selected_bank_id)
            
            # تعداد تراکنش‌های مغایرت‌گیری شده
            reconciled_bank = self.db_manager.get_reconciled_bank_transactions_count(selected_bank_id)
            
            # تعداد تراکنش‌های مغایرت‌گیری نشده
            unreconciled_bank = total_bank - reconciled_bank
            
            # درصد مغایرت‌گیری
            reconciliation_percentage = (reconciled_bank / total_bank * 100) if total_bank > 0 else 0
            
            stats = {
                "total_bank_transactions": total_bank,
                "reconciled_bank_transactions": reconciled_bank,
                "unreconciled_bank_transactions": unreconciled_bank,
                "reconciliation_percentage": round(reconciliation_percentage, 2)
            }
            
            logger.info(f"آمار مغایرت‌گیری: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"خطا در دریافت آمار مغایرت‌گیری: {str(e)}")
            return {}