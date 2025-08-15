import sqlite3
from datetime import datetime, timedelta
from config.settings import DB_PATH
from utils.logger_config import setup_logger

# راه‌اندازی لاگر
logger = setup_logger('database.reconciliation.reconciliation_repository')

def has_unreconciled_transactions(bank_id):
    """بررسی وجود تراکنش‌های مغایرت‌گیری نشده برای یک بانک"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM BankTransactions 
            WHERE bank_id = ? AND is_reconciled = 0
        """, (bank_id,))
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        logger.error(f"خطا در بررسی تراکنش‌های مغایرت‌گیری نشده: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()


    

def get_accounting_transactions_for_pos(pos_transaction):
    """Get matching accounting transactions for a given POS transaction."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    transaction_date = datetime.strptime(pos_transaction['transaction_date'], '%Y-%m-%d').date()
    previous_day = transaction_date - timedelta(days=1)

    query = """
        SELECT * FROM Accounting
        WHERE CAST(amount AS REAL) = ? AND date = ?
    """
    params = (pos_transaction['amount'], previous_day.strftime('%Y-%m-%d'))

    cursor.execute(query, params)
    matches = [dict(row) for row in cursor.fetchall()]

    if len(matches) > 1:
        # Further filtering if multiple matches are found
        if pos_transaction.get('card_number_last_four'):
            filtered_matches = [m for m in matches if m.get('card_number_last_four') == pos_transaction.get('card_number_last_four')]
            if filtered_matches:
                matches = filtered_matches

    if len(matches) > 1:
        if pos_transaction.get('tracking_code'):
            filtered_matches = [m for m in matches if m.get('tracking_code') == pos_transaction.get('tracking_code')]
            if filtered_matches:
                matches = filtered_matches

    conn.close()
    return matches

def set_reconciliation_status(bank_transaction_id, accounting_doc_id, status):
    """Set the reconciliation status for a bank transaction and an accounting document."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Mark bank transaction as reconciled
        cursor.execute('UPDATE BankTransactions SET is_reconciled = ? WHERE id = ?', (status, bank_transaction_id))
        
        # Mark accounting document as reconciled
        cursor.execute('UPDATE Accounting SET is_reconciled = ? WHERE id = ?', (status, accounting_doc_id))
        
        conn.commit()
        logger.info(f"Set reconciliation status to {status} for bank transaction {bank_transaction_id} and accounting doc {accounting_doc_id}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error setting reconciliation status: {e}")
    finally:
        conn.close()

def has_unknown_transactions(bank_id):
    """بررسی وجود تراکنش‌های نامشخص برای یک بانک"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM BankTransactions 
            WHERE bank_id = ? AND transaction_type = 'Unknown' AND is_reconciled = 0
        """, (bank_id,))
        count = cursor.fetchone()[0]
        return count > 0
    except Exception as e:
        logger.error(f"خطا در بررسی تراکنش‌های نامشخص: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_unknown_transactions_by_bank(bank_id):
    """دریافت تمام تراکنش‌های نامشخص برای یک بانک"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # برای دسترسی به نام ستون‌ها
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM BankTransactions 
            WHERE bank_id = ? AND transaction_type = 'Unknown' AND is_reconciled = 0
            ORDER BY transaction_date, transaction_time
        """, (bank_id,))
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌های نامشخص: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def update_transaction_type(transaction_id, new_type):
    """به‌روزرسانی نوع یک تراکنش"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE BankTransactions 
            SET transaction_type = ? 
            WHERE id = ?
        """, (new_type, transaction_id))
        conn.commit()
        logger.info(f"نوع تراکنش با شناسه {transaction_id} به {new_type} تغییر یافت")
        return True
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی نوع تراکنش: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_categorized_unreconciled_transactions(bank_id):
    """دریافت تراکنش‌های POS مغایرت‌گیری نشده برای یک بانک"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM BankTransactions 
            WHERE bank_id = ? AND is_reconciled = 0
            ORDER BY transaction_type, transaction_date, transaction_time
        """, (bank_id,))
        
        # دسته‌بندی تراکنش‌ها بر اساس نوع
        transactions = [dict(row) for row in cursor.fetchall()]
        categorized = {}
        
        for transaction in transactions:
            transaction_type = transaction['transaction_type']
            if transaction_type not in categorized:
                categorized[transaction_type] = []
            categorized[transaction_type].append(transaction)
        
        return categorized
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌های دسته‌بندی شده: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()