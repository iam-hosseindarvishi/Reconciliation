from datetime import datetime, timedelta
import sqlite3
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
            data.get('is_new_system',0),
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
        # Convert tuple results to a list of dictionaries
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
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
    new_system_type='';
    if(transaction_type in ['Pos','Received Transfer']):
        new_system_type='Pos / Received Transfer'
    elif(transaction_type =='Paid Transfer') :
        new_system_type='Pos / Paid Transfer'
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM AccountingTransactions
            WHERE bank_id = ? AND due_date BETWEEN ? AND ? AND (transaction_type = ? OR transaction_type= ?)
        """, (bank_id, start_date, end_date, transaction_type,new_system_type))
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logger.info(f"تعداد {len(result)} تراکنش از نوع {transaction_type} در بازه {start_date} تا {end_date} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌ها بر اساس تاریخ و نوع: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_transactions_advanced_search(search_params):
    """جستجوی پیشرفته تراکنش‌های حسابداری با پارامترهای متنوع"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # ساخت پرس و جو پایه
        query = "SELECT * FROM AccountingTransactions WHERE 1=1"
        params = []
        
        # اضافه کردن شرط‌ها بر اساس پارامترهای ورودی
        if search_params.get('bank_id'):
            query += " AND bank_id = ?"
            params.append(search_params['bank_id'])
            
        if search_params.get('custom_date'):
            query += " AND due_date = ?"
            params.append(search_params['custom_date'])
            
        if search_params.get('transaction_type'):
            transaction_type=search_params.get('transaction_type')
            new_system_type='';
            if(transaction_type in ['Pos','Received Transfer']):
                new_system_type='Pos / Received Transfer'
            elif(transaction_type =='Paid Transfer') :
                new_system_type='Pos / Paid Transfer'
            query += " AND transaction_type = ? OR transaction_type = ?"
            params.append(search_params['transaction_type'])
            params.append(new_system_type)
            
        if search_params.get('amount'):
            # جستجو بر اساس مبلغ با تلرانس 1000 ریال
            amount = float(search_params['amount'])
            query += " AND transaction_amount BETWEEN ? AND ?"
            params.append(amount - 1000)  # تلرانس پایین
            params.append(amount + 1000)  # تلرانس بالا
            
        if search_params.get('tracking_number'):
            query += " AND transaction_number LIKE ?"
            params.append(f"%{search_params['tracking_number']}%")
        
        # فقط رکوردهای مغایرت‌گیری نشده را برگردان
        query += " AND is_reconciled = 0"
        
        # اجرای پرس و جو
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        logger.info(f"جستجوی پیشرفته: تعداد {len(result)} تراکنش یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در جستجوی پیشرفته تراکنش‌ها: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
            

def get_transactions_by_date_less_than_amount_type(bank_id, transaction_date, amount, transaction_type):
    """Get transactions by date, amount less than specified amount and transaction type"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM AccountingTransactions 
            WHERE bank_id = ? 
            AND due_date = ?
            AND transaction_amount < ?
            AND transaction_type = ?
        """, (bank_id, transaction_date, amount, transaction_type))
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logger.info(f"Found {len(result)} transactions of type {transaction_type} with amount less than {amount} on date {transaction_date}")
        return result
    except Exception as e:
        logger.error(f"Error getting transactions by date, less than amount and type: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_transactions_by_date_amount_type(bank_id, transaction_date, amount, transaction_type):
    """Get transactions by date, amount and transaction type"""
    new_system_type='';
    if(transaction_type in ['Pos','Received Transfer']):
        new_system_type='Pos / Received Transfer'
    elif(transaction_type =='Paid Transfer') :
        new_system_type='Pos / Paid Transfer'
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM AccountingTransactions 
            WHERE bank_id = ? 
            AND due_date = ?
            AND transaction_amount = ?
            AND (transaction_type = ? OR transaction_type=?)
        """, (bank_id, transaction_date, amount, transaction_type,new_system_type))
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logger.info(f"Found {len(result)} transactions of type {transaction_type} with amount {amount} on date {transaction_date}")
        return result
    except Exception as e:
        logger.error(f"Error getting transactions by date, amount and type: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM AccountingTransactions 
            WHERE bank_id = ? 
            AND due_date = ?
            AND transaction_amount = ?
            AND (transaction_type = ? OR transaction_type=?)
        """, (bank_id, transaction_date, amount, transaction_type,new_system_type))
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logger.info(f"Found {len(result)} transactions of type {transaction_type} with amount {amount} on date {transaction_date}")
        return result

