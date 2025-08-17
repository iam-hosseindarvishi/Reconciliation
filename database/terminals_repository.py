from database.init_db import create_connection
from utils.logger_config import setup_logger
import sqlite3

# راه‌اندازی لاگر
logger = setup_logger('database.terminals_repository')

def create_terminal(terminal_number, terminal_name):
    """ایجاد ترمینال جدید با مدیریت خطا"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Terminals (terminal_number, terminal_name)
            VALUES (?, ?)
        """, (terminal_number, terminal_name))
        conn.commit()
        logger.info(f"ترمینال جدید با شماره {terminal_number} ثبت شد")
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        logger.error(f"خطای یکتایی در ثبت ترمینال: {str(e)}")
        if 'terminal_number' in str(e):
            logger.error(f"شماره ترمینال {terminal_number} تکراری است")
        elif 'terminal_name' in str(e):
            logger.error(f"نام ترمینال {terminal_name} تکراری است")
        raise
    except Exception as e:
        logger.error(f"خطا در ثبت ترمینال: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_all_terminals():
    """دریافت لیست تمام ترمینال‌ها"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, terminal_number, terminal_name FROM Terminals")
        result = cursor.fetchall()
        logger.info(f"تعداد {len(result)} ترمینال یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت لیست ترمینال‌ها: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_terminal_by_number(terminal_number):
    """جستجوی ترمینال با شماره ترمینال"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, terminal_number, terminal_name 
            FROM Terminals 
            WHERE terminal_number = ?
        """, (terminal_number,))
        result = cursor.fetchone()
        if result:
            logger.info(f"ترمینال با شماره {terminal_number} یافت شد")
        else:
            logger.info(f"ترمینال با شماره {terminal_number} یافت نشد")
        return result
    except Exception as e:
        logger.error(f"خطا در جستجوی ترمینال: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def delete_terminal(terminal_number):
    """حذف ترمینال"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Terminals WHERE terminal_number = ?", (terminal_number,))
        if cursor.rowcount > 0:
            logger.info(f"ترمینال با شماره {terminal_number} حذف شد")
        else:
            logger.warning(f"ترمینالی با شماره {terminal_number} یافت نشد")
        conn.commit()
    except Exception as e:
        logger.error(f"خطا در حذف ترمینال: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
