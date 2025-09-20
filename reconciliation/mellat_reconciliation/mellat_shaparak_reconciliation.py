# file: reconciliation/mellat_reconciliation/mellat_shaparak_reconciliation.py

import threading
import queue
from datetime import datetime, timedelta
from tkinter import messagebox
from utils.logger_config import setup_logger
from utils.compare_tracking_numbers import compare_tracking_numbers
from database.init_db import create_connection
from reconciliation.save_reconciliation_result import success_reconciliation_result, fail_reconciliation_result

logger = setup_logger('reconciliation.mellat_shaparak_reconciliation')


def reconcile_mellat_shaparak(shaparak_transactions, ui_handler, manual_reconciliation_queue):
    """
    Reconciles Mellat Bank Shaparak transactions in a separate thread to prevent UI freezing.
    
    Shaparak transactions are linked to pos_transaction records and need special handling
    where the transaction date is one day before the bank record date.

    Args:
        shaparak_transactions (list): List of Shaparak transactions to reconcile.
        ui_handler: An object to handle UI updates.
        manual_reconciliation_queue (queue.Queue): The queue for manual reconciliation requests.
    """
    thread = threading.Thread(
        target=_reconcile_in_thread,
        args=(shaparak_transactions, ui_handler, manual_reconciliation_queue)
    )
    thread.start()


def _reconcile_in_thread(shaparak_transactions, ui_handler, manual_reconciliation_queue):
    """
    The actual reconciliation logic that runs in a separate thread.
    """
    logger.info(f"Starting Shaparak reconciliation for {len(shaparak_transactions)} transactions.")
    total_transactions = len(shaparak_transactions)
    
    # Initialize counters for tracking reconciliation results
    successful_reconciliations = 0
    failed_reconciliations = 0
    
    for i, tx in enumerate(shaparak_transactions):
        try:
            result = _reconcile_single_shaparak(tx, ui_handler, manual_reconciliation_queue)
            if result:
                successful_reconciliations += 1
            else:
                failed_reconciliations += 1
        except Exception as e:
            logger.error(f"Error processing Shaparak transaction {tx.get('id', 'unknown')}: {e}")
            failed_reconciliations += 1

        # Update progress with thread-safe UI updates
        progress_percentage = (i + 1) / total_transactions * 100
        try:
            # Use after_idle to ensure UI updates are thread-safe
            if hasattr(ui_handler, 'parent'):
                ui_handler.parent.after_idle(lambda p=progress_percentage: ui_handler.update_progress(p))
                ui_handler.parent.after_idle(lambda i=i, t=total_transactions: ui_handler.update_detailed_status(f"مغایرت‌یابی {i + 1} از {t} تراکنش شاپرک انجام شد."))
            else:
                ui_handler.update_progress(progress_percentage)
                ui_handler.update_detailed_status(f"مغایرت‌یابی {i + 1} از {total_transactions} تراکنش شاپرک انجام شد.")
        except Exception as e:
            logger.warning(f"UI update failed: {e}")

    # Final status update
    final_message = f"مغایرت‌یابی شاپرک تکمیل شد. موفق: {successful_reconciliations}, ناموفق: {failed_reconciliations}"
    logger.info(final_message)
    
    try:
        if hasattr(ui_handler, 'parent'):
            ui_handler.parent.after_idle(lambda: ui_handler.update_status(final_message))
        else:
            ui_handler.update_status(final_message)
    except Exception as e:
        logger.warning(f"Final UI update failed: {e}")


