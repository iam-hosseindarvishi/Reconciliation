import sqlite3
from config.settings import DB_PATH
from utils.logger_config import setup_logger

# راه‌اندازی لاگر
logger = setup_logger('database.bank_transaction_repository')

def create_bank_transaction(data):
    """ایجاد تراکنش بانکی جدید با مدیریت خطا"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO BankTransactions (
                bank_id, transaction_date, transaction_time, amount, description, 
                reference_number, extracted_terminal_id, extracted_tracking_number, 
                transaction_type, source_card_number, is_reconciled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('bank_id'),
            data.get('transaction_date'),
            data.get('transaction_time'),
            data.get('amount'),
            data.get('description'),
            data.get('reference_number'),
            data.get('extracted_terminal_id'),
            data.get('extracted_tracking_number'),
            data.get('transaction_type'),
            data.get('source_card_number', ''),
            data.get('is_reconciled', 0)
        ))
        conn.commit()
        logger.info(f"تراکنش جدید با شماره مرجع {data.get('reference_number')} ثبت شد")
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        logger.error(f"خطای یکتایی در ثبت تراکنش: {str(e)}")
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        logger.error(f"خطا در ثبت تراکنش: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_transactions_by_bank(bank_id):
    """دریافت تراکنش‌های یک بانک"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM BankTransactions WHERE bank_id = ?", (bank_id,))
        result = cursor.fetchall()
        logger.info(f"تعداد {len(result)} تراکنش برای بانک {bank_id} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌های بانک {bank_id}: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_transactions_by_terminal(bank_id, terminal_id):
    """دریافت تراکنش‌های یک ترمینال"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM BankTransactions 
            WHERE bank_id = ? AND extracted_terminal_id = ?
        """, (bank_id, terminal_id))
        result = cursor.fetchall()
        logger.info(f"تعداد {len(result)} تراکنش برای ترمینال {terminal_id} در بانک {bank_id} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌های ترمینال {terminal_id}: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_transactions_by_date_range(bank_id, start_date, end_date):
    """دریافت تراکنش‌ها در بازه زمانی مشخص"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM BankTransactions
            WHERE bank_id = ? AND transaction_date BETWEEN ? AND ?
        """, (bank_id, start_date, end_date))
        result = cursor.fetchall()
        logger.info(f"تعداد {len(result)} تراکنش در بازه زمانی {start_date} تا {end_date} برای بانک {bank_id} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌ها در بازه زمانی: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_transactions_by_bank_and_date_range(bank_id, start_date, end_date):
    """دریافت تراکنش‌های بانک در بازه زمانی"""
    return get_transactions_by_date_range(bank_id, start_date, end_date)

def get_unreconciled_transactions_by_bank(bank_id):
    """دریافت تراکنش‌های تطبیق نشده"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM BankTransactions 
            WHERE bank_id = ? AND is_reconciled = 0
        """, (bank_id,))
        result = cursor.fetchall()
        logger.info(f"تعداد {len(result)} تراکنش تطبیق نشده برای بانک {bank_id} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌های تطبیق نشده: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def update_reconciliation_status(transaction_id, status):
    """به‌روزرسانی وضعیت تطبیق تراکنش"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        status_int = int(bool(status))
        cursor.execute("""
            UPDATE BankTransactions 
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

def delete_transaction(transaction_id):
    """حذف تراکنش"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM BankTransactions WHERE id = ?", (transaction_id,))
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
