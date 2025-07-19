#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول اصلی مغایرت‌گیری
این ماژول کلاس ReconciliationEngine را شامل می‌شود که تمام عملیات مغایرت‌گیری را هماهنگ می‌کند.
"""

from typing import Dict, List, Optional, Any

from modules.database_manager import DatabaseManager
from modules.logger import get_logger
from modules.pos_deposit_reconciliation import PosDepositReconciliation
from modules.received_transfer_reconciliation import ReceivedTransferReconciliation
from modules.paid_transfer_reconciliation import PaidTransferReconciliation
from modules.received_check_reconciliation import ReceivedCheckReconciliation
from modules.paid_check_reconciliation import PaidCheckReconciliation

# ایجاد شیء لاگر
logger = get_logger(__name__)

class ReconciliationEngine:
    """
    موتور اصلی مغایرت‌گیری
    این کلاس تمام عملیات مغایرت‌گیری را هماهنگ می‌کند
    """
    
    def __init__(self):
        """
        سازنده کلاس
        """
        self.db_manager = DatabaseManager()
        
        # ایجاد نمونه‌هایی از ماژول‌های مغایرت‌گیری
        self.pos_reconciler = PosDepositReconciliation()
        self.received_transfer_reconciler = ReceivedTransferReconciliation()
        self.paid_transfer_reconciler = PaidTransferReconciliation()
        self.received_check_reconciler = ReceivedCheckReconciliation()
        self.paid_check_reconciler = PaidCheckReconciliation()
        
        logger.info("موتور مغایرت‌گیری راه‌اندازی شد")
    
    def start_reconciliation(self, selected_bank_id: int) -> Dict[str, Any]:
        """
        شروع فرآیند مغایرت‌گیری
        
        پارامترها:
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            نتایج مغایرت‌گیری
        """
        logger.info(f"🚀 شروع فرآیند مغایرت‌گیری برای بانک {selected_bank_id}")
        
        # دریافت تراکنش‌های مغایرت‌گیری نشده بانک
        bank_transactions = self.db_manager.get_unreconciled_bank_transactions(selected_bank_id)
        logger.info(f"📊 تعداد تراکنش‌های بانکی مغایرت‌گیری نشده: {len(bank_transactions)}")
        
        if not bank_transactions:
            logger.info("هیچ تراکنش بانکی مغایرت‌گیری نشده‌ای یافت نشد")
            return {"message": "هیچ تراکنش بانکی مغایرت‌گیری نشده‌ای یافت نشد"}
        
        # آمار پردازش
        processed_count = 0
        successful_matches = 0
        
        # پردازش هر تراکنش بانکی
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
        
        if transaction_type == "Pos Deposit":
            return self.pos_reconciler.reconcile_pos_deposit(bank_record, selected_bank_id)
            
        elif transaction_type == "Received Transfer":
            return self.received_transfer_reconciler.reconcile_received_transfer(bank_record, selected_bank_id)
            
        elif transaction_type == "Paid Transfer":
            return self.paid_transfer_reconciler.reconcile_paid_transfer(bank_record, selected_bank_id)
            
        elif transaction_type == "Received Check":
            return self.received_check_reconciler.reconcile_received_check(bank_record, selected_bank_id)
            
        elif transaction_type == "Paid Check":
            return self.paid_check_reconciler.reconcile_paid_check(bank_record, selected_bank_id)
            
        else:
            logger.warning(f"نوع تراکنش ناشناخته: {transaction_type}")
            # علامت‌گذاری به عنوان پردازش شده با یادداشت
            self._mark_bank_record_reconciled(
                bank_record.get('id'), 
                f"نوع تراکنش ناشناخته: {transaction_type}"
            )
            return True
    
    def get_unreconciled_bank_transactions(self, selected_bank_id: int) -> List[Dict[str, Any]]:
        """
        دریافت تراکنش‌های بانکی مغایرت‌گیری نشده
        
        پارامترها:
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            لیست تراکنش‌های مغایرت‌گیری نشده
        """
        return self.db_manager.get_unreconciled_bank_transactions(selected_bank_id)
    
    def get_unreconciled_pos_transactions(self, selected_bank_id: int) -> List[Dict[str, Any]]:
        """
        دریافت تراکنش‌های پوز مغایرت‌گیری نشده
        
        پارامترها:
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            لیست تراکنش‌های پوز مغایرت‌گیری نشده
        """
        return self.db_manager.get_unreconciled_pos_transactions(selected_bank_id)
    
    def get_unreconciled_accounting_entries(self, selected_bank_id: int) -> List[Dict[str, Any]]:
        """
        دریافت ورودی‌های حسابداری مغایرت‌گیری نشده
        
        پارامترها:
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            لیست ورودی‌های حسابداری مغایرت‌گیری نشده
        """
        return self.db_manager.get_unreconciled_accounting_entries(selected_bank_id)
    
    def manual_reconcile(self, bank_id: int, pos_id: int = None, accounting_id: int = None, notes: str = None) -> bool:
        """
        مغایرت‌گیری دستی
        
        پارامترها:
            bank_id: شناسه تراکنش بانکی
            pos_id: شناسه تراکنش پوز (اختیاری)
            accounting_id: شناسه ورودی حسابداری (اختیاری)
            notes: یادداشت‌ها
            
        خروجی:
            موفقیت عملیات
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
        
        پارامترها:
            selected_bank_id: شناسه بانک انتخاب شده
            
        خروجی:
            آمار مغایرت‌گیری
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