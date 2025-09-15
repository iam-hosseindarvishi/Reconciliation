"""
Transaction Search and Query Operations Module
ماژول جستجوی پیشرفته تراکنش‌های حسابداری - جدا شده از accounting_repository.py
"""
from datetime import datetime, timedelta
from database.init_db import create_connection
from .transaction_type_mapper import TransactionTypeMapper
from utils.logger_config import setup_logger

# راه‌اندازی لاگر
logger = setup_logger('database.accounting_repository.transaction_search')


def get_transactions_by_type(bank_id, transaction_type):
    """دریافت تراکنش‌ها بر اساس نوع تراکنش"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # استفاده از TransactionTypeMapper برای نگاشت نوع تراکنش
        type_condition, type_params = TransactionTypeMapper.create_type_condition_sql(transaction_type)
        
        query = f"""
            SELECT * FROM AccountingTransactions 
            WHERE bank_id = ? AND {type_condition}
        """
        params = [bank_id] + type_params
        
        cursor.execute(query, params)
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
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # استفاده از TransactionTypeMapper
        type_condition, type_params = TransactionTypeMapper.create_type_condition_sql(transaction_type)
        
        query = f"""
            SELECT * FROM AccountingTransactions
            WHERE bank_id = ? AND due_date BETWEEN ? AND ? AND {type_condition}
        """
        params = [bank_id, start_date, end_date] + type_params
        
        cursor.execute(query, params)
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
            transaction_type = search_params.get('transaction_type')
            type_condition, type_params = TransactionTypeMapper.create_type_condition_sql(transaction_type)
            query += f" AND {type_condition}"
            params.extend(type_params)
            
        if search_params.get('amount'):
            # جستجو بر اساس مبلغ با تلرانس 1000 ریال
            amount = float(search_params['amount'])
            query += " AND transaction_amount BETWEEN ? AND ?"
            params.append(amount - 1000)  # تلرانس پایین
            params.append(amount + 1000)  # تلرانس بالا
            
        if search_params.get('tracking_number'):
            query += " AND transaction_number LIKE ?"
            params.append(f"%{search_params['tracking_number']}%")
        
        # فقط رکوردهای مغایرت‌گیری نشده را برگردان (مگر اینکه صراحتاً درخواست شده باشد)
        if not search_params.get('include_reconciled', False):
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
        
        # استفاده از TransactionTypeMapper
        type_condition, type_params = TransactionTypeMapper.create_type_condition_sql(transaction_type)
        
        query = f"""
            SELECT * FROM AccountingTransactions 
            WHERE bank_id = ? 
            AND due_date = ?
            AND transaction_amount < ?
            AND {type_condition}
        """
        params = [bank_id, transaction_date, amount] + type_params
        
        cursor.execute(query, params)
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
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # استفاده از TransactionTypeMapper
        type_condition, type_params = TransactionTypeMapper.create_type_condition_sql(transaction_type)
        
        query = f"""
            SELECT * FROM AccountingTransactions 
            WHERE bank_id = ? 
            AND due_date = ?
            AND transaction_amount = ?
            AND {type_condition}
        """
        params = [bank_id, transaction_date, amount] + type_params
        
        cursor.execute(query, params)
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


def get_transactions_by_date_type(bank_id, transaction_date, transaction_type):
    """Get all transactions by date and transaction type without considering amount"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # استفاده از TransactionTypeMapper
        type_condition, type_params = TransactionTypeMapper.create_type_condition_sql(transaction_type)
        
        query = f"""
            SELECT * FROM AccountingTransactions 
            WHERE bank_id = ? 
            AND due_date = ?
            AND {type_condition}
            AND is_reconciled = 0
        """
        params = [bank_id, transaction_date] + type_params
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logger.info(f"Found {len(result)} transactions of type {transaction_type} on date {transaction_date}")
        return result
    except Exception as e:
        logger.error(f"Error getting transactions by date and type: {str(e)}")
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
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        # استفاده از TransactionTypeMapper
        type_condition, type_params = TransactionTypeMapper.create_type_condition_sql(transaction_type)
        
        query = f"""
            SELECT * FROM AccountingTransactions 
            WHERE bank_id = ? 
            AND transaction_amount = ?
            AND {type_condition}
            AND is_reconciled = 0
        """
        params = [bank_id, amount] + type_params
        
        cursor.execute(query, params)
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
        
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
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
        
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logger.info(f"تعداد {len(result)} تراکنش با تاریخ وصول بین {start_date} تا {end_date} یافت شد")
        return result
    except Exception as e:
        logger.error(f"خطا در دریافت تراکنش‌ها بر اساس تاریخ وصول: {str(e)}")
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
        
        # محاسبه تاریخ روز قبل
        pos_date = datetime.strptime(pos_transaction['transaction_date'], '%Y-%m-%d')
        previous_day = (pos_date - timedelta(days=1)).strftime('%Y-%m-%d')
        
        params = [previous_day, pos_transaction['amount']]

        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        matches = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logger.info(f"{len(matches)} potential matches found for POS transaction {pos_transaction['id']}.")

        return matches
    except Exception as e:
        logger.error(f"Error getting accounting transactions for POS: {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()


def search_transactions_by_customer_name(bank_id, customer_name, transaction_type=None):
    """جستجو بر اساس نام مشتری"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM AccountingTransactions WHERE bank_id = ? AND customer_name LIKE ?"
        params = [bank_id, f"%{customer_name}%"]
        
        if transaction_type:
            type_condition, type_params = TransactionTypeMapper.create_type_condition_sql(transaction_type)
            query += f" AND {type_condition}"
            params.extend(type_params)
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logger.info(f"Found {len(result)} transactions for customer '{customer_name}'")
        return result
    except Exception as e:
        logger.error(f"Error searching transactions by customer name: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()


def search_transactions_by_description(bank_id, description, transaction_type=None):
    """جستجو بر اساس توضیحات تراکنش"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM AccountingTransactions WHERE bank_id = ? AND description LIKE ?"
        params = [bank_id, f"%{description}%"]
        
        if transaction_type:
            type_condition, type_params = TransactionTypeMapper.create_type_condition_sql(transaction_type)
            query += f" AND {type_condition}"
            params.extend(type_params)
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        logger.info(f"Found {len(result)} transactions with description containing '{description}'")
        return result
    except Exception as e:
        logger.error(f"Error searching transactions by description: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()
