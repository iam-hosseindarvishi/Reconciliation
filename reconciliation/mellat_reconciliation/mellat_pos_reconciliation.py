# file: reconciliation/mellat_pos_reconciliation.py

import threading
import queue
from tkinter import messagebox
from utils.logger_config import setup_logger
from utils.helpers import get_pos_date_from_bank
from utils.compare_tracking_numbers import compare_tracking_numbers
from database.repositories.accounting import get_transactions_by_date_amount_type
from reconciliation.save_reconciliation_result import success_reconciliation_result, fail_reconciliation_result

logger = setup_logger('reconciliation.mellat_pos_reconciliation')


def reconcile_mellat_pos(pos_transactions, ui_handler, manual_reconciliation_queue):
    """
    Reconciles Mellat Bank POS transactions in a separate thread to prevent UI freezing.

    Args:
        pos_transactions (list): List of POS transactions to reconcile.
        ui_handler: An object to handle UI updates.
        manual_reconciliation_queue (queue.Queue): The queue for manual reconciliation requests.
    """
    thread = threading.Thread(
        target=_reconcile_in_thread,
        args=(pos_transactions, ui_handler, manual_reconciliation_queue)
    )
    thread.start()


def _reconcile_in_thread(pos_transactions, ui_handler, manual_reconciliation_queue):
    """
    The actual reconciliation logic that runs in a separate thread.
    """
    logger.info(f"Starting POS reconciliation for {len(pos_transactions)} transactions.")
    total_transactions = len(pos_transactions)
    
    # Initialize counters for tracking reconciliation results
    successful_reconciliations = 0
    failed_reconciliations = 0
    
    for i, tx in enumerate(pos_transactions):
        try:
            result = _reconcile_single_pos(tx, ui_handler, manual_reconciliation_queue)
            if result:
                successful_reconciliations += 1
            else:
                failed_reconciliations += 1
        except Exception as e:
            logger.error(f"Error processing POS transaction {tx.get('id', 'unknown')}: {e}")
            failed_reconciliations += 1

        # Update progress with thread-safe UI updates
        progress_percentage = (i + 1) / total_transactions * 100
        try:
            # Use after_idle to ensure UI updates are thread-safe
            if hasattr(ui_handler, 'parent'):
                ui_handler.parent.after_idle(lambda p=progress_percentage: ui_handler.update_progress(p))
                ui_handler.parent.after_idle(lambda i=i, t=total_transactions: ui_handler.update_detailed_status(f"مغایرت‌یابی {i + 1} از {t} تراکنش POS انجام شد."))
            else:
                ui_handler.update_progress(progress_percentage)
                ui_handler.update_detailed_status(f"مغایرت‌یابی {i + 1} از {total_transactions} تراکنش POS انجام شد.")
        except Exception as e:
            logger.warning(f"UI update failed: {e}")

    # Final status update
    final_message = f"مغایرت‌یابی POS تکمیل شد. موفق: {successful_reconciliations}, ناموفق: {failed_reconciliations}"
    logger.info(final_message)
    
    try:
        if hasattr(ui_handler, 'parent'):
            ui_handler.parent.after_idle(lambda: ui_handler.update_status(final_message))
        else:
            ui_handler.update_status(final_message)
    except Exception as e:
        logger.warning(f"Final UI update failed: {e}")


def _reconcile_single_pos(bank_record, ui_handler, manual_reconciliation_queue):
    """
    Reconciles a single POS transaction with a more optimized logic.
    Returns True if reconciliation was successful, False otherwise.
    """
    try:
        bank_date = get_pos_date_from_bank(bank_record['transaction_date'])
        bank_amount = bank_record['amount']
        bank_tracking_num = bank_record['extracted_tracking_number']

        matches = get_transactions_by_date_amount_type(bank_record['bank_id'], bank_date, bank_amount, 'Pos')

        def handle_success(accounting_doc):
            success_reconciliation_result(bank_record['id'], accounting_doc['id'], None, 'Exact match', 'Pos')
            logger.info(f"Reconciled POS transaction {bank_record['id']} with accounting doc {accounting_doc['id']}")
            return True

        if matches:
            if len(matches)==1:
                handle_success(matches[0])
                return True
            tracking_matches = [
                match for match in matches
                if compare_tracking_numbers(bank_tracking_num, match['transaction_number'])
            ]

            if len(tracking_matches) == 1:
                handle_success(tracking_matches[0])
                return True
            elif len(tracking_matches) > 1:
                matches = tracking_matches

        if len(matches) == 1:
            handle_success(matches[0])
            return True
        elif len(matches) > 1:
            logger.warning(f"Multiple matches found for POS transaction {bank_record['id']}. Requesting manual reconciliation.")
            # فقط در صورتی که رکورد حسابداری مغایرت‌یابی نشده وجود داشته باشد، دیالوگ را نمایش می‌دهیم
            unreconciled_matches = [match for match in matches if match.get('reconciliation_status', 0) == 0]
            if unreconciled_matches and len(unreconciled_matches) > 0:
                # دریافت وضعیت نمایش مغایرت‌گیری دستی از ماژول ui_state
                from utils import ui_state
                show_manual_reconciliation = ui_state.get_show_manual_reconciliation()
                logger.info(f"Manual reconciliation dialog will be shown: {show_manual_reconciliation}")
                
                if show_manual_reconciliation:
                    result_queue = queue.Queue()
                    manual_reconciliation_queue.put({
                        'bank_record': bank_record,
                        'matches': unreconciled_matches,
                        'result_queue': result_queue,
                        'transaction_type': 'Pos'
                    })
                    selected_match = result_queue.get()  # Wait for the user's choice

                    if selected_match:
                        handle_success(selected_match)
                        return True
                    else:
                        fail_reconciliation_result(bank_record['id'], None, None, 'Manual reconciliation cancelled', 'Pos')
                        return False
                else:
                    logger.info(f"Skipping manual reconciliation dialog as per settings for POS transaction {bank_record['id']}")
                    fail_reconciliation_result(bank_record['id'], None, None, 'Manual reconciliation skipped by settings', 'Pos')
                    return False
            else:
                logger.warning(f"No unreconciled accounting records found for POS transaction {bank_record['id']}")
                fail_reconciliation_result(bank_record['id'], None, None, 'No unreconciled match found', 'Pos')
                return False
        else:
            logger.warning(f"No matching accounting document found for POS transaction {bank_record['id']}.")
            fail_reconciliation_result(bank_record['id'], None, None, 'No match found', 'Pos')
            return False

    except Exception as e:
        logger.error(f"Error reconciling POS transaction {bank_record['id']}: {e}", exc_info=True)
        fail_reconciliation_result(bank_record['id'], None, None, f"Processing error: {str(e)}", 'Pos')
        return False

