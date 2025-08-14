
# from ..database import (
#     get_unreconciled_pos_transactions,
#     get_accounting_transactions_for_pos,
#     set_reconciliation_status
# )
from database.accounting_repository import get_transactions_by_date_amount_type
from utils.logger_config import setup_logger
from .manual_reconciliation_dialog import ManualReconciliationDialog
from utils.helpers import get_pos_date_from_bank
logger = setup_logger('reconciliation.mellat_pos_reconciliation')

def reconcile_mellat_pos(pos_transactions, ui_handler):
    """Reconcile Mellat Bank POS transactions."""
    logger.info(f"Starting POS reconciliation for {len(pos_transactions)} transactions.")
    for tx in pos_transactions:
        reconcile_single_pos(tx, ui_handler)
    logger.info(f"Finished POS reconciliation.")

def reconcile_single_pos(pos_transaction, ui_handler):
    """Reconcile a single POS transaction."""
    pos_date = get_pos_date_from_bank(pos_transaction['transaction_date'])
    pos_amount = pos_transaction['transaction_amount']
    pos_type = pos_transaction['transaction_type']

    matches = get_transactions_by_date_amount_type(pos_transaction['bank_id'], pos_date, pos_amount, pos_type)

    if len(matches) == 1:
        # Exact match found
        accounting_doc = matches[0]
        logger.info(f"Reconciled POS transaction {pos_transaction['id']} with accounting doc {accounting_doc['id']}")
    elif len(matches) > 1:
        # Multiple matches, needs user intervention
        logger.warning(f"Multiple matches found for POS transaction {pos_transaction['id']}. Opening dialog for manual selection.")
        dialog = ManualReconciliationDialog(ui_handler.parent, matches)  # Pass parent from ui_handler
        selected_match = dialog.show()

        if selected_match:
            logger.info(f"Manually reconciled POS transaction {pos_transaction['id']} with accounting doc {selected_match['id']}")
        else:
            logger.warning(f"Manual reconciliation cancelled for POS transaction {pos_transaction['id']}")
    else:
        # No match found
        logger.warning(f"No matching accounting document found for POS transaction {pos_transaction['id']}")