import sqlite3
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
    """دریافت تراکنش‌های مغایرت‌گیری نشده به صورت دسته‌بندی شده و مرتب"""
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