def get_transactions_by_date_type(bank_id, transaction_date, transaction_type):
    """Get all transactions by date and transaction type without considering amount"""
    new_system_type='';
    if(transaction_type in ['Pos','Received Transfer']):
        new_system_type='Pos / Received Transfer'
    elif(transaction_type =='Paid Transfer') :
        new_system_type='Pos / Paid Transfer'
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM AccountingTransactions 
            WHERE bank_id = ? 
            AND due_date = ?
            AND (transaction_type = ? OR transaction_type=?)
            AND is_reconciled = 0
        """, (bank_id, transaction_date, transaction_type, new_system_type))
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logger.info(f"Found {len(result)} transactions of type {transaction_type} on date {transaction_date}")
        return result
    except Exception as e:
        logger.error(f"Error getting transactions by date, amount and type: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_transactions_by_amount_tracking(bank_id, amount, tracking_number, transaction_type):
    """جستجوی تراکنش‌های حسابداری بر اساس مبلغ و شماره پیگیری
    
    این تابع برای حل مشکل ثبت رکوردهای بانکی در تاریخ اشتباه استفاده می‌شود.
    
    Args:
        bank_id: شناسه بانک
        amount: مبلغ تراکنش
        tracking_number: شماره پیگیری بانک
        transaction_type: نوع تراکنش (مثلاً 'Paid Transfer')
        
    Returns:
        لیستی از تراکنش‌های حسابداری که مبلغ آنها دقیقاً برابر با مبلغ ورودی است
    """
    new_system_type=''
    if(transaction_type in ['Pos','Received Transfer']):
        new_system_type='Pos / Received Transfer'
    elif(transaction_type =='Paid Transfer') :
        new_system_type='Pos / Paid Transfer'
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM AccountingTransactions 
            WHERE bank_id = ? 
            AND transaction_amount = ?
            AND (transaction_type = ? OR transaction_type=?)
            AND is_reconciled = 0
        """, (bank_id, amount, transaction_type, new_system_type))
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logger.info(f"Found {len(result)} transactions of type {transaction_type} with amount {amount}")
        return result
    except Exception as e:
        logger.error(f"Error getting transactions by amount and tracking number: {str(e)}")
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
            else:
                logger.warning(f"تراکنشی با شناسه {transaction_id} یافت نشد")
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
            else:
                logger.warning(f"تراکنشی با شناسه {transaction_id} یافت نشد")
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی تراکنش {transaction_id}: {str(e)}")
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

def get_unreconciled_pos_transactions(bank_id):
    """دریافت تراکنش‌های POS مغایرت‌نشده"""
    conn = None
    try:
        conn = create_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM PosTransactions 
            WHERE bank_id = ? AND is_reconciled = 0
        """, (bank_id,))
        result = [dict(row) for row in cursor.fetchall()]
        logger.info(f"تعداد {len(result)} تراکنش POS مغایرت‌نشده برای بانک {bank_id} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌های POS مغایرت‌نشده: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_accounting_by_amount_and_types(amount, transaction_types,bank_id=None):
    """دریافت تراکنش‌های حسابداری بر اساس مبلغ و انواع"""
    conn = None
    try:
        conn = create_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        abs_amount=abs(float(amount));
        if isinstance(transaction_types, str):
            transaction_types=[x.strip() for x in transaction_types.split(',')]
        else:
            transaction_types=[x.strip() if isinstance(x, str) else x for x in transaction_types]
        if(len(transaction_types)==0):
            return []
        placeholders = ','.join('?' * len(transaction_types))
        query = f"""
            SELECT * FROM AccountingTransactions
            WHERE transaction_amount = ? 
            AND transaction_type IN ({placeholders})
            AND is_reconciled = 0
            AND ai_processed = 0
        """
        params = [abs_amount] + transaction_types
        if bank_id:
            query += " AND bank_id = ?"
            params.append(bank_id)
        cursor.execute(query, params)
        result = [dict(row) for row in cursor.fetchall()]
        logger.info(f"تعداد {len(result)} تراکنش حسابداری برای مبلغ {amount} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌های حسابداری: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def get_unreconciled_by_type(transaction_type):
    """دریافت تراکنش‌های حسابداری مغایرت‌نشده بر اساس نوع"""
    conn = None
    try:
        conn = create_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM AccountingTransactions 
            WHERE transaction_type = ? AND is_reconciled = 0
        """, (transaction_type,))
        result = [dict(row) for row in cursor.fetchall()]
        logger.info(f"تعداد {len(result)} تراکنش از نوع {transaction_type} مغایرت‌نشده یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌های مغایرت‌نشده: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def update_reconciliation_status(transaction_id, status):
    """تحدیث وضعیت تطبیق تراکنش حسابداری"""
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
            logger.info(f"وضعیت تطبیق تراکنش حسابداری {transaction_id} به {status_int} تغییر کرد")
            return True
        else:
            logger.warning(f"تراکنشی با شناسه {transaction_id} یافت نشد")
            return False
    except Exception as e:
        logger.error(f"خطا در تحدیث وضعیت تطبیق: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def update_ai_processed(transaction_id, ai_processed):
    """به‌روزرسانی وضعیت پردازش AI تراکنش حسابداری"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        ai_processed_int = int(bool(ai_processed))
        cursor.execute("""
            UPDATE AccountingTransactions 
            SET ai_processed = ? 
            WHERE id = ?
        """, (ai_processed_int, transaction_id))
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"وضعیت پردازش AI تراکنش حسابداری {transaction_id} به {ai_processed_int} تغییر کرد")
        else:
            logger.warning(f"تراکنشی با شناسه {transaction_id} یافت نشد")
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی وضعیت پردازش AI تراکنش حسابداری {transaction_id}: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
