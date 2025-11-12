"""
فایل مغایرت‌گیری POS بانک کشاورزی
شامل الگوریتم پیچیده مغایرت‌گیری POS با استفاده از جدول pos_transactions
"""
from datetime import datetime, timedelta
from database.repositories.accounting import get_transactions_by_date_amount_type
from database.bank_transaction_repository import update_bank_transaction_reconciliation_status
from database.pos_transactions_repository import (
    get_transactions_by_terminal, 
    get_transactions_by_date_and_terminal,
    update_reconciliation_status
)
from database.reconciliation_results_repository import create_reconciliation_result
from database.repositories.reconciliation_repository import ReconciliationRepository, ReconciliationHelpers
from utils.unified_logger import (
    log_info, log_warning, log_error, 
    log_operation_start, log_operation_end,
    log_reconciliation_summary
)

def reconcile_keshavarzi_pos(bank_transactions, ui_handler=None):
    """
    مغایرت‌گیری POS بانک کشاورزی با استفاده از جدول pos_transactions
    
    Args:
        bank_transactions: لیست تراکنش‌های بانکی POS
        ui_handler: شیء مدیریت رابط کاربری
    """
    try:
        reconciled_count = 0
        total_count = len(bank_transactions)
        
        log_operation_start("Keshavarzi POS Reconciliation", f"تعداد کل تراکنش‌ها: {total_count}")
        if ui_handler:
            ui_handler.log_info(f"شروع مغایرت‌گیری {total_count} تراکنش POS کشاورزی")
        
        for i, bank_transaction in enumerate(bank_transactions):
            try:
                # مغایرت‌گیری هر تراکنش POS
                result = reconcile_single_pos(bank_transaction)
                
                if result:
                    reconciled_count += 1
                    log_info(f"POS با شناسه {bank_transaction.get('id')} مغایرت‌گیری شد")
                
                # به‌روزرسانی پیشرفت
                if ui_handler:
                    progress = ((i + 1) / total_count) * 100
                    ui_handler.update_detailed_progress(int(progress))
                    ui_handler.update_detailed_status(f"مغایرت‌گیری POS {i + 1} از {total_count}")
            
            except Exception as e:
                log_error(f"خطا در مغایرت‌گیری POS {bank_transaction.get('id')}: {str(e)}")
                continue
        
        log_operation_end("Keshavarzi POS Reconciliation", True, f"تطبیق یافته: {reconciled_count} از {total_count}")
        log_reconciliation_summary("کشاورزی", "POS", total_count, reconciled_count, total_count - reconciled_count)
        if ui_handler:
            ui_handler.log_info(f"مغایرت‌گیری POS‌ها تکمیل شد. {reconciled_count} از {total_count} مغایرت‌گیری شدند")
        
        return reconciled_count
        
    except Exception as e:
        log_operation_end("Keshavarzi POS Reconciliation", False, str(e))
        log_error(f"خطا در فرآیند مغایرت‌گیری POS‌ها: {str(e)}")
        if ui_handler:
            ui_handler.log_error(f"خطا در فرآیند مغایرت‌گیری POS‌ها: {str(e)}")
        return 0

def reconcile_single_pos(bank_transaction):
    """
    مغایرت‌گیری یک تراکنش POS منفرد با الگوریتم پیچیده
    
    Args:
        bank_transaction: تراکنش بانکی POS
    
    Returns:
        bool: True اگر موفق باشد
    """
    try:
        # مرحله 1: دریافت extracted_terminal_id از رکورد بانک
        extracted_terminal_id = bank_transaction.get('extracted_terminal_id')
        if not extracted_terminal_id:
            log_warning(f"extracted_terminal_id یافت نشد برای تراکنش {bank_transaction.get('id')}")
            return False
        
        # مرحله 2: محاسبه pos_date (یک روز کمتر از تاریخ بانک)
        bank_date_str = bank_transaction.get('transaction_date')
        if not bank_date_str:
            log_warning(f"تاریخ تراکنش یافت نشد برای {bank_transaction.get('id')}")
            return False
        
        pos_date = ReconciliationHelpers.calculate_pos_date_from_bank_date(bank_date_str)
        log_info(f"تاریخ محاسبه شده POS: {pos_date} (از تاریخ بانک: {bank_date_str})")
        
        # مرحله 3: پیدا کردن terminal_id از جدول PosTransactions
        terminal_id = ReconciliationRepository.find_terminal_id_by_terminal_number(extracted_terminal_id)
        if not terminal_id:
            log_warning(f"terminal_id یافت نشد برای terminal_number: {extracted_terminal_id}")
            return apply_fallback_reconciliation_strategy(bank_transaction, extracted_terminal_id, pos_date)
        
        log_info(f"terminal_id یافت شد: {terminal_id} برای terminal_number: {extracted_terminal_id}")
        
        # مرحله 4: جستجوی terminal_id در جدول حسابداری به عنوان شماره پیگیری
        accounting_match = ReconciliationRepository.find_accounting_by_terminal_id(
            bank_transaction.get('bank_id'), terminal_id, bank_transaction.get('amount')
        )
        
        if accounting_match:
            # بررسی برابری مبلغ با احتساب مقادیر منفی/مثبت
            acc_amount = abs(float(accounting_match.get('transaction_amount', 0)))
            bank_amount = abs(float(bank_transaction.get('amount', 0)))
            if acc_amount == bank_amount:
                # مغایرت‌گیری رکورد بانک و حسابداری
                result = perform_reconciliation(
                    bank_transaction, accounting_match, None, 'Pos'
                )
                if result:
                    # مغایرت‌گیری تمام POS‌های مرتبط در آن روز
                    ReconciliationRepository.mark_pos_transactions_reconciled_by_terminal_date(terminal_id, pos_date)
                    return True
        
        # مرحله 5: اگر روش بالا کار نکرد، استراتژی جایگزین
        return apply_fallback_reconciliation_strategy(bank_transaction, extracted_terminal_id, pos_date)
        
    except Exception as e:
        log_error(f"خطا در مغایرت‌گیری POS منفرد: {str(e)}")
        return False

