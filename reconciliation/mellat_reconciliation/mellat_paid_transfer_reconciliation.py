# file: reconciliation/mellat_reconciliation/mellat_paid_transfer_reconciliation.py

# file: reconciliation/mellat_reconciliation/mellat_paid_transfer_reconciliation.py

import queue
import threading
import tkinter as tk
from tkinter import messagebox
from utils.logger_config import setup_logger
from utils.constants import TransactionTypes

from utils.compare_tracking_numbers import compare_tracking_numbers
from database.repositories.accounting import (
    get_transactions_by_date_amount_type,
    get_transactions_by_date_less_than_amount_type,
    get_transactions_by_date_type,
    get_transactions_by_amount_tracking,
    create_accounting_transaction,
    update_accounting_transaction_reconciliation_status
)
from reconciliation.save_reconciliation_result import success_reconciliation_result, fail_reconciliation_result
from utils.compare_tracking_numbers import compare_tracking_numbers

logger = setup_logger('reconciliation.mellat_paid_transfer_reconciliation')

def reconcile_mellat_paid_transfer(bank_transactions, ui_handler, manual_reconciliation_queue):
    """
    Reconciles Mellat Bank Paid Transfer transactions in a separate thread.

    Args:
        bank_transactions (list): List of bank transfer transactions to reconcile.
        ui_handler: An object to handle UI updates.
        manual_reconciliation_queue (queue.Queue): The queue for manual reconciliation requests.
    """
    thread = threading.Thread(
        target=_reconcile_in_thread,
        args=(bank_transactions, ui_handler, manual_reconciliation_queue)
    )
    thread.start()


def _reconcile_in_thread(bank_transactions, ui_handler, manual_reconciliation_queue):
    """
    The actual reconciliation logic that runs in a separate thread.
    """
    logger.info(f"Starting Paid_Transfer reconciliation for {len(bank_transactions)} transactions.")
    total_transactions = len(bank_transactions)
    
    # Initialize counters for tracking reconciliation results
    successful_reconciliations = 0
    failed_reconciliations = 0
    
    for i, bank_record in enumerate(bank_transactions):
        try:
            result = _reconcile_single_transfer(bank_record, ui_handler, manual_reconciliation_queue)
            if result:
                successful_reconciliations += 1
            else:
                failed_reconciliations += 1
        except Exception as e:
            logger.error(f"Error processing Paid Transfer transaction {bank_record.get('id', 'unknown')}: {e}")
            failed_reconciliations += 1

        # Update progress with thread-safe UI updates
        progress_percentage = (i + 1) / total_transactions * 100
        try:
            # Use after_idle to ensure UI updates are thread-safe
            if hasattr(ui_handler, 'parent'):
                ui_handler.parent.after_idle(lambda p=progress_percentage: ui_handler.update_progress(p))
                ui_handler.parent.after_idle(lambda i=i, t=total_transactions: ui_handler.update_detailed_status(f"مغایرت‌یابی {i + 1} از {t} تراکنش انتقال پرداختی انجام شد."))
            else:
                ui_handler.update_progress(progress_percentage)
                ui_handler.update_detailed_status(f"مغایرت‌یابی {i + 1} از {total_transactions} تراکنش انتقال پرداختی انجام شد.")
        except Exception as e:
            logger.warning(f"UI update failed: {e}")

    # Final status update
    final_message = f"مغایرت‌یابی انتقال پرداختی تکمیل شد. موفق: {successful_reconciliations}, ناموفق: {failed_reconciliations}"
    logger.info(final_message)
    
    try:
        if hasattr(ui_handler, 'parent'):
            ui_handler.parent.after_idle(lambda: ui_handler.update_status(final_message))
        else:
            ui_handler.update_status(final_message)
    except Exception as e:
        logger.warning(f"Final UI update failed: {e}")


