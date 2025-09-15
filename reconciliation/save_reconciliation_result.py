from database.reconciliation_results_repository import create_reconciliation_result
from database.pos_transactions_repository import update_reconciliation_status
from database.repositories.accounting import update_accounting_transaction_reconciliation_status
from database.bank_transaction_repository import update_bank_transaction_reconciliation_status
from utils.logger_config import setup_logger
logger = setup_logger('save_reconciliation_result')


def success_reconciliation_result(bank_record_id, acc_record_id, pos_record_id, description, match_type):
    """
    Submit successful reconciliation result to the database.
    
    Args:
        bank_record_id: ID of bank transaction
        acc_record_id: ID of accounting transaction
        pos_record_id: ID of POS transaction
        description: Description of reconciliation
        match_type: Type of match found
    """
    try:
        logger.info(f"Recording successful reconciliation: Bank={bank_record_id}, Acc={acc_record_id}, POS={pos_record_id}, Type={match_type}")
        
        # Create reconciliation result record
        create_reconciliation_result(pos_record_id, acc_record_id, bank_record_id, description, match_type)
        logger.debug(f"Created reconciliation result record for {match_type}")
        
        # Update POS transaction status if applicable
        if pos_record_id:
            update_reconciliation_status(pos_record_id, 1)
            logger.info(f"POS transaction {pos_record_id} marked as reconciled")

        # Update accounting transaction status if applicable
        if acc_record_id:
            update_accounting_transaction_reconciliation_status(acc_record_id, 1)
            logger.info(f"Accounting transaction {acc_record_id} marked as reconciled")
            
        # Update bank transaction status if applicable
        if bank_record_id:
            update_bank_transaction_reconciliation_status(bank_record_id, 1)
            logger.info(f"Bank transaction {bank_record_id} marked as reconciled")
            
        logger.info(f"Successfully completed reconciliation for {match_type}: {description}")
        
    except Exception as e:
        logger.error(f"Error submitting successful reconciliation result: {e}", exc_info=True)
        raise
def fail_reconciliation_result(bank_record_id, acc_record_id, pos_record_id, description, match_type):
    """
    Submit failed reconciliation result to the database.
    
    Args:
        bank_record_id: ID of bank transaction
        acc_record_id: ID of accounting transaction
        pos_record_id: ID of POS transaction
        description: Description of reconciliation failure
        match_type: Type of transaction
    """
    try:
        logger.warning(f"Recording failed reconciliation: Bank={bank_record_id}, Acc={acc_record_id}, POS={pos_record_id}, Type={match_type}, Reason={description}")
        
        # Create reconciliation result record for failure
        create_reconciliation_result(pos_record_id, acc_record_id, bank_record_id, description, match_type)
        logger.debug(f"Created failed reconciliation result record for {match_type}")
        
        # Update POS transaction status if applicable
        if pos_record_id:
            update_reconciliation_status(pos_record_id, 0)
            logger.info(f"POS transaction {pos_record_id} marked as failed reconciliation")
            
        # Update accounting transaction status if applicable
        if acc_record_id:
            update_accounting_transaction_reconciliation_status(acc_record_id, 0)
            logger.info(f"Accounting transaction {acc_record_id} marked as failed reconciliation")
            
        # Update bank transaction status if applicable
        if bank_record_id:
            update_bank_transaction_reconciliation_status(bank_record_id, 0)
            logger.info(f"Bank transaction {bank_record_id} marked as failed reconciliation")
            
        logger.warning(f"Recorded failed reconciliation for {match_type}: {description}")
        
    except Exception as e:
        logger.error(f"Error submitting failed reconciliation result: {e}", exc_info=True)
        raise