def _reconcile_single_shaparak(bank_record, ui_handler, manual_reconciliation_queue):
    """
    Reconciles a single Shaparak transaction with POS transaction records.
    
    Algorithm:
    1. Calculate POS date (one day before bank transaction date)
    2. Search for Mellat POS transactions in pos_transaction table for the calculated date
    3. Match with accounting transactions based on amount and date
    4. Mark all related transactions as reconciled
    
    Returns True if reconciliation was successful, False otherwise.
    """
    try:
        # Step 1: Calculate POS date (one day before bank date)
        bank_date_str = bank_record['transaction_date']
        bank_amount = bank_record['amount']
        bank_id = bank_record['bank_id']
        
        pos_date = calculate_pos_date(bank_date_str)
        if not pos_date:
            logger.error(f"Could not calculate POS date for bank record {bank_record['id']}")
            fail_reconciliation_result(bank_record['id'], None, None, 'Invalid transaction date', 'Shaparak')
            return False
            
        logger.info(f"Calculated POS date: {pos_date} for bank date: {bank_date_str}")
        
        # Step 2: Find POS transactions for Mellat bank on the calculated date
        pos_transactions = get_mellat_pos_transactions_by_date_amount(pos_date, bank_amount, bank_id)
        
        if not pos_transactions:
            logger.warning(f"No POS transactions found for Shaparak transaction {bank_record['id']} on {pos_date}")
            fail_reconciliation_result(bank_record['id'], None, None, 'No POS transactions found', 'Shaparak')
            return False
        
        logger.info(f"Found {len(pos_transactions)} POS transactions for Shaparak reconciliation")
        
        # Step 3: Find accounting transactions that match the POS date and amount
        accounting_matches = get_accounting_transactions_for_shaparak(bank_id, pos_date, bank_amount)
        
        if not accounting_matches:
            logger.warning(f"No accounting transactions found for Shaparak transaction {bank_record['id']}")
            fail_reconciliation_result(bank_record['id'], None, None, 'No accounting transactions found', 'Shaparak')
            return False
        
        # Step 4: Try to find the best match
        best_accounting_match = None
        
        if len(accounting_matches) == 1:
            best_accounting_match = accounting_matches[0]
        else:
            # Multiple matches found - try to find the best one using tracking numbers
            bank_tracking = bank_record.get('extracted_tracking_number', '')
            if bank_tracking:
                for acc_match in accounting_matches:
                    acc_tracking = acc_match.get('transaction_number', '')
                    if compare_tracking_numbers(bank_tracking, acc_tracking):
                        best_accounting_match = acc_match
                        break
            
            # If no tracking match found, use the first one
            if not best_accounting_match and accounting_matches:
                best_accounting_match = accounting_matches[0]
        
        if not best_accounting_match:
            logger.warning(f"Could not determine best accounting match for Shaparak transaction {bank_record['id']}")
            fail_reconciliation_result(bank_record['id'], None, None, 'No suitable accounting match found', 'Shaparak')
            return False
        
        # Step 5: Perform reconciliation
        result = perform_shaparak_reconciliation(
            bank_record, best_accounting_match, pos_transactions
        )
        
        if result:
            logger.info(f"Successfully reconciled Shaparak transaction {bank_record['id']}")
            return True
        else:
            logger.error(f"Failed to perform reconciliation for Shaparak transaction {bank_record['id']}")
            fail_reconciliation_result(bank_record['id'], None, None, 'Reconciliation operation failed', 'Shaparak')
            return False
            
    except Exception as e:
        logger.error(f"Error reconciling Shaparak transaction {bank_record['id']}: {e}", exc_info=True)
        fail_reconciliation_result(bank_record['id'], None, None, f"Processing error: {str(e)}", 'Shaparak')
        return False


def calculate_pos_date(bank_date_str):
    """
    Calculate POS date (one day before bank transaction date)
    
    Args:
        bank_date_str: Bank transaction date in YYYY-MM-DD format
        
    Returns:
        str: POS date in YYYY-MM-DD format or None if error
    """
    try:
        # Parse bank date
        bank_date = datetime.strptime(bank_date_str, '%Y-%m-%d')
        # Subtract one day
        pos_date = bank_date - timedelta(days=1)
        return pos_date.strftime('%Y-%m-%d')
    except Exception as e:
        logger.error(f"Error calculating POS date from {bank_date_str}: {str(e)}")
        return None


