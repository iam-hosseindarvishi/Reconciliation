# file: reconciliation/mellat_reconciliation/mellat_paid_transfer_reconciliation.py

# file: reconciliation/mellat_reconciliation/mellat_paid_transfer_reconciliation.py

import queue
import threading
import tkinter as tk
from tkinter import messagebox
from utils.logger_config import setup_logger

from utils.compare_tracking_numbers import compare_tracking_numbers
from database.accounting_repository import get_transactions_by_date_amount_type, get_transactions_by_date_less_than_amount_type, get_transactions_by_date_type, get_transactions_by_amount_tracking, create_accounting_transaction, update_accounting_transaction_reconciliation_status
from reconciliation.save_reconciliation_result import success_reconciliation_result, fail_reconciliation_result

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
    for i, bank_record in enumerate(bank_transactions):
        _reconcile_single_transfer(bank_record, ui_handler, manual_reconciliation_queue)

        # Update UI progress
        progress_percentage = (i + 1) / total_transactions * 100
        ui_handler.update_progress(progress_percentage)
        ui_handler.update_detailed_status(f"Reconciled {i + 1} of {total_transactions} transfer transactions.")

    logger.info("Finished Paid_Transfer reconciliation.")
    ui_handler.update_status("Finished Paid_Transfer reconciliation.")


def _reconcile_single_transfer(bank_record, ui_handler, manual_reconciliation_queue):
    """
    Reconciles a single Paid_Transfer transaction.
    """
    try:
        bank_date = bank_record['transaction_date']
        bank_amount = bank_record['amount']
        bank_id = bank_record['bank_id']
        transaction_type = 'Paid Transfer'

        # 1. ابتدا رکوردهای همسان در جدول حسابداری جستجو می‌شود
        exact_matches = get_transactions_by_date_amount_type(bank_id, bank_date, bank_amount, transaction_type)
        if len(exact_matches) == 1:
            # اگر یک رکورد با مبلغ دقیقاً یکسان پیدا شد، مغایرت‌گیری انجام می‌شود
            success_reconciliation_result(bank_record['id'], exact_matches[0]['id'], None, 'Exact match', transaction_type)
            logger.info(f"Reconciled Bank Transfer {bank_record['id']} with accounting doc {exact_matches[0]['id']}")
            return

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
                        return
            
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
            result = None

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
        else:
            fail_reconciliation_result(bank_record['id'], None, None, 'No match found', transaction_type)
            logger.warning(f"Manual reconciliation failed for Bank Transfer {bank_record['id']}. No match selected.")

    except Exception as e:
        logger.error(f"Error reconciling Bank Transfer {bank_record['id']}: {e}", exc_info=True)
        fail_reconciliation_result(bank_record['id'], None, None, f"Processing error: {str(e)}", transaction_type)
   