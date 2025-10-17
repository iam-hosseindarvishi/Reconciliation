# file: reconciliation/mellat_received_transfer_reconciliation.py

# file: reconciliation/mellat_received_transfer_reconciliation.py

import queue
import threading
import tkinter as tk
from tkinter import messagebox
from utils.logger_config import setup_logger
from utils.constants import TransactionTypes

from utils.compare_tracking_numbers import compare_tracking_numbers
from database.repositories.accounting import get_transactions_by_date_amount_type
from reconciliation.save_reconciliation_result import success_reconciliation_result, fail_reconciliation_result

logger = setup_logger('reconciliation.mellat_received_transfer_reconciliation')

def reconcile_mellat_received_transfer(bank_transactions, ui_handler, manual_reconciliation_queue):
    """
    Reconciles Mellat Bank Received Transfer transactions in a separate thread.

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
    logger.info(f"Starting Received_Transfer reconciliation for {len(bank_transactions)} transactions.")
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
            logger.error(f"Error processing Received Transfer transaction {bank_record.get('id', 'unknown')}: {e}")
            failed_reconciliations += 1

        # Update progress with thread-safe UI updates
        progress_percentage = (i + 1) / total_transactions * 100
        try:
            # Use after_idle to ensure UI updates are thread-safe
            if hasattr(ui_handler, 'parent'):
                ui_handler.parent.after_idle(lambda p=progress_percentage: ui_handler.update_progress(p))
                ui_handler.parent.after_idle(lambda i=i, t=total_transactions: ui_handler.update_detailed_status(f"مغایرت‌یابی {i + 1} از {t} تراکنش انتقال دریافتی انجام شد."))
            else:
                ui_handler.update_progress(progress_percentage)
                ui_handler.update_detailed_status(f"مغایرت‌یابی {i + 1} از {total_transactions} تراکنش انتقال دریافتی انجام شد.")
        except Exception as e:
            logger.warning(f"UI update failed: {e}")

    # Final status update
    final_message = f"مغایرت‌یابی انتقال دریافتی تکمیل شد. موفق: {successful_reconciliations}, ناموفق: {failed_reconciliations}"
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
    Reconciles a single Received_Transfer transaction.
    Returns True if reconciliation was successful, False otherwise.
    """
    try:
        bank_date = bank_record['transaction_date']
        bank_amount = bank_record['amount']
        bank_tracking_num = bank_record['extracted_tracking_number']

        # Step 1: Get all potential matches based on date, amount, and type
        matches = get_transactions_by_date_amount_type(bank_record['bank_id'], bank_date, bank_amount, TransactionTypes.RECEIVED_TRANSFER)

        # Helper function for consistent success handling
        def handle_success(accounting_doc):
            success_reconciliation_result(bank_record['id'], accounting_doc['id'], None, 'Exact match', 'Received_Transfer')
            logger.info(f"Reconciled Bank Transfer {bank_record['id']} with accounting doc {accounting_doc['id']}")
            return True

        # Step 2: Prioritize matching based on tracking number
        if matches:
            tracking_matches = [
                match for match in matches
                if compare_tracking_numbers(bank_tracking_num, match['transaction_number'])
            ]

            if len(tracking_matches) == 1:
                handle_success(tracking_matches[0])
                return True
            elif len(tracking_matches) > 1:
                # Multiple tracking matches still require manual intervention
                matches = tracking_matches

        if len(matches) == 1:
            # Fallback to a single match if no tracking number was available
            handle_success(matches[0])
            return True
        elif len(matches) > 1:
            # Multiple matches, requiring user intervention
            logger.warning(f"Multiple matches found for Bank Transfer {bank_record['id']}. Opening dialog.")
            # فقط در صورتی که رکورد حسابداری مغایرت‌یابی نشده وجود داشته باشد، دیالوگ را نمایش می‌دهیم
            unreconciled_matches = [match for match in matches if match.get('reconciliation_status', 0) == 0]
            if unreconciled_matches and len(unreconciled_matches) > 0:
                # دریافت وضعیت نمایش مغایرت‌گیری دستی از ماژول ui_state
                from utils import ui_state
                show_manual_reconciliation = ui_state.get_show_manual_reconciliation()
                logger.info(f"Manual reconciliation dialog will be shown: {show_manual_reconciliation}")
                
                if show_manual_reconciliation:
                    result_queue = queue.Queue()
                    manual_reconciliation_queue.put((bank_record, unreconciled_matches, result_queue, 'Received_Transfer'))
                    selected_match = result_queue.get()  # Wait for the result from the main thread
                    if selected_match:
                        handle_success(selected_match)
                        return True
                    else:
                        fail_reconciliation_result(bank_record['id'], None, None, 'Manual reconciliation cancelled', 'Received_Transfer')
                        return False
                else:
                    logger.info(f"Skipping manual reconciliation dialog as per settings for Bank Transfer {bank_record['id']}")
                    fail_reconciliation_result(bank_record['id'], None, None, 'Manual reconciliation skipped by settings', 'Received_Transfer')
                    return False
            else:
                logger.warning(f"No unreconciled accounting records found for Bank Transfer {bank_record['id']}")
                fail_reconciliation_result(bank_record['id'], None, None, 'No unreconciled match found', 'Received_Transfer')
                return False
        else:
            # No match found
            logger.warning(f"No matching accounting document found for Bank Transfer {bank_record['id']}.")
            fail_reconciliation_result(bank_record['id'], None, None, 'No match found', 'Received_Transfer')
            return False

    except Exception as e:
        logger.error(f"Error reconciling Bank Transfer {bank_record['id']}: {e}", exc_info=True)
        fail_reconciliation_result(bank_record['id'], None, None, f"Processing error: {str(e)}", 'Received_Transfer')
        return False
