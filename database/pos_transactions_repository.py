from database.init_db import create_connection
from utils.logger_config import setup_logger
import sqlite3

# راه‌اندازی لاگر
logger = setup_logger('database.pos_transactions_repository')

def create_pos_transaction(transaction_data):
    """ایجاد تراکنش پوز جدید با مدیریت خطا"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO PosTransactions (
                terminal_number, terminal_id, bank_id, card_number, transaction_date, 
                transaction_amount, tracking_number, is_reconciled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction_data.get('terminal_number'),
            transaction_data.get('terminal_id'),
            transaction_data.get('bank_id'),
            transaction_data.get('card_number'),
            transaction_data.get('transaction_date'),
            transaction_data.get('transaction_amount'),
            transaction_data.get('tracking_number'),
            transaction_data.get('is_reconciled', 0)
        ))
        conn.commit()
        logger.info(f"تراکنش پوز جدید با شماره پیگیری {transaction_data.get('tracking_number')} ثبت شد")
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        logger.error(f"خطای یکتایی در ثبت تراکنش پوز: {str(e)}")
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        logger.error(f"خطا در ثبت تراکنش پوز: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_transactions_by_terminal(terminal_number):
    """دریافت تراکنش‌های یک ترمینال"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM PosTransactions WHERE terminal_number = ?", (terminal_number,))
        result = cursor.fetchall()
        logger.info(f"تعداد {len(result)} تراکنش برای ترمینال {terminal_number} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌های ترمینال {terminal_number}: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_transactions_by_date_and_terminal(terminal_number, date):
    """دریافت تراکنش‌های یک ترمینال در تاریخ مشخص"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM PosTransactions
            WHERE terminal_number = ? AND transaction_date = ?
        """, (terminal_number, date))
        result = cursor.fetchall()
        logger.info(f"تعداد {len(result)} تراکنش برای ترمینال {terminal_number} در تاریخ {date} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌های ترمینال {terminal_number} در تاریخ {date}: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_transaction_by_date(date):
    """دریافت تراکنش‌های یک تاریخ مشخص"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM PosTransactions WHERE transaction_date = ?", (date,))
        result = cursor.fetchall()
        logger.info(f"تعداد {len(result)} تراکنش در تاریخ {date} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌های تاریخ {date}: {str(e)}")
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
            UPDATE PosTransactions 
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
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM PosTransactions WHERE id = ?", (transaction_id,))
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

def get_transactions_by_bank(bank_id):
    """دریافت تراکنش‌های یک بانک"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM PosTransactions WHERE bank_id = ?", (bank_id,))
        result = cursor.fetchall()
        logger.info(f"تعداد {len(result)} تراکنش برای بانک با شناسه {bank_id} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌های بانک با شناسه {bank_id}: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()
