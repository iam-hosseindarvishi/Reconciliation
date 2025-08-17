from database.reconciliation_results_repository import create_reconciliation_result
from database.pos_transactions_repository import update_reconciliation_status
from database.accounting_repository import update_accounting_transaction_reconciliation_status
from database.bank_transaction_repository import update_bank_transaction_reconciliation_status
from utils.logger_config import setup_logger
logger = setup_logger('save_reconciliation_result')


def success_reconciliation_result(bank_record_id,acc_record_id,pos_record_id,description,match_type):
    try:
            """Submit reconciliation result to the database."""
            create_reconciliation_result(pos_record_id,acc_record_id,bank_record_id,description,match_type)
            if(pos_record_id):
                update_reconciliation_status(pos_record_id,1)
                logger.info(f"POS transaction {pos_record_id} marked as reconciled")

            if(acc_record_id):
                update_accounting_transaction_reconciliation_status(acc_record_id,1)
                logger.info(f"Accounting transaction {acc_record_id} marked as reconciled")
            if(bank_record_id):
                update_bank_transaction_reconciliation_status(bank_record_id,1)
                logger.info(f"Bank transaction {bank_record_id} marked as reconciled")
    except Exception as e:
        logger.error(f"Error submitting reconciliation result: {e}")
        raise
def fail_reconciliation_result(bank_record_id,acc_record_id,pos_record_id,description,match_type):
    try:
        """Submit reconciliation result to the database."""
        create_reconciliation_result(pos_record_id,acc_record_id,bank_record_id,description,match_type)
        if(pos_record_id):
            update_reconciliation_status(pos_record_id,0)
            logger.info(f"POS transaction {pos_record_id} marked as failed")
        if(acc_record_id):
            update_accounting_transaction_reconciliation_status(acc_record_id,0)
            logger.info(f"Accounting transaction {acc_record_id} marked as failed")
        if(bank_record_id):
            update_bank_transaction_reconciliation_status(bank_record_id,0)
            logger.info(f"Bank transaction {bank_record_id} marked as failed")
    except Exception as e:
        logger.error(f"Error submitting reconciliation result: {e}")
        raise