def _reconcile_single_transfer(bank_record, ui_handler, manual_reconciliation_queue):
    """
    Reconciles a single Paid_Transfer transaction.
    Returns True if reconciliation was successful, False otherwise.
    """
    try:
        bank_date = bank_record['transaction_date']
        bank_amount = bank_record['amount']
        bank_id = bank_record['bank_id']
        transaction_type = TransactionTypes.PAID_TRANSFER

        # ۰. بررسی ویژه برای تراکنش‌های Paid_Transfer با کلمه "حقوق" و نام واریز کننده
        if ('حقوق' in bank_record.get('description', '') and 
            bank_record.get('depositor_name') and 
            bank_record.get('depositor_name').strip()):
            
            salary_result = _handle_salary_payment_reconciliation(
                bank_record, ui_handler, manual_reconciliation_queue, bank_id, bank_date, bank_amount, transaction_type
            )
            if salary_result is not None:
                return salary_result
        
        # ۱. ابتدا رکوردهای همسان در جدول حسابداری جستجو می‌شود
        exact_matches = get_transactions_by_date_amount_type(bank_id, bank_date, bank_amount, transaction_type)
        if len(exact_matches) == 1:
            # اگر یک رکورد با مبلغ دقیقاً یکسان پیدا شد، مغایرت‌گیری انجام می‌شود
            success_reconciliation_result(bank_record['id'], exact_matches[0]['id'], None, 'Exact match', transaction_type)
            logger.info(f"Reconciled Bank Transfer {bank_record['id']} with accounting doc {exact_matches[0]['id']}")
            return True

        # 2. اگر رکورد دقیقاً مشابه پیدا نشد، تمام رکوردهای حسابداری در تاریخ مورد نظر را بررسی می‌کنیم
        all_accounting_records = get_transactions_by_date_type(bank_id, bank_date, transaction_type)
        
        # اگر تراکنش‌های بازیافتی 0 بود، بر اساس مبلغ و شماره پیگیری در حسابداری جستجو کن
        if not all_accounting_records or len(all_accounting_records) == 0:
            bank_tracking_number = bank_record.get('extracted_tracking_number', '')
            if bank_tracking_number:
                all_accounting_records = get_transactions_by_amount_tracking(bank_id, bank_amount, bank_tracking_number, transaction_type)
                logger.info(f"Searching by amount and tracking number due to no date matches. Found {len(all_accounting_records)} potential matches.")
        
        if all_accounting_records and len(all_accounting_records) > 0:
            # بررسی شماره پیگیری
            bank_tracking_number = bank_record.get('extracted_tracking_number', '')
            
            for acc_record in all_accounting_records:
                acc_tracking_number = acc_record.get('transaction_number', '')
                
                # مقایسه شماره پیگیری با استفاده از تابع compare_tracking_numbers
                if acc_tracking_number and bank_tracking_number:
                    # تبدیل به رشته برای اطمینان
                    bank_tracking_str = str(bank_tracking_number)
                    acc_tracking_str = str(acc_tracking_number)
                    
                    # استفاده از تابع compare_tracking_numbers برای مقایسه شماره‌های پیگیری
                    if compare_tracking_numbers(bank_tracking_str, acc_tracking_str) and float(acc_record['transaction_amount']) < float(bank_amount):
                        # کارمزد را محاسبه می‌کنیم
                        fee_amount = float(bank_amount) - float(acc_record['transaction_amount'])
                        
                        # کارمزد به عنوان یک تراکنش جداگانه در جدول بانک ثبت می‌شود، نه در جدول حسابداری
                        from database.bank_transaction_repository import create_bank_transaction
                        
                        # ایجاد تراکنش کارمزد در جدول بانک
                        fee_transaction_data = {
                            'bank_id': bank_id,
                            'transaction_date': bank_record['transaction_date'],
                            'transaction_time': bank_record['transaction_time'],
                            'amount': fee_amount,
                            'description': f"کارمزد برای تراکنش {acc_record['transaction_number']} - شماره پیگیری بانک: {bank_tracking_number}",
                            'reference_number': bank_record['reference_number'],
                            'extracted_terminal_id': bank_record['extracted_terminal_id'],
                            'extracted_tracking_number': bank_record['extracted_tracking_number'],
                            'transaction_type': 'bank_fee',
                            'source_card_number': bank_record['source_card_number'],
                            'is_reconciled': 1
                        }
                        
                        create_bank_transaction(fee_transaction_data)
                        
                        # به‌روزرسانی مبلغ رکورد بانک (کارمزد از آن کسر شده)
                        bank_record['amount'] = acc_record['transaction_amount'] 
                        
                        # ذخیره رکورد بانک پس از بروزرسانی مبلغ
                        from database.bank_transaction_repository import update_bank_transaction
                        update_bank_transaction(bank_record['id'], {'amount': acc_record['transaction_amount']})
                        
                        # تنظیم فیلد is_reconciled برای هر دو رکورد بانک و حسابداری
                        update_bank_transaction(bank_record['id'], {'is_reconciled': 1})
                        update_accounting_transaction_reconciliation_status(acc_record['id'], 1)
                        
                        # ثبت نتیجه مغایرت‌گیری
                        success_reconciliation_result(bank_record['id'], acc_record['id'], None, 
                                                    f'Automatic fee reconciliation with tracking number match. Fee: {fee_amount}', 
                                                    transaction_type)
                        logger.info(f"Automatically reconciled Bank Transfer {bank_record['id']} with tracking number match. Fee: {fee_amount}")
                        return True
            
        # روش قبلی برای مغایرت‌گیری با کارمزد ثابت حذف شد

        # 3. مغایرت‌گیری دستی
        potential_matches = get_transactions_by_date_less_than_amount_type(bank_id, bank_date, bank_amount, transaction_type)
        
        # فقط در صورتی که رکورد حسابداری مغایرت‌یابی نشده وجود داشته باشد، دیالوگ را نمایش می‌دهیم
        if potential_matches and len(potential_matches) > 0:
            # دریافت وضعیت نمایش مغایرت‌گیری دستی از ماژول ui_state
            from utils import ui_state
            show_manual_reconciliation = ui_state.get_show_manual_reconciliation()
            logger.info(f"Manual reconciliation dialog will be shown: {show_manual_reconciliation}")
            
            if show_manual_reconciliation:
                result_queue = queue.Queue()
                manual_reconciliation_queue.put((bank_record, potential_matches, result_queue, 'Paid_Transfer'))
                result = result_queue.get()  # Wait for the result from the main thread
            else:
                logger.info(f"Skipping manual reconciliation dialog as per settings for Bank Transfer {bank_record['id']}")
                result = None
        else:
            # در تاریخ رکورد بانک، رکوردی در حسابداری موجود نیست
            logger.warning(f"No unreconciled accounting records found for Bank Transfer {bank_record['id']}")
            # این رکورد بانک را به عنوان مغایرت در جدول result ثبت می‌کنیم
            fail_reconciliation_result(bank_record['id'], None, None, 'No accounting records found on this date', transaction_type)
            return False

        if result:
            notes = 'Manual reconciliation'
            
            # اگر کارمزد جدا شده باشد
            if 'fee_amount' in bank_record and bank_record['fee_amount'] > 0:
                fee = bank_record['fee_amount']
                
                # کارمزد به عنوان یک تراکنش جداگانه در جدول بانک ثبت می‌شود، نه در جدول حسابداری
                from database.bank_transaction_repository import create_bank_transaction
                
                # ایجاد تراکنش کارمزد در جدول بانک
                fee_transaction_data = {
                    'bank_id': bank_record['bank_id'],
                    'transaction_date': bank_record['transaction_date'],
                    'transaction_time': bank_record['transaction_time'],
                    'amount': fee,
                    'description': f"کارمزد برای تراکنش دستی - شماره پیگیری بانک: {bank_record['extracted_tracking_number']}",
                    'reference_number': bank_record['reference_number'],
                    'extracted_terminal_id': bank_record['extracted_terminal_id'],
                    'extracted_tracking_number': bank_record['extracted_tracking_number'],
                    'transaction_type': 'bank_fee',
                    'source_card_number': bank_record['source_card_number'],
                    'is_reconciled': 1
                }
                
                create_bank_transaction(fee_transaction_data)
                
                notes = f'Manual reconciliation with fee: {fee}'
                logger.info(f"Fee of {fee} recorded for Bank Transfer {bank_record['id']}")
            
            # ثبت نتیجه مغایرت‌گیری
            success_reconciliation_result(bank_record['id'], result['id'], None, notes, transaction_type)
            logger.info(f"Manually reconciled Bank Transfer {bank_record['id']} with accounting doc {result['id']}")
            return True
        else:
            fail_reconciliation_result(bank_record['id'], None, None, 'No match found', transaction_type)
            logger.warning(f"Manual reconciliation failed for Bank Transfer {bank_record['id']}. No match selected.")
            return False

    except Exception as e:
        logger.error(f"Error reconciling Bank Transfer {bank_record['id']}: {e}", exc_info=True)
        fail_reconciliation_result(bank_record['id'], None, None, f"Processing error: {str(e)}", transaction_type)
        return False


