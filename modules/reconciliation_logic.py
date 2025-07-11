#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول منطق مغایرت‌گیری
این ماژول مسئول انجام عملیات مغایرت‌گیری بین داده‌های بانک، پوز و حسابداری است.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from modules.database_manager import DatabaseManager
from modules.logger import get_logger

# ایجاد شیء لاگر
logger = get_logger(__name__)


class ReconciliationEngine:
    """
    موتور مغایرت‌گیری برای تطبیق داده‌های بانک، پوز و حسابداری
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        مقداردهی اولیه کلاس ReconciliationEngine
        
        پارامترها:
            db_manager: نمونه‌ای از کلاس DatabaseManager
        """
        self.db_manager = db_manager
        self.reconciliation_results = []
        
    def get_unreconciled_bank_transactions(self):
        """
        دریافت تراکنش‌های بانکی مغایرت‌گیری نشده
        
        خروجی:
            لیست تراکنش‌های بانکی مغایرت‌گیری نشده
        """
        return self.db_manager.get_unreconciled_bank_transactions()
    
    def get_unreconciled_pos_transactions(self):
        """
        دریافت تراکنش‌های پوز مغایرت‌گیری نشده
        
        خروجی:
            لیست تراکنش‌های پوز مغایرت‌گیری نشده
        """
        return self.db_manager.get_unreconciled_pos_transactions()
    
    def get_unreconciled_accounting_entries(self):
        """
        دریافت ورودی‌های حسابداری مغایرت‌گیری نشده
        
        خروجی:
            لیست ورودی‌های حسابداری مغایرت‌گیری نشده
        """
        return self.db_manager.get_unreconciled_accounting_entries()
    
    def start_reconciliation(self) -> Dict[str, Any]:
        """
        شروع فرآیند مغایرت‌گیری
        
        خروجی:
            دیکشنری حاوی نتایج مغایرت‌گیری
        """
        logger.info("شروع فرآیند مغایرت‌گیری...")
        
        # دریافت داده‌های مغایرت‌گیری نشده
        bank_transactions = self.db_manager.get_unreconciled_bank_transactions()
        pos_transactions = self.db_manager.get_unreconciled_pos_transactions()
        accounting_entries = self.db_manager.get_unreconciled_accounting_entries()
        
        logger.info(f"تعداد تراکنش‌های بانکی مغایرت‌گیری نشده: {len(bank_transactions)}")
        logger.info(f"تعداد تراکنش‌های پوز مغایرت‌گیری نشده: {len(pos_transactions)}")
        logger.info(f"تعداد ورودی‌های حسابداری مغایرت‌گیری نشده: {len(accounting_entries)}")
        
        # انجام مغایرت‌گیری‌های مختلف
        shaparak_results = self.reconcile_shaparak_pos(bank_transactions, pos_transactions)
        check_results = self.reconcile_checks(bank_transactions, accounting_entries)
        transfer_results = self.reconcile_transfers(bank_transactions, accounting_entries)
        pos_accounting_results = self.reconcile_pos_accounting(pos_transactions, accounting_entries)
        card_suffix_hints = self.find_card_suffix_hints(pos_transactions, accounting_entries)
        
        # جمع‌آوری نتایج
        results = {
            "shaparak_pos": shaparak_results,
            "checks": check_results,
            "transfers": transfer_results,
            "pos_accounting": pos_accounting_results,
            "card_suffix_hints": card_suffix_hints
        }
        
        # محاسبه آمار
        stats = self.db_manager.get_reconciliation_statistics()
        results["statistics"] = stats
        
        logger.info("فرآیند مغایرت‌گیری با موفقیت به پایان رسید.")
        return results
    
    def reconcile_shaparak_pos(self, bank_transactions: List[Dict[str, Any]] = None, 
                              pos_transactions: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        مغایرت‌گیری بین تراکنش‌های بانکی شاپرک و تراکنش‌های پوز
        
        پارامترها:
            bank_transactions: لیست تراکنش‌های بانکی (اختیاری)
            pos_transactions: لیست تراکنش‌های پوز (اختیاری)
            
        خروجی:
            دیکشنری حاوی نتایج مغایرت‌گیری
        """
        # اگر پارامترها ارسال نشده باشند، داده‌ها را از پایگاه داده دریافت می‌کنیم
        if bank_transactions is None:
            bank_transactions = self.db_manager.get_unreconciled_bank_transactions()
        if pos_transactions is None:
            pos_transactions = self.db_manager.get_unreconciled_pos_transactions()
        logger.info("شروع مغایرت‌گیری شاپرک-پوز...")
        results = []
        
        # فیلتر کردن تراکنش‌های بانکی از نوع واریز پوز
        pos_deposit_transactions = [t for t in bank_transactions if t.get('Transaction_Type_Bank') == "POS Deposit"]
        logger.info(f"تعداد تراکنش‌های واریز پوز بانکی: {len(pos_deposit_transactions)}")
        
        for bank_tx in pos_deposit_transactions:
            # تبدیل تاریخ بانک به شیء datetime
            try:
                bank_date_str = bank_tx.get('Date')
                bank_date = datetime.strptime(bank_date_str, '%Y/%m/%d')
                # تاریخ پوز معمولاً یک روز قبل از تاریخ بانک است
                pos_expected_date = bank_date - timedelta(days=1)
                pos_expected_date_str = pos_expected_date.strftime('%Y/%m/%d')
            except Exception as e:
                logger.warning(f"خطا در تبدیل تاریخ بانک: {str(e)}, تاریخ: {bank_tx.get('Date')}, شناسه: {bank_tx.get('id')}")
                continue
            
            # مبلغ واریز بانک
            bank_amount = bank_tx.get('Deposit_Amount')
            if not bank_amount:
                continue
                
            # شناسه ترمینال استخراج شده
            terminal_id = bank_tx.get('Extracted_Shaparak_Terminal_ID')
            if not terminal_id:
                continue
            
            # جستجو برای تراکنش پوز منطبق
            for pos_tx in pos_transactions:
                pos_date_str = pos_tx.get('Transaction_Date')
                pos_amount = pos_tx.get('Transaction_Amount')
                pos_terminal_id = pos_tx.get('Terminal_ID')
                
                # بررسی تطابق تاریخ، مبلغ و شناسه ترمینال
                if (pos_date_str == pos_expected_date_str and 
                    abs(float(bank_amount) - float(pos_amount)) < 0.01 and 
                    terminal_id == pos_terminal_id):
                    
                    # ثبت نتیجه مغایرت‌گیری
                    reconciliation_result = {
                        "bank_id": bank_tx.get('id'),
                        "pos_id": pos_tx.get('id'),
                        "amount": bank_amount,
                        "date_bank": bank_date_str,
                        "date_pos": pos_date_str,
                        "terminal_id": terminal_id,
                        "tracking_id_bank": bank_tx.get('Bank_Tracking_ID'),
                        "tracking_id_pos": pos_tx.get('POS_Tracking_Number')
                    }
                    
                    # ثبت در پایگاه داده
                    success = self.db_manager.record_reconciliation_result(
                        bank_id=bank_tx.get('id'),
                        pos_id=pos_tx.get('id'),
                        accounting_id=None,
                        reconciliation_type="Shaparak-POS",
                        notes=f"مبلغ: {bank_amount}, تاریخ بانک: {bank_date_str}, تاریخ پوز: {pos_date_str}, ترمینال: {terminal_id}"
                    )
                    
                    if success:
                        logger.info(f"مغایرت‌گیری موفق شاپرک-پوز: بانک ID {bank_tx.get('id')}, پوز ID {pos_tx.get('id')}, مبلغ: {bank_amount}")
                        results.append(reconciliation_result)
                    break
        
        logger.info(f"مغایرت‌گیری شاپرک-پوز: {len(results)} مورد تطبیق یافت شد.")
        
        # محاسبه تعداد موارد تطبیق نشده
        matched_bank_ids = [r["bank_id"] for r in results]
        matched_pos_ids = [r["pos_id"] for r in results]
        
        unmatched_bank = len([tx for tx in bank_transactions 
                            if tx.get('Transaction_Type_Bank') == "POS Deposit" 
                            and tx.get('id') not in matched_bank_ids])
        
        unmatched_pos = len([tx for tx in pos_transactions 
                           if tx.get('id') not in matched_pos_ids])
        
        return {
            "results": results,
            "matched": len(results),
            "unmatched": unmatched_bank + unmatched_pos
        }
    
    def reconcile_checks(self, bank_transactions: List[Dict[str, Any]] = None, 
                        accounting_entries: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        مغایرت‌گیری بین چک‌های بانکی و ورودی‌های حسابداری
        
        پارامترها:
            bank_transactions: لیست تراکنش‌های بانکی (اختیاری)
            accounting_entries: لیست ورودی‌های حسابداری (اختیاری)
            
        خروجی:
            دیکشنری حاوی نتایج مغایرت‌گیری
        """
        # اگر پارامترها ارسال نشده باشند، داده‌ها را از پایگاه داده دریافت می‌کنیم
        if bank_transactions is None:
            bank_transactions = self.db_manager.get_unreconciled_bank_transactions()
        if accounting_entries is None:
            accounting_entries = self.db_manager.get_unreconciled_accounting_entries()
        logger.info("شروع مغایرت‌گیری چک‌ها...")
        results = []
        
        # فیلتر کردن تراکنش‌های بانکی از نوع چک
        check_transactions = [t for t in bank_transactions 
                             if t.get('Transaction_Type_Bank') in ["Received Check", "Paid Check"]]
        logger.info(f"تعداد تراکنش‌های چک بانکی: {len(check_transactions)}")
        
        for bank_tx in check_transactions:
            check_type = bank_tx.get('Transaction_Type_Bank')
            
            # تعیین مبلغ بر اساس نوع چک
            if check_type == "Received Check":
                bank_amount = bank_tx.get('Deposit_Amount')
                accounting_field = 'Debit'  # چک دریافتی در حسابداری بدهکار است
            else:  # Paid Check
                bank_amount = bank_tx.get('Withdrawal_Amount')
                accounting_field = 'Credit'  # چک پرداختی در حسابداری بستانکار است
            
            if not bank_amount:
                continue
                
            bank_description = str(bank_tx.get('Description_Bank', ''))
            
            # جستجو برای ورودی حسابداری منطبق
            for acc_entry in accounting_entries:
                acc_amount = acc_entry.get(accounting_field)
                acc_ref_suffix = str(acc_entry.get('Account_Reference_Suffix', ''))
                
                # بررسی تطابق مبلغ و شماره مرجع در توضیحات
                if (acc_amount and abs(float(bank_amount) - float(acc_amount)) < 0.01 and 
                    acc_ref_suffix and acc_ref_suffix in bank_description):
                    
                    # ثبت نتیجه مغایرت‌گیری
                    reconciliation_result = {
                        "bank_id": bank_tx.get('id'),
                        "accounting_id": acc_entry.get('id'),
                        "amount": bank_amount,
                        "check_type": check_type,
                        "account_reference": acc_ref_suffix,
                        "date_bank": bank_tx.get('Date'),
                        "tracking_id_bank": bank_tx.get('Bank_Tracking_ID')
                    }
                    
                    # ثبت در پایگاه داده
                    success = self.db_manager.record_reconciliation_result(
                        bank_id=bank_tx.get('id'),
                        pos_id=None,
                        accounting_id=acc_entry.get('id'),
                        reconciliation_type="Check",
                        notes=f"نوع چک: {check_type}, مبلغ: {bank_amount}, شماره مرجع: {acc_ref_suffix}"
                    )
                    
                    if success:
                        logger.info(f"مغایرت‌گیری موفق چک: بانک ID {bank_tx.get('id')}, حسابداری ID {acc_entry.get('id')}, مبلغ: {bank_amount}")
                        results.append(reconciliation_result)
                    break
        
        logger.info(f"مغایرت‌گیری چک‌ها: {len(results)} مورد تطبیق یافت شد.")
        
        # محاسبه تعداد موارد تطبیق نشده
        matched_bank_ids = [r["bank_id"] for r in results]
        matched_acc_ids = [r["accounting_id"] for r in results]
        
        unmatched_bank = len([tx for tx in bank_transactions 
                            if tx.get('Transaction_Type_Bank') in ["Received Check", "Paid Check"] 
                            and tx.get('id') not in matched_bank_ids])
        
        # تعداد ورودی‌های حسابداری مغایرت‌گیری نشده را نمی‌توان به طور دقیق محاسبه کرد
        # زیرا نمی‌دانیم کدام ورودی‌ها مربوط به چک هستند
        
        return {
            "results": results,
            "matched": len(results),
            "unmatched": unmatched_bank
        }
    
    def reconcile_transfers(self, bank_transactions: List[Dict[str, Any]] = None, 
                           accounting_entries: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        مغایرت‌گیری بین انتقال‌های بانکی و ورودی‌های حسابداری
        
        پارامترها:
            bank_transactions: لیست تراکنش‌های بانکی (اختیاری)
            accounting_entries: لیست ورودی‌های حسابداری (اختیاری)
            
        خروجی:
            دیکشنری حاوی نتایج مغایرت‌گیری
        """
        # اگر پارامترها ارسال نشده باشند، داده‌ها را از پایگاه داده دریافت می‌کنیم
        if bank_transactions is None:
            bank_transactions = self.db_manager.get_unreconciled_bank_transactions()
        if accounting_entries is None:
            accounting_entries = self.db_manager.get_unreconciled_accounting_entries()
        logger.info("شروع مغایرت‌گیری انتقال‌ها...")
        results = []
        
        # فیلتر کردن تراکنش‌های بانکی از نوع انتقال
        transfer_transactions = [t for t in bank_transactions 
                               if t.get('Transaction_Type_Bank') in ["Received Transfer", "Paid Transfer"]]
        logger.info(f"تعداد تراکنش‌های انتقال بانکی: {len(transfer_transactions)}")
        
        for bank_tx in transfer_transactions:
            transfer_type = bank_tx.get('Transaction_Type_Bank')
            
            # تعیین مبلغ و فیلد حسابداری بر اساس نوع انتقال
            if transfer_type == "Received Transfer":
                bank_amount = bank_tx.get('Deposit_Amount')
                accounting_field = 'Debit'  # انتقال دریافتی در حسابداری بدهکار است
            else:  # Paid Transfer
                bank_amount = bank_tx.get('Withdrawal_Amount')
                accounting_field = 'Credit'  # انتقال پرداختی در حسابداری بستانکار است
            
            if not bank_amount:
                continue
                
            bank_date_str = bank_tx.get('Date')
            bank_tracking_id = str(bank_tx.get('Bank_Tracking_ID', ''))
            
            # جستجو برای ورودی حسابداری منطبق
            for acc_entry in accounting_entries:
                acc_amount = acc_entry.get(accounting_field)
                acc_date_str = acc_entry.get('Due_Date')
                acc_ref_suffix = str(acc_entry.get('Account_Reference_Suffix', ''))
                
                # بررسی تطابق مبلغ و تاریخ
                if (acc_amount and abs(float(bank_amount) - float(acc_amount)) < 0.01 and 
                    acc_date_str == bank_date_str):
                    
                    # بررسی اختیاری تطابق پسوند شناسه پیگیری
                    suffix_match = False
                    if acc_ref_suffix and bank_tracking_id:
                        if acc_ref_suffix in bank_tracking_id or bank_tracking_id[-len(acc_ref_suffix):] == acc_ref_suffix:
                            suffix_match = True
                    
                    # ثبت نتیجه مغایرت‌گیری
                    reconciliation_result = {
                        "bank_id": bank_tx.get('id'),
                        "accounting_id": acc_entry.get('id'),
                        "amount": bank_amount,
                        "transfer_type": transfer_type,
                        "date": bank_date_str,
                        "tracking_id_bank": bank_tracking_id,
                        "suffix_match": suffix_match
                    }
                    
                    # ثبت در پایگاه داده
                    success = self.db_manager.record_reconciliation_result(
                        bank_id=bank_tx.get('id'),
                        pos_id=None,
                        accounting_id=acc_entry.get('id'),
                        reconciliation_type="Transfer",
                        notes=f"نوع انتقال: {transfer_type}, مبلغ: {bank_amount}, تاریخ: {bank_date_str}, تطابق پسوند: {'بله' if suffix_match else 'خیر'}"
                    )
                    
                    if success:
                        logger.info(f"مغایرت‌گیری موفق انتقال: بانک ID {bank_tx.get('id')}, حسابداری ID {acc_entry.get('id')}, مبلغ: {bank_amount}")
                        results.append(reconciliation_result)
                    break
        
        logger.info(f"مغایرت‌گیری انتقال‌ها: {len(results)} مورد تطبیق یافت شد.")
        
        # محاسبه تعداد موارد تطبیق نشده
        matched_bank_ids = [r["bank_id"] for r in results]
        matched_acc_ids = [r["accounting_id"] for r in results]
        
        unmatched_bank = len([tx for tx in bank_transactions 
                            if tx.get('Transaction_Type_Bank') in ["Received Transfer", "Paid Transfer"] 
                            and tx.get('id') not in matched_bank_ids])
        
        # تعداد ورودی‌های حسابداری مغایرت‌گیری نشده را نمی‌توان به طور دقیق محاسبه کرد
        # زیرا نمی‌دانیم کدام ورودی‌ها مربوط به انتقال هستند
        
        return {
            "results": results,
            "matched": len(results),
            "unmatched": unmatched_bank
        }
    
    def reconcile_pos_accounting(self, pos_transactions: List[Dict[str, Any]] = None, 
                               accounting_entries: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        مغایرت‌گیری بین تراکنش‌های پوز و ورودی‌های حسابداری
        
        پارامترها:
            pos_transactions: لیست تراکنش‌های پوز (اختیاری)
            accounting_entries: لیست ورودی‌های حسابداری (اختیاری)
            
        خروجی:
            دیکشنری حاوی نتایج مغایرت‌گیری
        """
        # اگر پارامترها ارسال نشده باشند، داده‌ها را از پایگاه داده دریافت می‌کنیم
        if pos_transactions is None:
            pos_transactions = self.db_manager.get_unreconciled_pos_transactions()
        if accounting_entries is None:
            accounting_entries = self.db_manager.get_unreconciled_accounting_entries()
        logger.info("شروع مغایرت‌گیری پوز-حسابداری...")
        results = []
        
        # فیلتر کردن ورودی‌های حسابداری مرتبط با پوز
        pos_accounting_entries = [e for e in accounting_entries 
                                if "پوز دریافتنی" in str(e.get('Entry_Type_Acc', '')) or 
                                "پوز" in str(e.get('Description_Notes_Acc', ''))]  # فیلتر بر اساس نوع یا توضیحات
        
        logger.info(f"تعداد ورودی‌های حسابداری مرتبط با پوز: {len(pos_accounting_entries)}")
        
        for pos_tx in pos_transactions:
            pos_amount = pos_tx.get('Transaction_Amount')
            pos_date_str = pos_tx.get('Transaction_Date')
            pos_terminal_id = pos_tx.get('Terminal_ID')
            
            if not pos_amount or not pos_date_str:
                continue
                
            # تبدیل تاریخ پوز به شیء datetime
            try:
                pos_date = datetime.strptime(pos_date_str, '%Y/%m/%d')
                # محدوده تاریخ برای جستجو (±1 روز)
                date_range = [
                    (pos_date - timedelta(days=1)).strftime('%Y/%m/%d'),
                    pos_date_str,
                    (pos_date + timedelta(days=1)).strftime('%Y/%m/%d')
                ]
            except Exception as e:
                logger.warning(f"خطا در تبدیل تاریخ پوز: {str(e)}, تاریخ: {pos_date_str}, شناسه: {pos_tx.get('id')}")
                continue
            
            # جستجو برای ورودی حسابداری منطبق
            for acc_entry in pos_accounting_entries:
                acc_amount = acc_entry.get('Debit')  # پوز دریافتنی در حسابداری بدهکار است
                acc_date_str = acc_entry.get('Due_Date')
                acc_description = str(acc_entry.get('Description_Notes_Acc', ''))
                
                # بررسی تطابق مبلغ، تاریخ و شناسه ترمینال
                if (acc_amount and abs(float(pos_amount) - float(acc_amount)) < 0.01 and 
                    acc_date_str in date_range and 
                    (pos_terminal_id in acc_description or not pos_terminal_id)):
                    
                    # ثبت نتیجه مغایرت‌گیری
                    reconciliation_result = {
                        "pos_id": pos_tx.get('id'),
                        "accounting_id": acc_entry.get('id'),
                        "amount": pos_amount,
                        "date_pos": pos_date_str,
                        "date_accounting": acc_date_str,
                        "terminal_id": pos_terminal_id,
                        "tracking_id_pos": pos_tx.get('POS_Tracking_Number')
                    }
                    
                    # ثبت در پایگاه داده
                    success = self.db_manager.record_reconciliation_result(
                        bank_id=None,
                        pos_id=pos_tx.get('id'),
                        accounting_id=acc_entry.get('id'),
                        reconciliation_type="POS-Accounting",
                        notes=f"مبلغ: {pos_amount}, تاریخ پوز: {pos_date_str}, تاریخ حسابداری: {acc_date_str}, ترمینال: {pos_terminal_id}"
                    )
                    
                    if success:
                        logger.info(f"مغایرت‌گیری موفق پوز-حسابداری: پوز ID {pos_tx.get('id')}, حسابداری ID {acc_entry.get('id')}, مبلغ: {pos_amount}")
                        results.append(reconciliation_result)
                    break
        
        logger.info(f"مغایرت‌گیری پوز-حسابداری: {len(results)} مورد تطبیق یافت شد.")
        
        # محاسبه تعداد موارد تطبیق نشده
        matched_pos_ids = [r["pos_id"] for r in results]
        matched_acc_ids = [r["accounting_id"] for r in results]
        
        unmatched_pos = len([tx for tx in pos_transactions 
                           if tx.get('id') not in matched_pos_ids])
        
        # تعداد ورودی‌های حسابداری مغایرت‌گیری نشده مرتبط با پوز
        pos_accounting_entries = [e for e in accounting_entries 
                                if "پوز دریافتنی" in str(e.get('Entry_Type_Acc', '')) or 
                                "پوز" in str(e.get('Description_Notes_Acc', ''))]
        
        unmatched_acc = len([e for e in pos_accounting_entries 
                           if e.get('id') not in matched_acc_ids])
        
        return {
            "results": results,
            "matched": len(results),
            "unmatched": unmatched_pos + unmatched_acc
        }
    
    def find_card_suffix_hints(self, pos_transactions: List[Dict[str, Any]] = None, 
                              accounting_entries: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        یافتن پیشنهادهای مطابقت بر اساس 4 رقم آخر کارت
        
        پارامترها:
            pos_transactions: لیست تراکنش‌های پوز (اختیاری)
            accounting_entries: لیست ورودی‌های حسابداری (اختیاری)
            
        خروجی:
            دیکشنری حاوی نتایج و آمار پیشنهادهای مطابقت
        """
        # اگر پارامترها ارسال نشده باشند، داده‌ها را از پایگاه داده دریافت می‌کنیم
        if pos_transactions is None:
            pos_transactions = self.db_manager.get_unreconciled_pos_transactions()
        if accounting_entries is None:
            accounting_entries = self.db_manager.get_unreconciled_accounting_entries()
        logger.info("شروع یافتن پیشنهادهای مطابقت بر اساس پسوند کارت...")
        hints = []
        
        # فیلتر کردن ورودی‌های حسابداری با پسوند کارت
        acc_entries_with_card = [e for e in accounting_entries if e.get('Extracted_Card_Suffix_Acc')]
        logger.info(f"تعداد ورودی‌های حسابداری با پسوند کارت: {len(acc_entries_with_card)}")
        
        for pos_tx in pos_transactions:
            card_number = str(pos_tx.get('Card_Number', ''))
            pos_amount = pos_tx.get('Transaction_Amount')
            
            if not card_number or len(card_number) < 4 or not pos_amount:
                continue
                
            # استخراج 4 رقم آخر کارت
            card_suffix = card_number[-4:]
            
            # جستجو برای ورودی حسابداری با پسوند کارت مشابه
            for acc_entry in acc_entries_with_card:
                acc_card_suffix = acc_entry.get('Extracted_Card_Suffix_Acc')
                acc_amount = acc_entry.get('Debit')
                
                if acc_card_suffix == card_suffix and acc_amount and abs(float(pos_amount) - float(acc_amount)) < 0.01:
                    # ایجاد پیشنهاد مطابقت
                    hint = {
                        "pos_id": pos_tx.get('id'),
                        "accounting_id": acc_entry.get('id'),
                        "card_suffix": card_suffix,
                        "amount": pos_amount,
                        "date_pos": pos_tx.get('Transaction_Date'),
                        "date_accounting": acc_entry.get('Due_Date'),
                        "terminal_id": pos_tx.get('Terminal_ID'),
                        "tracking_id_pos": pos_tx.get('POS_Tracking_Number')
                    }
                    
                    logger.info(f"پیشنهاد مطابقت بر اساس پسوند کارت: پوز ID {pos_tx.get('id')}, حسابداری ID {acc_entry.get('id')}, پسوند کارت: {card_suffix}, مبلغ: {pos_amount}")
                    hints.append(hint)
        
        logger.info(f"یافتن پیشنهادهای مطابقت بر اساس پسوند کارت: {len(hints)} مورد پیشنهاد یافت شد.")
        return {
            "results": hints,
            "matched": 0,  # این مقدار صفر است زیرا این فقط پیشنهاد است و هنوز مغایرت‌گیری انجام نشده
            "unmatched": 0  # این مقدار صفر است زیرا این فقط پیشنهاد است و هنوز مغایرت‌گیری انجام نشده
        }
    
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
            logger.info(f"مغایرت‌گیری دستی با موفقیت انجام شد. نوع: {reconciliation_type}, بانک ID: {bank_id}, پوز ID: {pos_id}, حسابداری ID: {accounting_id}")
        else:
            logger.error("خطا در انجام مغایرت‌گیری دستی.")
        
        return success