def get_mellat_pos_transactions_by_date_amount(pos_date, amount, bank_id):
    """
    Get POS transactions from pos_transaction table for Mellat bank on a specific date and amount
    
    Args:
        pos_date: Date to search for POS transactions
        amount: Transaction amount
        bank_id: Bank ID (should be Mellat - ID 1)
        
    Returns:
        list: List of matching POS transactions
    """
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # Search for POS transactions with matching amount and date for Mellat bank
        cursor.execute("""
            SELECT * FROM PosTransactions 
            WHERE transaction_date = ? 
            AND ABS(transaction_amount) = ?
            AND bank_id = ?
            AND is_reconciled = 0
        """, (pos_date, abs(float(amount)), bank_id))
        
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        logger.info(f"Found {len(result)} POS transactions for date {pos_date}, amount {amount}, bank {bank_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting POS transactions: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()


def get_accounting_transactions_for_shaparak(bank_id, transaction_date, amount):
    """
    Get accounting transactions that match the Shaparak criteria
    
    Args:
        bank_id: Bank ID
        transaction_date: Transaction date
        amount: Transaction amount
        
    Returns:
        list: List of matching accounting transactions
    """
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # Search for accounting transactions with matching criteria
        # Using the same pattern as the agricultural bank reconciliation
        cursor.execute("""
            SELECT * FROM AccountingTransactions 
            WHERE bank_id = ? 
            AND due_date = ?
            AND ABS(transaction_amount) = ?
            AND (transaction_type = 'Pos' OR transaction_type = 'Pos / Received Transfer')
            AND is_reconciled = 0
        """, (bank_id, transaction_date, abs(float(amount))))
        
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        logger.info(f"Found {len(result)} accounting transactions for Shaparak reconciliation")
        return result
        
    except Exception as e:
        logger.error(f"Error getting accounting transactions for Shaparak: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()


def perform_shaparak_reconciliation(bank_record, accounting_record, pos_transactions):
    """
    Perform the actual reconciliation between bank, accounting, and POS records
    
    Args:
        bank_record: Bank transaction record
        accounting_record: Accounting transaction record  
        pos_transactions: List of POS transactions
        
    Returns:
        bool: True if successful
    """
    try:
        # Import required functions
        from database.bank_transaction_repository import update_bank_transaction_reconciliation_status
        from database.repositories.accounting.transaction_crud import update_accounting_transaction_reconciliation_status
        from database.pos_transactions_repository import update_reconciliation_status
        
        # Mark bank transaction as reconciled
        update_bank_transaction_reconciliation_status(bank_record['id'], True)
        
        # Mark accounting transaction as reconciled
        update_accounting_transaction_reconciliation_status(accounting_record['id'], True)
        
        # Mark all related POS transactions as reconciled
        for pos_transaction in pos_transactions:
            update_reconciliation_status(pos_transaction['id'], True)
            logger.info(f"POS transaction {pos_transaction['id']} marked as reconciled")
        
        # Record the reconciliation result
        pos_id = pos_transactions[0]['id'] if pos_transactions else None
        description = f"شاپرک - مغایرت‌یابی با {len(pos_transactions)} تراکنش پوز - مبلغ: {bank_record['amount']}"
        
        success_reconciliation_result(
            bank_record['id'],
            accounting_record['id'],
            pos_id,
            description,
            'Shaparak'
        )
        
        logger.info(f"Shaparak reconciliation successful: Bank ID={bank_record['id']}, " +
                   f"Acc ID={accounting_record['id']}, POS count={len(pos_transactions)}")
        return True
        
    except Exception as e:
        logger.error(f"Error in Shaparak reconciliation operation: {str(e)}")
        return False


def mark_related_pos_transactions_reconciled(pos_transactions):
    """
    Mark all related POS transactions as reconciled
    
    Args:
        pos_transactions: List of POS transactions to mark as reconciled
    """
    try:
        from database.pos_transactions_repository import update_reconciliation_status
        
        for pos_transaction in pos_transactions:
            update_reconciliation_status(pos_transaction['id'], True)
            logger.info(f"POS transaction {pos_transaction['id']} marked as reconciled")
        
        logger.info(f"Marked {len(pos_transactions)} POS transactions as reconciled")
        
    except Exception as e:
        logger.error(f"Error marking POS transactions as reconciled: {str(e)}")
