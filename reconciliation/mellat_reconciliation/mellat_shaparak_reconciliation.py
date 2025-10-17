# file: reconciliation/mellat_reconciliation/mellat_shaparak_reconciliation.py

import threading
import queue
from datetime import datetime, timedelta
from tkinter import messagebox
from utils.logger_config import setup_logger
from utils.compare_tracking_numbers import compare_tracking_numbers
from database.init_db import create_connection
from reconciliation.save_reconciliation_result import success_reconciliation_result, fail_reconciliation_result

logger = setup_logger('reconciliation.mellat_shaparak_reconciliation')


def reconcile_mellat_shaparak(shaparak_transactions, ui_handler, manual_reconciliation_queue):
    """
    Reconciles Mellat Bank Shaparak transactions in a separate thread to prevent UI freezing.
    
    Shaparak transactions are linked to pos_transaction records and need special handling
    where the transaction date is one day before the bank record date.

    Args:
        shaparak_transactions (list): List of Shaparak transactions to reconcile.
        ui_handler: An object to handle UI updates.
        manual_reconciliation_queue (queue.Queue): The queue for manual reconciliation requests.
    """
    thread = threading.Thread(
        target=_reconcile_in_thread,
        args=(shaparak_transactions, ui_handler, manual_reconciliation_queue)
    )
    thread.start()


def _reconcile_in_thread(shaparak_transactions, ui_handler, manual_reconciliation_queue):
    """
    The actual reconciliation logic that runs in a separate thread.
    """
    logger.info(f"Starting Shaparak reconciliation for {len(shaparak_transactions)} transactions.")
    total_transactions = len(shaparak_transactions)
    
    # Initialize counters for tracking reconciliation results
    successful_reconciliations = 0
    failed_reconciliations = 0
    
    for i, tx in enumerate(shaparak_transactions):
        try:
            result = _reconcile_single_shaparak(tx, ui_handler, manual_reconciliation_queue)
            if result:
                successful_reconciliations += 1
            else:
                failed_reconciliations += 1
        except Exception as e:
            logger.error(f"Error processing Shaparak transaction {tx.get('id', 'unknown')}: {e}")
            failed_reconciliations += 1

        # Update progress with thread-safe UI updates
        progress_percentage = (i + 1) / total_transactions * 100
        try:
            # Use after_idle to ensure UI updates are thread-safe
            if hasattr(ui_handler, 'parent'):
                ui_handler.parent.after_idle(lambda p=progress_percentage: ui_handler.update_progress(p))
                ui_handler.parent.after_idle(lambda i=i, t=total_transactions: ui_handler.update_detailed_status(f"مغایرت‌یابی {i + 1} از {t} تراکنش شاپرک انجام شد."))
            else:
                ui_handler.update_progress(progress_percentage)
                ui_handler.update_detailed_status(f"مغایرت‌یابی {i + 1} از {total_transactions} تراکنش شاپرک انجام شد.")
        except Exception as e:
            logger.warning(f"UI update failed: {e}")

    # Final status update
    final_message = f"مغایرت‌یابی شاپرک تکمیل شد. موفق: {successful_reconciliations}, ناموفق: {failed_reconciliations}"
    logger.info(final_message)
    
    try:
        if hasattr(ui_handler, 'parent'):
            ui_handler.parent.after_idle(lambda: ui_handler.update_status(final_message))
        else:
            ui_handler.update_status(final_message)
    except Exception as e:
        logger.warning(f"Final UI update failed: {e}")


