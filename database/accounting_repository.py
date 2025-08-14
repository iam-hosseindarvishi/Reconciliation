from datetime import datetime, timedelta
from database.init_db import create_connection
from utils.logger_config import setup_logger

# راه‌اندازی لاگر
logger = setup_logger('database.accounting_repository')

def create_accounting_transaction(data):
    """ایجاد تراکنش حسابداری جدید با مدیریت خطا"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO AccountingTransactions (
                bank_id, transaction_number, transaction_amount, due_date, collection_date, 
                transaction_type, customer_name, description, is_reconciled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('bank_id'),
            data.get('transaction_number'),
            data.get('transaction_amount'),
            data.get('due_date'),
            data.get('collection_date'),
            data.get('transaction_type'),
            data.get('customer_name'),
            data.get('description', ''),
            data.get('is_reconciled', 0)
        ))
        conn.commit()
        logger.info(f"تراکنش حسابداری جدید با شماره {data.get('transaction_number')} ثبت شد")
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"خطا در ثبت تراکنش حسابداری: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
def get_transactions_by_type(bank_id, transaction_type):
    """دریافت تراکنش‌ها بر اساس نوع تراکنش"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM AccountingTransactions 
            WHERE bank_id = ? AND transaction_type = ?
        """, (bank_id, transaction_type))
        result = cursor.fetchall()
        logger.info(f"تعداد {len(result)} تراکنش از نوع {transaction_type} برای بانک {bank_id} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌های نوع {transaction_type}: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_transactions_by_date_and_type(bank_id, start_date, end_date, transaction_type):
    """دریافت تراکنش‌ها بر اساس تاریخ و نوع تراکنش"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM AccountingTransactions
            WHERE bank_id = ? AND due_date BETWEEN ? AND ? AND transaction_type = ?
        """, (bank_id, start_date, end_date, transaction_type))
        result = cursor.fetchall()
        logger.info(f"تعداد {len(result)} تراکنش از نوع {transaction_type} در بازه {start_date} تا {end_date} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌ها بر اساس تاریخ و نوع: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_transactions_by_date_amount_type(bank_id, transaction_date, amount, transaction_type):
    """Get transactions by date, amount and transaction type"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM AccountingTransactions 
            WHERE bank_id = ? 
            AND due_date = ?
            AND transaction_amount = ?
            AND transaction_type = ?
        """, (bank_id, transaction_date, amount, transaction_type))
        result = cursor.fetchall()
        logger.info(f"Found {len(result)} transactions of type {transaction_type} with amount {amount} on date {transaction_date}")
        return result
    except Exception as e:
        logger.error(f"Error getting transactions by date, amount and type: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()


def get_transactions_by_bank(bank_id):
    """دریافت تمام تراکنش‌های یک بانک"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM AccountingTransactions WHERE bank_id = ?", (bank_id,))
        result = cursor.fetchall()
        logger.info(f"تعداد {len(result)} تراکنش برای بانک {bank_id} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌های بانک {bank_id}: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_transactions_by_due_date_and_bank(bank_id, start_date, end_date):
    """دریافت تراکنش‌ها بر اساس تاریخ سررسید"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM AccountingTransactions
            WHERE bank_id = ? AND due_date BETWEEN ? AND ?
        """, (bank_id, start_date, end_date))
        result = cursor.fetchall()
        logger.info(f"تعداد {len(result)} تراکنش با تاریخ سررسید بین {start_date} تا {end_date} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌ها بر اساس تاریخ سررسید: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_transactions_by_collection_date_and_bank(bank_id, start_date, end_date):
    """دریافت تراکنش‌ها بر اساس تاریخ وصول"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM AccountingTransactions
            WHERE bank_id = ? AND collection_date BETWEEN ? AND ?
        """, (bank_id, start_date, end_date))
        result = cursor.fetchall()
        logger.info(f"تعداد {len(result)} تراکنش با تاریخ وصول بین {start_date} تا {end_date} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌ها بر اساس تاریخ وصول: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def update_reconciliation_status(transaction_id, status):
    """به‌روزرسانی وضعیت تطبیق تراکنش"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        status_int = int(bool(status))
        cursor.execute("""
            UPDATE AccountingTransactions 
            SET is_reconciled = ? 
            WHERE id = ?
        """, (status_int, transaction_id))
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"وضعیت تطبیق تراکنش {transaction_id} به {status_int} تغییر کرد")
        else:
            logger.warning(f"تراکنشی با شناسه {transaction_id} یافت نشد")
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی وضعیت تطبیق تراکنش {transaction_id}: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_accounting_transactions_for_pos(pos_transaction):
    """Get accounting transactions that could match a given POS transaction."""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Search for transactions from the previous day with the same amount
        query = """
            SELECT *
            FROM AccountingTransactions
            WHERE due_date = ?  
              AND transaction_amount = ? 
              AND is_reconciled = 0
        """
        
        params = [
            (datetime.strptime(pos_transaction['transaction_date'], '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d'),
            pos_transaction['amount']
        ]

        cursor.execute(query, params)
        matches = cursor.fetchall()
        logger.info(f"{len(matches)} potential matches found for POS transaction {pos_transaction['id']}.")

        return matches
    except Exception as e:
        logger.error(f"Error getting accounting transactions for POS: {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()


def delete_transaction(transaction_id):
    """حذف تراکنش"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM AccountingTransactions WHERE id = ?", (transaction_id,))
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"تراکنش {transaction_id} با موفقیت حذف شد")
        else:
            logger.warning(f"تراکنشی با شناسه {transaction_id} یافت نشد")
    except Exception as e:
        logger.error(f"خطا در حذف تراکنش {transaction_id}: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
