import sqlite3
from database.init_db import create_connection
from utils.logger_config import setup_logger

# راه‌اندازی لاگر
logger = setup_logger('banks_repository')

def create_bank(bank_name):
    """ایجاد بانک جدید"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Banks (bank_name) VALUES (?)", (bank_name,))
        conn.commit()
        logger.info(f"بانک جدید با نام {bank_name} ایجاد شد")
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"خطا در ایجاد بانک {bank_name}: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_all_banks():
    """دریافت لیست تمام بانک‌ها"""
    conn = None
    try:
        conn = create_connection()
        conn.row_factory = sqlite3.Row  # برای دسترسی به نام ستون‌ها
        cursor = conn.cursor()
        cursor.execute("SELECT id, bank_name FROM Banks")
        result = cursor.fetchall()
        logger.info(f"تعداد {len(result)} بانک یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت لیست بانک‌ها: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_bank_by_name(bank_name):
    """جستجوی بانک بر اساس نام"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, bank_name FROM Banks WHERE bank_name = ?", (bank_name,))
        result = cursor.fetchone()
        if result:
            logger.info(f"بانک با نام {bank_name} یافت شد")
        else:
            logger.info(f"بانکی با نام {bank_name} یافت نشد")
        return result
    except Exception as e:
        logger.error(f"خطا در جستجوی بانک {bank_name}: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def delete_bank(bank_id):
    """حذف بانک بر اساس شناسه"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Banks WHERE id = ?", (bank_id,))
        if cursor.rowcount > 0:
            logger.info(f"بانک با شناسه {bank_id} حذف شد")
        else:
            logger.warning(f"بانکی با شناسه {bank_id} یافت نشد")
        conn.commit()
    except Exception as e:
        logger.error(f"خطا در حذف بانک با شناسه {bank_id}: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def update_bank(bank_id, new_bank_name):
    """به‌روزرسانی نام بانک"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Banks SET bank_name = ? WHERE id = ?", (new_bank_name, bank_id))
        if cursor.rowcount > 0:
            logger.info(f"نام بانک با شناسه {bank_id} به {new_bank_name} تغییر یافت")
        else:
            logger.warning(f"بانکی با شناسه {bank_id} یافت نشد")
        conn.commit()
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی نام بانک با شناسه {bank_id}: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()
