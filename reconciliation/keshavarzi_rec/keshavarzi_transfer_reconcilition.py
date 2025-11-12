"""
فایل مغایرت‌گیری انتقال‌های بانک کشاورزی
شامل انتقال‌های دریافتی و پرداختی
"""
from datetime import datetime, timedelta
from database.repositories.accounting import get_transactions_by_date_amount_type
from database.bank_transaction_repository import update_bank_transaction_reconciliation_status
from database.reconciliation_results_repository import create_reconciliation_result
from database.repositories.reconciliation_repository import ReconciliationRepository, ReconciliationHelpers
from utils.unified_logger import (
    log_info, log_warning, log_error, 
    log_operation_start, log_operation_end,
    log_reconciliation_summary
)

def reconcile_keshavarzi_transfers(bank_transactions, ui_handler=None):
    """
    مغایرت‌گیری انتقال‌های بانک کشاورزی (دریافتی و پرداختی)
    
    Args:
        bank_transactions: لیست تراکنش‌های بانکی انتقال
        ui_handler: شیء مدیریت رابط کاربری
    """
    try:
        reconciled_count = 0
        total_count = len(bank_transactions)
        
        log_operation_start("Keshavarzi Transfer Reconciliation", f"تعداد کل تراکنش‌ها: {total_count}")
        if ui_handler:
            ui_handler.log_info(f"شروع مغایرت‌گیری {total_count} تراکنش انتقال کشاورزی")
        
        for i, bank_transaction in enumerate(bank_transactions):
            try:
                # تعیین نوع انتقال (دریافتی یا پرداختی)
                transaction_type = bank_transaction.get('transaction_type', '').strip()
                
                if not transaction_type:
                    log_warning(f"نوع تراکنش انتقال مشخص نیست: {bank_transaction.get('id')}")
                    continue
                
                # مغایرت‌گیری بر اساس نوع
                result = reconcile_single_transfer(bank_transaction, transaction_type)
                
                if result:
                    reconciled_count += 1
                    log_info(f"انتقال با شناسه {bank_transaction.get('id')} مغایرت‌گیری شد")
                
                # به‌روزرسانی پیشرفت
                if ui_handler:
                    progress = ((i + 1) / total_count) * 100
                    ui_handler.update_detailed_progress(int(progress))
                    ui_handler.update_detailed_status(f"مغایرت‌گیری انتقال {i + 1} از {total_count}")
            
            except Exception as e:
                log_error(f"خطا در مغایرت‌گیری انتقال {bank_transaction.get('id')}: {str(e)}")
                continue
        
        log_operation_end("Keshavarzi Transfer Reconciliation", True, f"تطبیق یافته: {reconciled_count} از {total_count}")
        log_reconciliation_summary("کشاورزی", "انتقال", total_count, reconciled_count, total_count - reconciled_count)
        if ui_handler:
            ui_handler.log_info(f"مغایرت‌گیری انتقال‌ها تکمیل شد. {reconciled_count} از {total_count} مغایرت‌گیری شدند")
        
        return reconciled_count
        
    except Exception as e:
        log_operation_end("Keshavarzi Transfer Reconciliation", False, str(e))
        log_error(f"خطا در فرآیند مغایرت‌گیری انتقال‌ها: {str(e)}")
        if ui_handler:
            ui_handler.log_error(f"خطا در فرآیند مغایرت‌گیری انتقال‌ها: {str(e)}")
        return 0

# def determine_transfer_type(bank_transaction):
#     """
#     تعیین نوع انتقال (دریافتی یا پرداختی) بر اساس اطلاعات تراکنش بانک
#     """
#     transaction_type = bank_transaction.get('transaction_type', '').strip()
    
#     # تبدیل نوع تراکنش بانک به نوع حسابداری
#     if 'Received_Transfer' in transaction_type or 'دریافتی' in transaction_type:
#         return 'Received Transfer'
#     elif 'Paid_Transfer' in transaction_type or 'پرداختی' in transaction_type:
#         return 'Paid Transfer'
    
#     return None

