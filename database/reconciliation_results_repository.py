# file: database/reconciliation_results_repository.py

import sqlite3
from .init_db import create_connection

def create_reconciliation_result(pos_id, acc_id, bank_record_id, description, type_matched):
    """
    Adds a new reconciliation result to the database.

    Args:
        pos_id (int): ID of the corresponding POS transaction.
        acc_id (int): ID of the corresponding Accounting transaction.
        bank_record_id (int): ID of the corresponding Bank transaction record.
        description (str): Description of the reconciliation result.
        type_matched (str): The type of matched transaction.

    Returns:
        bool: True if successful, False otherwise.
    """
    conn = create_connection()
    if conn:
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ReconciliationResults (
                        pos_id, acc_id, bank_record_id, description, type_matched
                    ) VALUES (?, ?, ?, ?, ?)
                """, (pos_id, acc_id, bank_record_id, description, type_matched))
            return True
        except sqlite3.Error as e:
            print(f"Error creating reconciliation result: {e}")
            return False
        finally:
            conn.close()
    return False

def get_all_reconciliation_results():
    """
    Fetches all reconciliation results from the database.

    Returns:
        list: A list of tuples containing all results.
    """
    conn = create_connection()
    if conn:
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM ReconciliationResults")
                return cursor.fetchall()
        finally:
            conn.close()
    return []

def get_reconciliation_results_by_bank_id(bank_id):
    """
    Fetches reconciliation results based on the bank ID.

    This function performs a join operation to link the ReconciliationResults table
    with the PosTransactions and AccountingTransactions tables.

    Args:
        bank_id (int): The ID of the bank to filter by.

    Returns:
        list: A list of tuples containing the filtered results.
    """
    conn = create_connection()
    if conn:
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        r.id, r.pos_id, r.acc_id, r.bank_record_id, r.description, r.type_matched, r.date_time
                    FROM ReconciliationResults r
                    LEFT JOIN PosTransactions p ON r.pos_id = p.id
                    LEFT JOIN AccountingTransactions a ON r.acc_id = a.id
                    LEFT JOIN BankTransactions b ON r.bank_record_id = b.id
                    WHERE p.bank_id = ? OR a.bank_id = ? OR b.bank_id = ?
                """, (bank_id, bank_id, bank_id))
                return cursor.fetchall()
        finally:
            conn.close()
    return []

def delete_reconciliation_result(result_id):
    """
    Deletes a reconciliation result by its ID.

    Args:
        result_id (int): The ID of the result to be deleted.

    Returns:
        bool: True if successful, False otherwise.
    """
    conn = create_connection()
    if conn:
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ReconciliationResults WHERE id = ?", (result_id,))
                return cursor.rowcount > 0
        finally:
            conn.close()
    return False

def get_reconciliation_results():
    """
    Fetches all reconciliation results from the database with detailed information.

    Returns:
        list: A list of dictionaries containing all results with joined data from related tables.
    """
    conn = create_connection()
    if conn:
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    r.*, 
                    b.bank_name,
                    bt.amount as bank_amount,
                    bt.transaction_date as bank_date,
                    bt.transaction_type as bank_transaction_type,
                    at.transaction_amount as accounting_amount,
                    at.due_date as accounting_date,
                    at.transaction_type as accounting_transaction_type,
                    pt.transaction_amount as pos_amount,
                    pt.transaction_date as pos_date
                FROM ReconciliationResults r
                LEFT JOIN BankTransactions bt ON r.bank_record_id = bt.id
                LEFT JOIN AccountingTransactions at ON r.acc_id = at.id
                LEFT JOIN PosTransactions pt ON r.pos_id = pt.id
                LEFT JOIN Banks b ON bt.bank_id = b.id
            """)
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except sqlite3.Error as e:
            print(f"Error fetching reconciliation results: {e}")
            return []
        finally:
            conn.close()
    return []