def _handle_salary_payment_reconciliation(bank_record, ui_handler, manual_reconciliation_queue, 
                                        bank_id, bank_date, bank_amount, transaction_type):
    """
    هندل مغایرت‌یابی مخصوص پرداخت حقوق بر اساس نام واریز کننده
    
    Returns:
        True: اگر مغایرت‌یابی موفق بود
        False: اگر مغایرت‌یابی ناموفق بود
        None: اگر نیاز به ادامه روند عادی است
    """
    try:
        depositor_name = bank_record.get('depositor_name', '').strip()
        logger.info(f"بررسی پرداخت حقوق برای نام واریز کننده: {depositor_name}")
        
        # جستجوی رکوردهای حسابداری بر اساس نام مشتری و تاریخ
        # استفاده از ماژول جدید
        from database.repositories.accounting import search_transactions_by_customer_name
        
        # استفاده از تابع جستجوی جدید
        try:
            accounting_matches = search_transactions_by_customer_name(
                bank_id, depositor_name, transaction_type
            )
            # فیلتر کردن بر اساس تاریخ
            accounting_matches = [
                match for match in accounting_matches
                if match.get('due_date') == bank_date
            ]
        except Exception as e:
            # اگر تابع موجود نیست، از تابع کلی استفاده کنیم
            logger.warning(f"خطا در استفاده از تابع جستجو: {str(e)}")
            accounting_matches = _search_accounting_by_customer_name(bank_id, depositor_name, bank_date, transaction_type)
        
        if not accounting_matches:
            logger.info(f"هیچ رکورد حسابداری برای نام {depositor_name} و تاریخ {bank_date} یافت نشد")
            return None  # ادامه روند عادی
        
        # فیلتر کردن رکوردهایی که مبلغشان کمتر از مبلغ بانک است
        smaller_amount_matches = [
            match for match in accounting_matches
            if float(match.get('transaction_amount', 0)) < float(bank_amount)
        ]
        
        if not smaller_amount_matches:
            logger.info(f"هیچ رکورد حسابداری با مبلغ کمتر از {bank_amount} یافت نشد")
            return None  # ادامه روند عادی
        
        # اگر یک رکورد پیدا شد، مستقیم مغایرت‌یابی کنیم
        if len(smaller_amount_matches) == 1:
            return _process_single_salary_match(
                bank_record, smaller_amount_matches[0], bank_amount, transaction_type
            )
        
        # اگر بیش از یک رکورد پیدا شد، بر اساس شماره پیگیری فیلتر کنیم
        elif len(smaller_amount_matches) > 1:
            tracking_matches = _filter_by_tracking_number(
                bank_record, smaller_amount_matches
            )
            
            if len(tracking_matches) == 1:
                return _process_single_salary_match(
                    bank_record, tracking_matches[0], bank_amount, transaction_type
                )
            else:
                logger.warning(f"بیش از یک رکورح مطابق پیدا شد: {len(tracking_matches)}")
                return None  # ادامه روند عادی
        
        return None  # ادامه روند عادی
        
    except Exception as e:
        logger.error(f"خطا در مغایرت‌یابی پرداخت حقوق: {str(e)}")
        return None


