# file: reconciliation/mellat_reconciliation/mellat_paid_transfer_reconciliation.py

# file: reconciliation/mellat_reconciliation/mellat_paid_transfer_reconciliation.py

import queue
import threading
import tkinter as tk
from tkinter import messagebox
from utils.logger_config import setup_logger

from utils.compare_tracking_numbers import compare_tracking_numbers
from database.accounting_repository import get_transactions_by_date_amount_type, get_transactions_by_date_less_than_amount_type, create_accounting_transaction, update_accounting_transaction_reconciliation_status
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

        # Exact Match
        exact_matches = get_transactions_by_date_amount_type(bank_id, bank_date, bank_amount, transaction_type)
        if len(exact_matches) == 1:
            success_reconciliation_result(bank_record['id'], exact_matches[0]['id'], None, 'Exact match', transaction_type)
            logger.info(f"Reconciled Bank Transfer {bank_record['id']} with accounting doc {exact_matches[0]['id']}")
            return

        # Fixed Fee Match
        for fee in [450, 360]:
            potential_matches = get_transactions_by_date_amount_type(bank_id, bank_date, bank_amount - fee, transaction_type)
            if len(potential_matches) == 1:
                match = potential_matches[0]
                fee_transaction_data = {
                    'bank_id': bank_id,
                    'transaction_amount': fee,
                    'due_date': bank_date,
                    'transaction_type': 'Fee',
                    'description': f"Fee for transaction {match['transaction_number']}",
                }
                fee_transaction_id = create_accounting_transaction(fee_transaction_data)
                update_accounting_transaction_reconciliation_status(fee_transaction_id, True)

                bank_record['amount'] = match['transaction_amount']
                success_reconciliation_result(bank_record['id'], match['id'], None, f'Automatic fee reconciliation with fee: {fee}', transaction_type)
                logger.info(f"Automatically reconciled Bank Transfer {bank_record['id']} with fee {fee}")
                return

        # Manual Reconciliation Dialog
        potential_matches = get_transactions_by_date_less_than_amount_type(bank_id, bank_date, bank_amount, transaction_type)
        result_queue = queue.Queue()
        manual_reconciliation_queue.put((bank_record, potential_matches, result_queue, 'Paid_Transfer'))
        result = result_queue.get()  # Wait for the result from the main thread

        if result:
            success_reconciliation_result(bank_record['id'], result['id'], None, 'Manual reconciliation', transaction_type)
            logger.info(f"Manually reconciled Bank Transfer {bank_record['id']} with accounting doc {result['id']}")
        else:
            fail_reconciliation_result(bank_record['id'], None, None, 'No match found', transaction_type)
            logger.warning(f"Manual reconciliation failed for Bank Transfer {bank_record['id']}. No match selected.")

    except Exception as e:
        logger.error(f"Error reconciling Bank Transfer {bank_record['id']}: {e}", exc_info=True)
        fail_reconciliation_result(bank_record['id'], None, None, f"Processing error: {str(e)}", transaction_type)
   