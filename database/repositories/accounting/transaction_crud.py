"""
Accounting Transaction CRUD Operations Module
ماژول عملیات CRUD تراکنش‌های حسابداری - جدا شده از accounting_repository.py
"""
from database.init_db import create_connection
from utils.logger_config import setup_logger

# راه‌اندازی لاگر
logger = setup_logger('database.accounting_repository.transaction_crud')


def create_accounting_transaction(data):
    """ایجاد تراکنش حسابداری جدید با مدیریت خطا"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO AccountingTransactions (
                bank_id, transaction_number, transaction_amount, due_date, collection_date, 
                transaction_type, customer_name, description, is_reconciled, is_new_system
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('bank_id'),
            data.get('transaction_number'),
            data.get('transaction_amount'),
            data.get('due_date'),
            data.get('collection_date'),
            data.get('transaction_type'),
            data.get('customer_name'),
            data.get('description', ''),
            data.get('is_reconciled', 0),
            data.get('is_new_system', 0),
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
            return True
        else:
            logger.warning(f"تراکنشی با شناسه {transaction_id} یافت نشد")
            return False
    except Exception as e:
        logger.error(f"خطا در حذف تراکنش {transaction_id}: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def update_accounting_transaction_reconciliation_status(transaction_id, status_or_data):
    """به‌روزرسانی وضعیت تطبیق تراکنش یا به‌روزرسانی کامل تراکنش"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # بررسی نوع پارامتر دوم
        if isinstance(status_or_data, dict):
            # به‌روزرسانی کامل با دیکشنری
            update_fields = []
            params = []
            
            for key, value in status_or_data.items():
                if key != 'id':  # شناسه را به‌روزرسانی نمی‌کنیم
                    update_fields.append(f"{key} = ?")
                    params.append(value)
            
            # افزودن شناسه به پارامترها
            params.append(transaction_id)
            
            query = f"UPDATE AccountingTransactions SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, params)
            
            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"تراکنش حسابداری {transaction_id} با موفقیت به‌روزرسانی شد")
                return True
            else:
                logger.warning(f"تراکنشی با شناسه {transaction_id} یافت نشد")
                return False
        else:
            # به‌روزرسانی فقط وضعیت تطبیق
            status_int = int(bool(status_or_data))
            cursor.execute("""
                UPDATE AccountingTransactions 
                SET is_reconciled = ? 
                WHERE id = ?
            """, (status_int, transaction_id))
            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"وضعیت تطبیق تراکنش {transaction_id} به {status_int} تغییر کرد")
                return True
            else:
                logger.warning(f"تراکنشی با شناسه {transaction_id} یافت نشد")
                return False
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی تراکنش {transaction_id}: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def get_transaction_by_id(transaction_id):
    """دریافت تراکنش با شناسه مشخص"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM AccountingTransactions WHERE id = ?", (transaction_id,))
        result = cursor.fetchone()
        if result:
            # تبدیل tuple به dictionary
            columns = [description[0] for description in cursor.description]
            result = dict(zip(columns, result))
            logger.info(f"تراکنش {transaction_id} یافت شد")
        else:
            logger.warning(f"تراکنشی با شناسه {transaction_id} یافت نشد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش {transaction_id}: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()


def get_transaction_count_by_bank(bank_id, reconciled_only=None):
    """دریافت تعداد تراکنش‌های یک بانک"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        query = "SELECT COUNT(*) FROM AccountingTransactions WHERE bank_id = ?"
        params = [bank_id]
        
        if reconciled_only is not None:
            query += " AND is_reconciled = ?"
            params.append(int(bool(reconciled_only)))
        
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        logger.info(f"تعداد {count} تراکنش برای بانک {bank_id} یافت شد")
        return count
    except Exception as e:
        logger.error(f"خطا در دریافت تعداد تراکنش‌های بانک {bank_id}: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()