def _search_accounting_by_customer_name(bank_id, customer_name, transaction_date, transaction_type):
    """جستجوی دستی رکوردهای حسابداری بر اساس نام مشتری"""
    from database.init_db import create_connection
    
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # جستجوی رکوردهای حسابداری بر اساس نام مشتری
        cursor.execute("""
            SELECT * FROM AccountingTransactions 
            WHERE bank_id = ? 
            AND customer_name LIKE ? 
            AND due_date = ?
            AND transaction_type = ?
            AND is_reconciled = 0
        """, (bank_id, f"%{customer_name}%", transaction_date, transaction_type))
        
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        logger.info(f"یافت شد {len(result)} رکورد حسابداری با نام {customer_name}")
        return result
        
    except Exception as e:
        logger.error(f"خطا در جستجوی رکوردهای حسابداری: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()


def _filter_by_tracking_number(bank_record, accounting_matches):
    """فیلتر کردن رکوردها بر اساس شماره پیگیری"""
    bank_tracking = bank_record.get('extracted_tracking_number', '')
    
    if not bank_tracking:
        logger.warning("شماره پیگیری بانک خالی است")
        return accounting_matches
    
    matching_records = []
    for acc_record in accounting_matches:
        acc_tracking = acc_record.get('transaction_number', '')
        
        if acc_tracking and _compare_tracking_digits(bank_tracking, acc_tracking):
            matching_records.append(acc_record)
    
    logger.info(f"بعد از فیلتر شماره پیگیری: {len(matching_records)} رکورد")
    return matching_records


def _compare_tracking_digits(bank_tracking, acc_tracking):
    """مقایسه رقم‌های انتهایی شماره‌های پیگیری"""
    try:
        # حذف فضاهای خالی و کاراکترهای غیرعددی
        bank_digits = ''.join(filter(str.isdigit, str(bank_tracking)))
        acc_digits = ''.join(filter(str.isdigit, str(acc_tracking)))
        
        # طول رقم‌های حسابداری
        acc_length = len(acc_digits)
        
        if acc_length == 0 or len(bank_digits) < acc_length:
            return False
        
        # مقایسه آخرین رقم‌ها
        return bank_digits[-acc_length:] == acc_digits
        
    except Exception as e:
        logger.warning(f"خطا در مقایسه شماره‌های پیگیری: {str(e)}")
        return False


def _process_single_salary_match(bank_record, accounting_record, bank_amount, transaction_type):
    """پردازش مغایرت‌یابی یک رکورد حقوق"""
    try:
        accounting_amount = float(accounting_record.get('transaction_amount', 0))
        fee_amount = float(bank_amount) - accounting_amount
        
        logger.info(f"پردازش مغایرت‌یابی حقوق: مبلغ بانک={bank_amount}, مبلغ حسابداری={accounting_amount}, کارمزد={fee_amount}")
        
        # ایجاد رکورد کارمزد جدید
        from database.bank_transaction_repository import create_bank_transaction
        
        fee_transaction_data = {
            'bank_id': bank_record['bank_id'],
            'transaction_date': bank_record['transaction_date'],
            'transaction_time': bank_record.get('transaction_time'),
            'amount': fee_amount,
            'description': f"کارمزد برای رکورد شماره {bank_record['id']} بانک - حقوق {bank_record.get('depositor_name', '')}",
            'reference_number': bank_record.get('reference_number'),
            'extracted_terminal_id': bank_record.get('extracted_terminal_id'),
            'extracted_tracking_number': bank_record.get('extracted_tracking_number'),
            'transaction_type': 'bank_fee',
            'source_card_number': bank_record.get('source_card_number'),
            'depositor_name': bank_record.get('depositor_name'),
            'is_reconciled': 0  # کارمزد مغایرت‌یابی نمی‌شود
        }
        
        create_bank_transaction(fee_transaction_data)
        
        # به‌روزرسانی مبلغ رکورد بانک اصلی
        from database.bank_transaction_repository import update_bank_transaction
        update_bank_transaction(bank_record['id'], {'amount': accounting_amount})
        
        # علامت‌گذاری هر دو رکورد به عنوان مغایرت‌یابی شده
        from database.bank_transaction_repository import update_bank_transaction_reconciliation_status
        from database.repositories.accounting import update_accounting_transaction_reconciliation_status
        
        update_bank_transaction_reconciliation_status(bank_record['id'], 1)
        update_accounting_transaction_reconciliation_status(accounting_record['id'], 1)
        
        # ثبت نتیجه مغایرت‌یابی
        success_reconciliation_result(
            bank_record['id'], 
            accounting_record['id'], 
            None, 
            f'مغایرت‌یابی خودکار حقوق با کارمزد {fee_amount} - {bank_record.get("depositor_name", "")}', 
            transaction_type
        )
        
        logger.info(f"مغایرت‌یابی خودکار حقوق برای رکورد {bank_record['id']} با کارمزد {fee_amount} موفق بود")
        return True
        
    except Exception as e:
        logger.error(f"خطا در پردازش مغایرت‌یابی حقوق: {str(e)}")
        return False
   