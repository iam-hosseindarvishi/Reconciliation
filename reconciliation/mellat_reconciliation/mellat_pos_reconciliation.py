# file: reconciliation/mellat_pos_reconciliation.py

import threading
import queue
from tkinter import messagebox
from utils.logger_config import setup_logger
from utils.helpers import get_pos_date_from_bank
from utils.compare_tracking_numbers import compare_tracking_numbers
from database.accounting_repository import get_transactions_by_date_amount_type
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
    for i, tx in enumerate(pos_transactions):
        _reconcile_single_pos(tx, ui_handler, manual_reconciliation_queue)

        progress_percentage = (i + 1) / total_transactions * 100
        ui_handler.update_progress(progress_percentage)
        ui_handler.update_detailed_status(f"Reconciled {i + 1} of {total_transactions} POS transactions.")

    logger.info("Finished POS reconciliation.")
    ui_handler.update_status("Finished POS reconciliation.")


def _reconcile_single_pos(bank_record, ui_handler, manual_reconciliation_queue):
    """
    Reconciles a single POS transaction with a more optimized logic.
    """
    try:
        bank_date = get_pos_date_from_bank(bank_record['transaction_date'])
        bank_amount = bank_record['amount']
        bank_tracking_num = bank_record['extracted_tracking_number']

        matches = get_transactions_by_date_amount_type(bank_record['bank_id'], bank_date, bank_amount, 'Pos')

        def handle_success(accounting_doc):
            success_reconciliation_result(None, accounting_doc['id'], bank_record['id'], 'Exact match', 'Pos')
            logger.info(f"Reconciled POS transaction {bank_record['id']} with accounting doc {accounting_doc['id']}")

        if matches:
            tracking_matches = [
                match for match in matches
                if compare_tracking_numbers(bank_tracking_num, match['transaction_number'])
            ]

            if len(tracking_matches) == 1:
                handle_success(tracking_matches[0])
                return
            elif len(tracking_matches) > 1:
                matches = tracking_matches

        if len(matches) == 1:
            handle_success(matches[0])
        elif len(matches) > 1:
            logger.warning(f"Multiple matches found for POS transaction {bank_record['id']}. Requesting manual reconciliation.")
            result_queue = queue.Queue()
            manual_reconciliation_queue.put({
                'bank_record': bank_record,
                'matches': matches,
                'result_queue': result_queue,
                'transaction_type': 'Pos'
            })
            selected_match = result_queue.get()  # Wait for the user's choice

            if selected_match:
                handle_success(selected_match)
            else:
                fail_reconciliation_result(bank_record['id'], None, None, 'Manual reconciliation cancelled', 'Pos')
        else:
            logger.warning(f"No matching accounting document found for POS transaction {bank_record['id']}.")
            fail_reconciliation_result(bank_record['id'], None, None, 'No match found', 'Pos')

    except Exception as e:
        logger.error(f"Error reconciling POS transaction {bank_record['id']}: {e}", exc_info=True)
        fail_reconciliation_result(bank_record['id'], None, None, f"Processing error: {str(e)}", 'Pos')