# توابع calculate_pos_date و find_terminal_id_by_terminal_number به ReconciliationRepository و ReconciliationHelpers منتقل شدند

# توابع find_accounting_by_terminal_id و mark_related_pos_transactions_reconciled به ReconciliationRepository منتقل شدند

def apply_fallback_reconciliation_strategy(bank_transaction, terminal_number, pos_date):
    """
    استراتژی جایگزین برای مغایرت‌گیری POS‌ها
    
    شامل مغایرت‌گیری تک‌تک رکوردهای POS با حسابداری
    """
    try:
        log_info(f"اعمال استراتژی جایگزین برای terminal_number: {terminal_number}")
        
        # دریافت تراکنش‌های POS برای این terminal و تاریخ
        pos_transactions = ReconciliationRepository.get_pos_transactions_by_terminal_and_date(terminal_number, pos_date)
        
        if not pos_transactions:
            log_warning(f"هیچ تراکنش POS یافت نشد برای terminal: {terminal_number}, date: {pos_date}")
            return False
        
        reconciled_pos_count = 0
        
        # مغایرت‌گیری هر تراکنش POS با حسابداری
        for pos_transaction in pos_transactions:
            result = reconcile_individual_pos_transaction(pos_transaction, bank_transaction.get('bank_id'))
            if result:
                reconciled_pos_count += 1
        
        # اگر حداقل یک POS مغایرت‌گیری شد، رکورد بانک را هم reconciled کنیم
        if reconciled_pos_count > 0:
            update_bank_transaction_reconciliation_status(bank_transaction.get('id'), True)
            log_info(f"رکورد بانک {bank_transaction.get('id')} reconciled شد - {reconciled_pos_count} POS مغایرت‌گیری شدند")
            return True
        
        return False
        
    except Exception as e:
        log_error(f"خطا در استراتژی جایگزین: {str(e)}")
        return False

# تابع get_pos_transactions_by_terminal_and_date به ReconciliationRepository منتقل شد
def get_pos_transactions_by_terminal_and_date(terminal_number, date):
    """
    دریافت تراکنش‌های POS بر اساس شماره ترمینال و تاریخ
    """
    return ReconciliationRepository.get_pos_transactions_by_terminal_and_date(terminal_number, date)

def reconcile_individual_pos_transaction(pos_transaction, bank_id):
    """
    مغایرت‌گیری یک تراکنش POS منفرد با حسابداری
    """
    try:
        pos_amount = pos_transaction.get('transaction_amount')
        pos_date = pos_transaction.get('transaction_date')
        
        # جستجوی تراکنش حسابداری بر اساس تاریخ و مبلغ (با مقایسه مطلق)
        accounting_transactions = get_transactions_by_date_amount_type_pos_abs(
            bank_id, pos_date, pos_amount, 'Pos'
        )
        
        if not accounting_transactions:
            log_warning(f"هیچ تراکنش حسابداری یافت نشد برای POS {pos_transaction.get('id')}")
            return False
        
        # اگر فقط یک رکورد برگشت
        if len(accounting_transactions) == 1:
            result = perform_reconciliation(
                None, accounting_transactions[0], pos_transaction, 'Pos'
            )
            if result:
                update_reconciliation_status(pos_transaction.get('id'), True)
            return result
        
        # اگر چند رکورد برگشت، جستجوی پیشرفته
        matched_accounting = find_best_accounting_match_for_pos(pos_transaction, accounting_transactions)
        if matched_accounting:
            result = perform_reconciliation(
                None, matched_accounting, pos_transaction, 'Pos'
            )
            if result:
                update_reconciliation_status(pos_transaction.get('id'), True)
            return result
        
        return False
        
    except Exception as e:
        logger.error(f"خطا در مغایرت‌گیری تراکنش POS منفرد: {str(e)}")
        return False