def reconcile_single_transfer(bank_transaction, transfer_type):
    """
    مغایرت‌گیری یک انتقال منفرد
    
    Args:
        bank_transaction: تراکنش بانکی
        transfer_type: نوع انتقال (Received Transfer یا Paid Transfer)
    
    Returns:
        bool: True اگر موفق باشد
    """
    try:
        bank_id = bank_transaction.get('bank_id')
        bank_amount = bank_transaction.get('amount')
        bank_date = bank_transaction.get('transaction_date')
        
        # جستجوی تراکنش‌های حسابداری بر اساس due_date و مبلغ
        accounting_transactions = ReconciliationRepository.get_accounting_by_date_amount_type_abs(
            bank_id, bank_date, bank_amount, transfer_type
        )
        
        if not accounting_transactions:
            log_warning(f"هیچ تراکنش حسابداری یافت نشد برای انتقال {bank_transaction.get('id')}")
            return False
        
        # اگر فقط یک رکورد برگشت
        if len(accounting_transactions) == 1:
            return perform_reconciliation(bank_transaction, accounting_transactions[0], None, transfer_type)
        
        # اگر چند رکورد برگشت، مراحل جستجوی پیشرفته
        else:
            matched_transaction = find_best_match_for_transfer(bank_transaction, accounting_transactions)
            if matched_transaction:
                return perform_reconciliation(bank_transaction, matched_transaction, None, transfer_type)
        
        log_warning(f"نتوانستیم تراکنش مناسب برای انتقال {bank_transaction.get('id')} پیدا کنیم")
        return False
        
    except Exception as e:
        log_error(f"خطا در مغایرت‌گیری انتقال منفرد: {str(e)}")
        return False

def find_best_match_for_transfer(bank_transaction, accounting_transactions):
    """
    پیدا کردن بهترین تطبیق برای انتقال‌ها با روش‌های مختلف
    
    روش‌ها:
    1. مقایسه شماره پیگری سیستم حسابداری با extracted_tracking_number یا reference_number
    2. جستجو source_card_number در description حسابداری
    """
    # مرحله 1: جستجو بر اساس شماره پیگیری
    tracking_match = find_matching_by_tracking_number(bank_transaction, accounting_transactions)
    if tracking_match:
        log_info("تطبیق بر اساس شماره پیگیری یافت شد")
        return tracking_match
    
    # مرحله 2: جستجو بر اساس شماره کارت
    card_match = find_matching_by_card_number(bank_transaction, accounting_transactions)
    if card_match:
        log_info("تطبیق بر اساس شماره کارت یافت شد")
        return card_match
    
    log_warning("هیچ تطبیق مناسبی یافت نشد")
    return None

def find_matching_by_tracking_number(bank_transaction, accounting_transactions):
    """
    جستجوی تطبیق بر اساس شماره پیگیری
    
    مقایسه transaction_number حسابداری با extracted_tracking_number و reference_number بانک
    """
    bank_extracted_tracking = str(bank_transaction.get('extracted_tracking_number', ''))
    bank_reference = str(bank_transaction.get('reference_number', ''))
    
    for acc_transaction in accounting_transactions:
        acc_tracking = str(acc_transaction.get('transaction_number', ''))
        
        if acc_tracking and (
            acc_tracking == bank_extracted_tracking or
            acc_tracking == bank_reference or
            acc_tracking in bank_extracted_tracking or
            acc_tracking in bank_reference
        ):
            log_info(f"تطبیق شماره پیگیری: {acc_tracking}")
            return acc_transaction
    
    return None

def find_matching_by_card_number(bank_transaction, accounting_transactions):
    """
    جستجوی تطبیق بر اساس شماره کارت
    
    جستجوی source_card_number بانک در description حسابداری
    (معمولاً بعد از کلمه "ک" قرار می‌گیرد)
    """
    source_card_number = str(bank_transaction.get('source_card_number', ''))
    
    if not source_card_number:
        return None
    
    for acc_transaction in accounting_transactions:
        description = str(acc_transaction.get('description', ''))
        
        # جستجوی شماره کارت در توضیحات
        # معمولاً بعد از کلمه "ک" قرار می‌گیرد
        if source_card_number in description:
            log_info(f"تطبیق شماره کارت: {source_card_number}")
            return acc_transaction
        
        # جستجوی چهار رقم آخر شماره کارت
        if len(source_card_number) >= 4:
            last_four_digits = source_card_number[-4:]
            if last_four_digits in description:
                log_info(f"تطبیق چهار رقم آخر کارت: {last_four_digits}")
                return acc_transaction
    
    return None

# تابع get_transactions_by_date_amount_type_abs به ReconciliationRepository منتقل شد

def perform_reconciliation(bank_transaction, accounting_transaction, pos_transaction, transaction_type):
    """
    انجام عملیات مغایرت‌گیری و ثبت نتیجه
    """
    try:
        # به‌روزرسانی وضعیت تراکنش بانکی
        bank_id = bank_transaction.get('id')
        update_bank_transaction_reconciliation_status(bank_id, True)
        
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
        
        log_info(f"مغایرت‌گیری موفق: Bank ID={bank_id}, Acc ID={acc_id}")
        return True
        
    except Exception as e:
        log_error(f"خطا در انجام مغایرت‌گیری: {str(e)}")
        return False

# تابع update_accounting_transaction_reconciliation_status به ReconciliationRepository منتقل شد