def _reconcile_single_shaparak(bank_record, ui_handler, manual_reconciliation_queue):
    """
    مغایرت‌یابی یک تراکنش Shaparak با الگوریتم مشابه POS کشاورزی
    
    روند کار:
    1. کسر یک روز از تاریخ بانک (تاریخ POS)
    2. دریافت تمام رکوردهای POS بانک ملت (bank_id=1) در آن تاریخ
    3. برای هر رکورد POS, جستجوی رکورد حسابداری مطابق (مبلغ، تاریخ، شماره پیگیری)
    4. مغایرت‌یابی رکوردهای POS با حسابداری
    5. علامت‌گذاری رکورد بانک به عنوان مغایرت‌یابی شده
    """
    try:
        # مرحله 1: محاسبه تاریخ POS (یک روز قبل از تاریخ بانک)
        bank_date_str = bank_record['transaction_date']
        bank_amount = bank_record['amount']
        bank_id = bank_record['bank_id']
        
        pos_date = calculate_pos_date(bank_date_str)
        if not pos_date:
            logger.error(f"خطا در محاسبه تاریخ POS برای رکورد بانک {bank_record['id']}")
            fail_reconciliation_result(bank_record['id'], None, None, 'Invalid transaction date', 'Shaparak')
            return False
            
        logger.info(f"تاریخ POS محاسبه شد: {pos_date} (تاریخ بانک: {bank_date_str})")
        
        # مرحله 2: دریافت تمام تراکنش‌های POS بانک ملت در آن تاریخ
        pos_transactions = get_mellat_pos_transactions_by_date(pos_date, bank_id)
        
        if not pos_transactions:
            logger.warning(f"هیچ تراکنش POS یافت نشد برای Shaparak {bank_record['id']} در تاریخ {pos_date}")
            fail_reconciliation_result(bank_record['id'], None, None, 'No POS transactions found', 'Shaparak')
            return False
        
        logger.info(f"{len(pos_transactions)} تراکنش POS یافت شد برای مغایرت‌یابی Shaparak")
        
        # مرحله 3 و 4: برای هر رکورد POS, مغایرت‌یابی با حسابداری
        reconciled_pos_count = 0
        reconciled_accounting_ids = []
        
        for pos_record in pos_transactions:
            pos_amount = pos_record.get('transaction_amount', 0)
            pos_tracking = pos_record.get('tracking_number', '')
            
            # جستجوی رکورد حسابداری بر اساس مبلغ و تاریخ
            accounting_matches = get_accounting_transactions_for_pos(bank_id, pos_date, pos_amount)
            
            if not accounting_matches:
                logger.debug(f"رکورد حسابداری برای POS {pos_record['id']} یافت نشد")
                continue
            
            # انتخاب بهترین رکورد حسابداری
            best_accounting_match = None
            
            if len(accounting_matches) == 1:
                best_accounting_match = accounting_matches[0]
            else:
                # چند رکورد یافت شد - مقایسه شماره پیگیری
                for acc_match in accounting_matches:
                    acc_tracking = acc_match.get('transaction_number', '')
                    if pos_tracking and acc_tracking and compare_tracking_numbers(pos_tracking, acc_tracking):
                        best_accounting_match = acc_match
                        break
                
                # اگر با شماره پیگیری پیدا نشد، اولین رکورد را انتخاب کن
                if not best_accounting_match:
                    best_accounting_match = accounting_matches[0]
            
            if best_accounting_match:
                # مغایرت‌یابی POS با حسابداری
                if reconcile_pos_with_accounting(pos_record, best_accounting_match):
                    reconciled_pos_count += 1
                    reconciled_accounting_ids.append(best_accounting_match['id'])
                    logger.info(f"POS {pos_record['id']} با حسابداری {best_accounting_match['id']} مغایرت‌یابی شد")
        
        # مرحله 5: علامت‌گذاری رکورد بانک به عنوان مغایرت‌یابی شده
        if reconciled_pos_count > 0:
            from database.bank_transaction_repository import update_bank_transaction_reconciliation_status
            update_bank_transaction_reconciliation_status(bank_record['id'], 1)
            
            # ثبت نتیجه مغایرت‌یابی
            description = f"شاپرک - {reconciled_pos_count} تراکنش POS مغایرت‌یابی شد"
            # ثبت نتیجه برای اولین رکورد حسابداری
            if reconciled_accounting_ids:
                success_reconciliation_result(
                    bank_record['id'],
                    reconciled_accounting_ids[0],
                    None,
                    description,
                    'Shaparak'
                )
            
            logger.info(f"مغایرت‌یابی Shaparak موفق: بانک={bank_record['id']}, POS={reconciled_pos_count}")
            return True
        else:
            logger.warning(f"هیچ رکورد POS مغایرت‌یابی نشد برای Shaparak {bank_record['id']}")
            fail_reconciliation_result(bank_record['id'], None, None, 'No POS reconciled', 'Shaparak')
            return False
            
    except Exception as e:
        logger.error(f"خطا در مغایرت‌یابی Shaparak {bank_record['id']}: {e}", exc_info=True)
        fail_reconciliation_result(bank_record['id'], None, None, f"Processing error: {str(e)}", 'Shaparak')
        return False


