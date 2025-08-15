# file: reconciliation/mellat_received_transfer_reconciliation.py

import threading
import tkinter as tk
from tkinter import messagebox
from utils.logger_config import setup_logger
from utils.helpers import get_transfer_date_from_bank
from utils.compare_tracking_numbers import compare_tracking_numbers
from database.accounting_repository import get_transactions_by_date_amount_type
from reconciliation.save_reconciliation_result import success_reconciliation_result, fail_reconciliation_result
from ui.dialog.manual_reconciliation_dialog import ManualReconciliationDialog

logger = setup_logger('reconciliation.mellat_received_transfer_reconciliation')


class UiHandler:
    """
    A helper class to pass UI elements to a separate thread.
    This ensures the thread has a reference to the UI widgets and variables
    it needs to update, without being tightly coupled to the main UI class.
    """
    def __init__(self, parent, overall_progressbar, detailed_status_var, overall_status_var):
        self.parent = parent
        self.overall_progressbar = overall_progressbar
        self.detailed_status_var = detailed_status_var
        self.overall_status_var = overall_status_var
    
    def update_idletasks(self):
        """
        Updates the UI to show changes.
        """
        if self.parent:
            self.parent.update_idletasks()

def reconcile_mellat_received_transfer(bank_transactions, parent_widget, overall_progressbar, detailed_status_var, overall_status_var, on_complete):
    """
    Reconciles Mellat Bank Received Transfer transactions in a separate thread.

    Args:
        bank_transactions (list): List of bank transfer transactions to reconcile.
        parent_widget: The main parent widget for dialogs.
        overall_progressbar: The main progress bar widget.
        detailed_status_var: StringVar for detailed status updates.
        overall_status_var: StringVar for overall status updates.
        on_complete (callable): A callback function to call when reconciliation is finished.
    """
    ui_handler = UiHandler(parent_widget, overall_progressbar, detailed_status_var, overall_status_var)

    thread = threading.Thread(
        target=_reconcile_in_thread,
        args=(bank_transactions, ui_handler, on_complete)
    )
    thread.start()


def _reconcile_in_thread(bank_transactions, ui_handler, on_complete):
    """
    The actual reconciliation logic that runs in a separate thread.
    """
    logger.info(f"Starting Received_Transfer reconciliation for {len(bank_transactions)} transactions.")
    total_transactions = len(bank_transactions)
    for i, bank_record in enumerate(bank_transactions):
        _reconcile_single_transfer(bank_record, ui_handler)

        # Update UI progress
        progress_percentage = (i + 1) / total_transactions * 100
        ui_handler.overall_progressbar['value'] = progress_percentage
        ui_handler.detailed_status_var.set(f"Reconciled {i + 1} of {total_transactions} transfer transactions.")
        ui_handler.update_idletasks()

    logger.info("Finished Received_Transfer reconciliation.")
    ui_handler.overall_status_var.set("Finished Received_Transfer reconciliation.")
    ui_handler.update_idletasks()
    on_complete()


def _reconcile_single_transfer(bank_record, ui_handler):
    """
    Reconciles a single Received_Transfer transaction.
    """
    try:
        bank_date = bank_record['transaction_date']
        bank_amount = bank_record['amount']
        bank_tracking_num = bank_record['extracted_tracking_number']

        # Step 1: Get all potential matches based on date, amount, and type
        matches = get_transactions_by_date_amount_type(bank_record['bank_id'], bank_date, bank_amount, 'Received Transfer')

        # Helper function for consistent success handling
        def handle_success(accounting_doc):
            success_reconciliation_result(bank_record['id'], accounting_doc['id'], None, 'Exact match', 'Received_Transfer')
            logger.info(f"Reconciled Bank Transfer {bank_record['id']} with accounting doc {accounting_doc['id']}")

        # Step 2: Prioritize matching based on tracking number
        if matches:
            tracking_matches = [
                match for match in matches
                if compare_tracking_numbers(bank_tracking_num, match['transaction_number'])
            ]

            if len(tracking_matches) == 1:
                handle_success(tracking_matches[0])
                return
            elif len(tracking_matches) > 1:
                # Multiple tracking matches still require manual intervention
                matches = tracking_matches

        if len(matches) == 1:
            # Fallback to a single match if no tracking number was available
            handle_success(matches[0])
        elif len(matches) > 1:
            # Multiple matches, requiring user intervention
            logger.warning(f"Multiple matches found for Bank Transfer {bank_record['id']}. Opening dialog.")
            dialog = ManualReconciliationDialog(ui_handler.parent, matches)
            selected_match = dialog.show()
            if selected_match:
                handle_success(selected_match)
            else:
                fail_reconciliation_result(bank_record['id'], None, None, 'Manual reconciliation cancelled', 'Received_Transfer')
        else:
            # No match found
            logger.warning(f"No matching accounting document found for Bank Transfer {bank_record['id']}.")
            fail_reconciliation_result(bank_record['id'], None, None, 'No match found', 'Received_Transfer')

    except Exception as e:
        logger.error(f"Error reconciling Bank Transfer {bank_record['id']}: {e}", exc_info=True)
        fail_reconciliation_result(bank_record['id'], None, None, f"Processing error: {str(e)}", 'Received_Transfer')
