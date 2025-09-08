import sqlite3
from database.init_db import create_connection
from utils.logger_config import setup_logger

# راه‌اندازی لاگر
logger = setup_logger('database.bank_fees_repository')

def collect_bank_fees(bank_id):
    """
    جمع‌آوری کارمزدهای بانکی براساس تاریخ برای بانک مشخص شده
    
    Args:
        bank_id: شناسه بانک
        
    Returns:
        تعداد رکوردهای ایجاد شده
    """
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # حذف کارمزدهای قبلی برای این بانک (اختیاری)
        # cursor.execute("DELETE FROM BankFees WHERE bank_id = ?", (bank_id,))
        
        # استخراج کارمزدها براساس تاریخ و ثبت در جدول BankFees
        cursor.execute("""
            INSERT INTO BankFees (bank_id, fee_date, total_amount, transaction_count, description)
            SELECT 
                bank_id, 
                transaction_date, 
                SUM(amount) as total_amount, 
                COUNT(*) as transaction_count,
                'کارمزدهای تجمیع شده' as description
            FROM BankTransactions 
            WHERE bank_id = ? AND transaction_type = 'BANK_FEE' AND is_reconciled = 0
            GROUP BY transaction_date
        """, (bank_id,))
        
        # علامت‌گذاری کارمزدهای پردازش شده به عنوان مغایرت‌گیری شده
        cursor.execute("""
            UPDATE BankTransactions 
            SET is_reconciled = 1 
            WHERE bank_id = ? AND transaction_type = 'BANK_FEE' AND is_reconciled = 0
        """, (bank_id,))
        
        # تعداد رکوردهای ایجاد شده
        rows_affected = cursor.rowcount
        
        conn.commit()
        logger.info(f"کارمزدهای بانک با شناسه {bank_id} با موفقیت جمع‌آوری شدند. {rows_affected} رکورد پردازش شد.")
        return rows_affected
        
    except sqlite3.Error as e:
        logger.error(f"خطا در جمع‌آوری کارمزدهای بانکی: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_bank_fees(bank_id=None):
    """
    دریافت لیست کارمزدهای تجمیع شده
    
    Args:
        bank_id: شناسه بانک (اختیاری)
        
    Returns:
        لیست کارمزدهای تجمیع شده
    """
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        if bank_id:
            cursor.execute("""
                SELECT bf.*, b.bank_name 
                FROM BankFees bf
                JOIN Banks b ON bf.bank_id = b.id
                WHERE bf.bank_id = ?
                ORDER BY bf.fee_date DESC
            """, (bank_id,))
        else:
            cursor.execute("""
                SELECT bf.*, b.bank_name 
                FROM BankFees bf
                JOIN Banks b ON bf.bank_id = b.id
                ORDER BY bf.fee_date DESC
            """)
            
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        
        return result
        
    except sqlite3.Error as e:
        logger.error(f"خطا در دریافت کارمزدهای تجمیع شده: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()