def find_best_accounting_match_for_pos(pos_transaction, accounting_transactions):
    """
    پیدا کردن بهترین تطبیق حسابداری برای تراکنش POS
    
    روش‌ها:
    1. جستجوی چهار رقم آخر card_number در description حسابداری
    2. جستجوی tracking_number POS در transaction_number حسابداری
    """
    # روش 1: جستجوی بر اساس شماره کارت
    card_match = find_accounting_by_card_number(pos_transaction, accounting_transactions)
    if card_match:
        logger.info("تطبیق بر اساس شماره کارت یافت شد")
        return card_match
    
    # روش 2: جستجوی بر اساس شماره پیگیری
    tracking_match = find_accounting_by_tracking_number_pos(pos_transaction, accounting_transactions)
    if tracking_match:
        logger.info("تطبیق بر اساس شماره پیگیری یافت شد")
        return tracking_match
    
    logger.warning("هیچ تطبیق مناسبی برای POS یافت نشد")
    return None

def find_accounting_by_card_number(pos_transaction, accounting_transactions):
    """
    جستجوی تطبیق بر اساس چهار رقم آخر شماره کارت
    """
    card_number = str(pos_transaction.get('card_number', ''))
    
    if len(card_number) >= 4:
        last_four_digits = card_number[-4:]
        
        for acc_transaction in accounting_transactions:
            description = str(acc_transaction.get('description', ''))
            
            if last_four_digits in description:
                logger.info(f"تطبیق چهار رقم آخر کارت: {last_four_digits}")
                return acc_transaction
    
    return None

def find_accounting_by_tracking_number_pos(pos_transaction, accounting_transactions):
    """
    جستجوی تطبیق بر اساس شماره پیگیری POS
    """
    pos_tracking = str(pos_transaction.get('tracking_number', ''))
    
    if pos_tracking:
        for acc_transaction in accounting_transactions:
            acc_tracking = str(acc_transaction.get('transaction_number', ''))
            
            if pos_tracking == acc_tracking:
                logger.info(f"تطبیق شماره پیگیری: {pos_tracking}")
                return acc_transaction
    
    return None

# تابع get_transactions_by_date_amount_type_pos_abs به ReconciliationRepository منتقل شد
def get_transactions_by_date_amount_type_pos_abs(bank_id, transaction_date, amount, transaction_type):
    """
    دریافت تراکنش‌های حسابداری با مقایسه مبلغ مطلق برای POS
    """
    return ReconciliationRepository.get_accounting_by_date_amount_type_abs(bank_id, transaction_date, amount, transaction_type)

def perform_reconciliation(bank_transaction, accounting_transaction, pos_transaction, transaction_type):
    """
    انجام عملیات مغایرت‌گیری و ثبت نتیجه
    """
    try:
        # به‌روزرسانی وضعیت تراکنش بانکی (اگر موجود باشد)
        if bank_transaction:
            bank_id = bank_transaction.get('id')
            update_bank_transaction_reconciliation_status(bank_id, True)
        else:
            bank_id = None
        
        # به‌روزرسانی وضعیت تراکنش حسابداری
        if accounting_transaction:
            update_accounting_transaction_reconciliation_status(
                accounting_transaction.get('id'), True
            )
        
        # ثبت نتیجه مغایرت‌گیری
        pos_id = pos_transaction.get('id') if pos_transaction else None
        acc_id = accounting_transaction.get('id') if accounting_transaction else None
        
        amount = bank_transaction.get('amount') if bank_transaction else pos_transaction.get('transaction_amount')
        description = f"مغایرت‌گیری {transaction_type} - مبلغ: {amount}"
        
        create_reconciliation_result(
            pos_id=pos_id,
            acc_id=acc_id,
            bank_record_id=bank_id,
            description=description,
            type_matched=transaction_type
        )
        
        logger.info(f"مغایرت‌گیری موفق: Bank ID={bank_id}, Acc ID={acc_id}, POS ID={pos_id}")
        return True
        
    except Exception as e:
        logger.error(f"خطا در انجام مغایرت‌گیری: {str(e)}")
        return False

# تابع update_accounting_transaction_reconciliation_status به ReconciliationRepository منتقل شد
def update_accounting_transaction_reconciliation_status(transaction_id, status):
    """
    به‌روزرسانی وضعیت مغایرت‌گیری تراکنش حسابداری
    """
    return ReconciliationRepository.update_accounting_reconciliation_status(transaction_id, status)