def calculate_pos_date(bank_date_str):
    """
    Calculate POS date (one day before bank transaction date)
    
    Args:
        bank_date_str: Bank transaction date in YYYY-MM-DD format
        
    Returns:
        str: POS date in YYYY-MM-DD format or None if error
    """
    try:
        # Parse bank date
        bank_date = datetime.strptime(bank_date_str, '%Y-%m-%d')
        # Subtract one day
        pos_date = bank_date - timedelta(days=1)
        return pos_date.strftime('%Y-%m-%d')
    except Exception as e:
        logger.error(f"Error calculating POS date from {bank_date_str}: {str(e)}")
        return None


def get_mellat_pos_transactions_by_date(pos_date, bank_id):
    """
    دریافت تمام تراکنش‌های POS بانک ملت در تاریخ مشخص
    
    Args:
        pos_date: تاریخ مورد نظر
        bank_id: شناسه بانک (باید ملت باشد - ID=1)
        
    Returns:
        list: لیست تراکنش‌های POS مغایرت‌یابی نشده
    """
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # جستجوی تمام تراکنش‌های POS بانک ملت در آن تاریخ
        cursor.execute("""
            SELECT * FROM PosTransactions 
            WHERE transaction_date = ? 
            AND bank_id = ?
            AND is_reconciled = 0
        """, (pos_date, bank_id))
        
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        logger.info(f"{len(result)} تراکنش POS یافت شد برای تاریخ {pos_date} و بانک {bank_id}")
        return result
        
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌های POS: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()


def get_accounting_transactions_for_pos(bank_id, transaction_date, amount):
    """
    جستجوی رکوردهای حسابداری برای POS
    
    Args:
        bank_id: شناسه بانک
        transaction_date: تاریخ تراکنش
        amount: مبلغ تراکنش
        
    Returns:
        list: لیست رکوردهای حسابداری مغایرت‌یابی نشده
    """
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # جستجوی رکوردهای حسابداری POS با مبلغ و تاریخ مطابق
        cursor.execute("""
            SELECT * FROM AccountingTransactions 
            WHERE bank_id = ? 
            AND due_date = ?
            AND ABS(transaction_amount) = ?
            AND (transaction_type = 'Pos' OR transaction_type = 'Pos / Received Transfer' 
                 OR transaction_type = 'Received_Transfer')
            AND is_reconciled = 0
        """, (bank_id, transaction_date, abs(float(amount))))
        
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        logger.info(f"{len(result)} رکورد حسابداری POS یافت شد")
        return result
        
    except Exception as e:
        logger.error(f"خطا در جستجوی حسابداری POS: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()


def reconcile_pos_with_accounting(pos_record, accounting_record):
    """
    مغایرت‌یابی یک رکورد POS با رکورد حسابداری
    
    Args:
        pos_record: رکورد POS
        accounting_record: رکورد حسابداری
        
    Returns:
        bool: True اگر موفق باشد
    """
    try:
        from database.repositories.accounting.transaction_crud import update_accounting_transaction_reconciliation_status
        from database.pos_transactions_repository import update_reconciliation_status
        
        # علامت‌گذاری رکورد حسابداری به عنوان مغایرت‌یابی شده
        update_accounting_transaction_reconciliation_status(accounting_record['id'], 1)
        
        # علامت‌گذاری رکورد POS به عنوان مغایرت‌یابی شده
        update_reconciliation_status(pos_record['id'], 1)
        
        logger.info(f"POS {pos_record['id']} و حسابداری {accounting_record['id']} مغایرت‌یابی شدند")
        return True
        
    except Exception as e:
        logger.error(f"خطا در مغایرت‌یابی POS با حسابداری: {str(e)}")
        return False


