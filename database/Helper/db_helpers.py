# file: database/Helper/db_helpers.py

import sqlite3
from config.settings import DB_PATH
from utils.logger_config import setup_logger
from database.bank_transaction_repository import create_bank_transaction

# راه‌اندازی لاگر
logger = setup_logger('database.Helper.db_helpers')

def deduct_fee(bank_record_id, original_amount, fee_amount, description=None):
    """
    کسر کارمزد از مبلغ تراکنش بانکی و ایجاد رکورد جدید برای کارمزد
    
    Args:
        bank_record_id (int): شناسه رکورد بانک
        original_amount (float): مبلغ اصلی تراکنش
        fee_amount (float): مبلغ کارمزد
        description (str, optional): توضیحات اضافی برای رکورد کارمزد
    
    Returns:
        tuple: (updated_bank_record_id, fee_record_id) شناسه رکورد بانک به‌روزرسانی شده و شناسه رکورد کارمزد
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # برای دسترسی به نام ستون‌ها
        cursor = conn.cursor()
        
        # دریافت اطلاعات رکورد بانک
        cursor.execute("SELECT * FROM BankTransactions WHERE id = ?", (bank_record_id,))
        bank_record = dict(cursor.fetchone())
        
        if not bank_record:
            logger.error(f"رکورد بانک با شناسه {bank_record_id} یافت نشد")
            return None, None
        
        # به‌روزرسانی مبلغ رکورد بانک به مبلغ اصلی
        cursor.execute("""
            UPDATE BankTransactions 
            SET amount = ? 
            WHERE id = ?
        """, (original_amount, bank_record_id))
        
        # ایجاد رکورد جدید برای کارمزد
        fee_description = description or f"کارمزد برای رکورد {bank_record_id}"
        
        # ایجاد داده‌های رکورد کارمزد
        fee_record_data = {
            'bank_id': bank_record['bank_id'],
            'transaction_date': bank_record['transaction_date'],
            'transaction_time': bank_record['transaction_time'],
            'amount': fee_amount,
            'description': fee_description,
            'reference_number': bank_record['reference_number'],
            'extracted_terminal_id': bank_record['extracted_terminal_id'],
            'extracted_tracking_number': bank_record['extracted_tracking_number'],
            'transaction_type': 'bank_fee',  # نوع تراکنش کارمزد
            'source_card_number': bank_record['source_card_number'],
            'is_reconciled': 0  # وضعیت تطبیق نشده
        }
        
        # ایجاد رکورد کارمزد در جدول
        cursor.execute("""
            INSERT INTO BankTransactions (
                bank_id, transaction_date, transaction_time, amount, description, 
                reference_number, extracted_terminal_id, extracted_tracking_number, 
                transaction_type, source_card_number, is_reconciled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fee_record_data['bank_id'],
            fee_record_data['transaction_date'],
            fee_record_data['transaction_time'],
            fee_record_data['amount'],
            fee_record_data['description'],
            fee_record_data['reference_number'],
            fee_record_data['extracted_terminal_id'],
            fee_record_data['extracted_tracking_number'],
            fee_record_data['transaction_type'],
            fee_record_data['source_card_number'],
            fee_record_data['is_reconciled']
        ))
        
        fee_record_id = cursor.lastrowid
        
        conn.commit()
        logger.info(f"کارمزد به مبلغ {fee_amount} از رکورد بانک {bank_record_id} کسر شد و رکورد کارمزد با شناسه {fee_record_id} ایجاد شد")
        
        return bank_record_id, fee_record_id
    
    except Exception as e:
        logger.error(f"خطا در کسر کارمزد از رکورد بانک {bank_record_id}: {str(e)}")
        if conn:
            conn.rollback()
        raise
    
    finally:
        if conn:
            conn.close()