# file: reconciliation/mellat_reconciliation/mellat_paid_transfer_reconciliation.py

import threading
import tkinter as tk
from tkinter import messagebox
from utils.logger_config import setup_logger

from utils.compare_tracking_numbers import compare_tracking_numbers
from database.accounting_repository import get_transactions_by_date_amount_type, get_transactions_by_date_less_than_amount_type, create_accounting_transaction, update_accounting_transaction_reconciliation_status
from reconciliation.save_reconciliation_result import success_reconciliation_result, fail_reconciliation_result
from ui.dialog.manual_reconciliation_dialog import ManualReconciliationDialog

logger = setup_logger('reconciliation.mellat_paid_transfer_reconciliation')

def reconcile_mellat_paid_transfer(bank_transactions, ui_handler):
    """
    Reconciles Mellat Bank Paid Transfer transactions in a separate thread.

    Args:
        bank_transactions (list): List of bank transfer transactions to reconcile.
        ui_handler: An object to handle UI updates.

    """
    thread = threading.Thread(
        target=_reconcile_in_thread,
        args=(bank_transactions, ui_handler)
    )
    thread.start()


def _reconcile_in_thread(bank_transactions, ui_handler):
    """
    The actual reconciliation logic that runs in a separate thread.
    """
    logger.info(f"Starting Paid_Transfer reconciliation for {len(bank_transactions)} transactions.")
    total_transactions = len(bank_transactions)
    for i, bank_record in enumerate(bank_transactions):
        _reconcile_single_transfer(bank_record, ui_handler)

        # Update UI progress
        progress_percentage = (i + 1) / total_transactions * 100
        ui_handler.update_progress(progress_percentage)
        ui_handler.update_detailed_status(f"Reconciled {i + 1} of {total_transactions} transfer transactions.")

    logger.info("Finished Paid_Transfer reconciliation.")
    ui_handler.update_status("Finished Paid_Transfer reconciliation.")


def _reconcile_single_transfer(bank_record, ui_handler):
    """
    Reconciles a single Paid_Transfer transaction.
    """
    try:
        bank_date = bank_record['transaction_date']
        bank_amount = bank_record['amount']
        bank_tracking_num = bank_record['extracted_tracking_number']
        bank_id = bank_record['bank_id']
        transaction_type = 'Paid Transfer'

        # Exact Match
        exact_matches = get_transactions_by_date_amount_type(bank_id, bank_date, bank_amount, transaction_type)
        if len(exact_matches) == 1:
            success_reconciliation_result(bank_record['id'], exact_matches[0]['id'], None, 'Exact match', transaction_type)
            logger.info(f"Reconciled Bank Transfer {bank_record['id']} with accounting doc {exact_matches[0]['id']}")
            return

        # Approximate Match (Fee Reconciliation)
        potential_matches = get_transactions_by_date_less_than_amount_type(bank_id, bank_date, bank_amount, transaction_type)

        if not potential_matches:
            logger.warning(f"No matching accounting document found for Bank Transfer {bank_record['id']}.")
            fail_reconciliation_result(bank_record['id'], None, None, 'No match found', transaction_type)
            return

        possible_matches_with_fee = []
        for match in potential_matches:
            fee = bank_amount - match['transaction_amount']
            if(match['transaction_number']==bank_tracking_num):
                possible_matches_with_fee.append((match, fee))
                break
            elif 0 < fee:
                possible_matches_with_fee.append((match, fee))

        if len(possible_matches_with_fee) == 1:
            match, fee = possible_matches_with_fee[0]
            if fee <= 100000:
                # Automatic Reconciliation
                fee_transaction_data = {
                    'bank_id': bank_id,
                    'transaction_amount': fee,
                    'due_date': bank_date,
                    'transaction_type': 'Fee',
                    'description': f"Fee for transaction {match['transaction_number']}",
                }
                fee_transaction_id = create_accounting_transaction(fee_transaction_data)
                update_accounting_transaction_reconciliation_status(fee_transaction_id, True)
                
                bank_record['amount'] = match['amount']
                success_reconciliation_result(bank_record['id'], match['id'], None, 'Automatic fee reconciliation', transaction_type)
                logger.info(f"Automatically reconciled Bank Transfer {bank_record['id']} with fee {fee}")
                return

        # Manual Confirmation
        # This part requires a dialog for user confirmation. For now, we will log it.
        if possible_matches_with_fee:
            logger.warning(f"Manual confirmation needed for Bank Transfer {bank_record['id']}.")
            # Here you would open a dialog and based on user action proceed or fail.
            # For now, we will fail it as a placeholder for manual intervention.

        fail_reconciliation_result(bank_record['id'], None, None, 'Manual confirmation required', transaction_type)

    except Exception as e:
        logger.error(f"Error reconciling Bank Transfer {bank_record['id']}: {e}", exc_info=True)
        fail_reconciliation_result(bank_record['id'], None, None, f"Processing error: {str(e)}", transaction_type)
    """
    Reconciles a single Paid_Transfer transaction.
    """
   