"""
فایل مغایرت‌گیری چک‌های بانک کشاورزی
شامل چک‌های دریافتی و پرداختی
"""
import logging
from datetime import datetime, timedelta
from database.accounting_repository import get_transactions_advanced_search
from database.bank_transaction_repository import update_bank_transaction_reconciliation_status
from database.repositories.accounting import (
    get_transactions_by_date_amount_type,
    get_transactions_by_date_less_than_amount_type
)
from database.repositories.reconciliation_repository import ReconciliationRepository, ReconciliationHelpers
from utils.logger_config import setup_logger

# راه‌اندازی لاگر
logger = setup_logger('reconciliation.keshavarzi_check')

def reconcile_keshavarzi_checks(bank_transactions, ui_handler=None):
    """
    مغایرت‌گیری چک‌های بانک کشاورزی (دریافتی و پرداختی)
    
    Args:
        bank_transactions: لیست تراکنش‌های بانکی چک
        ui_handler: شیء مدیریت رابط کاربری
    """
    try:
        reconciled_count = 0
        total_count = len(bank_transactions)
        
        logger.info(f"شروع مغایرت‌گیری {total_count} تراکنش چک کشاورزی")
        if ui_handler:
            ui_handler.log_info(f"شروع مغایرت‌گیری {total_count} تراکنش چک کشاورزی")
        
        for i, bank_transaction in enumerate(bank_transactions):
            try:
                # تعیین نوع چک (دریافتی یا پرداختی)
                transaction_type = bank_transaction.get('transaction_type', '').strip()
                
                if not transaction_type:
                    logger.warning(f"نوع تراکنش چک مشخص نیست: {bank_transaction.get('id')}")
                    continue
                
                # مغایرت‌گیری بر اساس نوع
                result = reconcile_single_check(bank_transaction, transaction_type)
                
                if result:
                    reconciled_count += 1
                    logger.info(f"چک با شناسه {bank_transaction.get('id')} مغایرت‌گیری شد")
                
                # به‌روزرسانی پیشرفت
                if ui_handler:
                    progress = ((i + 1) / total_count) * 100
                    ui_handler.update_detailed_progress(int(progress))
                    ui_handler.update_detailed_status(f"مغایرت‌گیری چک {i + 1} از {total_count}")
            
            except Exception as e:
                logger.error(f"خطا در مغایرت‌گیری چک {bank_transaction.get('id')}: {str(e)}")
                continue
        
        logger.info(f"مغایرت‌گیری چک‌ها تکمیل شد. {reconciled_count} از {total_count} مغایرت‌گیری شدند")
        if ui_handler:
            ui_handler.log_info(f"مغایرت‌گیری چک‌ها تکمیل شد. {reconciled_count} از {total_count} مغایرت‌گیری شدند")
        
        return reconciled_count
        
    except Exception as e:
        logger.error(f"خطا در فرآیند مغایرت‌گیری چک‌ها: {str(e)}")
        if ui_handler:
            ui_handler.log_error(f"خطا در فرآیند مغایرت‌گیری چک‌ها: {str(e)}")
        return 0

# def determine_check_type(bank_transaction):
#     """
#     تعیین نوع چک (دریافتی یا پرداختی) بر اساس اطلاعات تراکنش بانک
#     """
#     transaction_type = bank_transaction.get('transaction_type', '').strip()
    
#     # تبدیل نوع تراکنش بانک به نوع حسابداری
#     if 'Received_Check' in transaction_type or 'دریافتی' in transaction_type:
#         return 'Received_Check'
#     elif 'Paid_Check' in transaction_type or 'پرداختی' in transaction_type:
#         return 'Paid_Check'
    
#     return None

def reconcile_single_check(bank_transaction, check_type):
    """
    مغایرت‌گیری یک چک منفرد
    
    Args:
        bank_transaction: تراکنش بانکی
        check_type: نوع چک (Received Check یا Paid Check)
    
    Returns:
        bool: True اگر موفق باشد
    """
    try:
        bank_id = bank_transaction.get('bank_id')
        bank_amount = bank_transaction.get('amount')
        bank_date = bank_transaction.get('transaction_date')
        
        # جستجوی تراکنش‌های حسابداری بر اساس collection_date و مبلغ
        accounting_transactions = ReconciliationRepository.get_transactions_by_collection_date_and_amount(
            bank_id, bank_date, bank_amount, check_type
        )
        
        if not accounting_transactions:
            logger.warning(f"هیچ تراکنش حسابداری یافت نشد برای چک {bank_transaction.get('id')}")
            return False
        
        # اگر فقط یک رکورد برگشت
        if len(accounting_transactions) == 1:
            # بررسی شماره پیگیری
            if ReconciliationHelpers.verify_tracking_number(bank_transaction, accounting_transactions[0]):
                return perform_reconciliation(bank_transaction, accounting_transactions[0], None, check_type)
        
        # اگر چند رکورد برگشت، جستجو بر اساس شماره پیگیری
        else:
            matched_transaction = ReconciliationHelpers.find_matching_by_tracking_number(bank_transaction, accounting_transactions)
            if matched_transaction:
                return perform_reconciliation(bank_transaction, matched_transaction, None, check_type)
        
        logger.warning(f"نتوانستیم تراکنش مناسب برای چک {bank_transaction.get('id')} پیدا کنیم")
        return False
        
    except Exception as e:
        logger.error(f"خطا در مغایرت‌گیری چک منفرد: {str(e)}")
        return False

# توابع get_transactions_by_collection_date_and_amount، verify_tracking_number و find_matching_by_tracking_number به ReconciliationRepository منتقل شدند
        
        # به‌روزرسانی وضعیت تراکنش حسابداری
        if accounting_transaction:
            ReconciliationRepository.update_accounting_reconciliation_status(
                accounting_transaction.get('id'), True
            )
        
        # ثبت نتیجه مغایرت‌گیری
        pos_id = pos_transaction.get('id') if pos_transaction else None
        acc_id = accounting_transaction.get('id') if accounting_transaction else None
        
        description = f"مغایرت‌گیری {transaction_type} - مبلغ: {bank_transaction.get('amount')}"
        
        create_reconciliation_result(
            pos_id=pos_id,
            acc_id=acc_id,
            bank_record_id=bank_id,
            description=description,
            type_matched=transaction_type
        )
        
        logger.info(f"مغایرت‌گیری موفق: Bank ID={bank_id}, Acc ID={acc_id}")
        return True
        
    except Exception as e:
        logger.error(f"خطا در انجام مغایرت‌گیری: {str(e)}")
        return False

# تابع update_accounting_transaction_reconciliation_status به ReconciliationRepository منتقل شد
