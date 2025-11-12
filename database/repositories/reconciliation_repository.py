"""
Repository برای عملیات مغایرت‌گیری مشترک
یکپارچه‌سازی کوئری‌های تکراری از فایل‌های مختلف reconciliation
"""
import logging
from database.init_db import create_connection
from utils.logger_config import setup_logger

# راه‌اندازی لاگر
logger = setup_logger('database.repositories.reconciliation')

class ReconciliationRepository:
    """
    Repository برای عملیات مغایرت‌گیری مشترک
    """

    @staticmethod
    def find_terminal_id_by_terminal_number(terminal_number):
        """
        پیدا کردن terminal_id از جدول PosTransactions بر اساس terminal_number
        
        Args:
            terminal_number: شماره ترمینال
            
        Returns:
            terminal_id یا None
        """
        conn = None
        try:
            conn = create_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT terminal_id FROM PosTransactions 
                WHERE terminal_number = ? 
                LIMIT 1
            """, (terminal_number,))
            
            result = cursor.fetchone()
            if result:
                return result[0]
            
            return None
            
        except Exception as e:
            logger.error(f"خطا در پیدا کردن terminal_id: {str(e)}")
            return None
        finally:
            if conn:
                conn.close()

    @staticmethod
    def find_accounting_by_terminal_id(bank_id, terminal_id, amount):
        """
        جستجوی رکورد حسابداری بر اساس terminal_id به عنوان شماره پیگیری
        
        Args:
            bank_id: شناسه بانک
            terminal_id: شناسه ترمینال
            amount: مبلغ تراکنش
            
        Returns:
            dict رکورد حسابداری یا None
        """
        conn = None
        try:
            conn = create_connection()
            cursor = conn.cursor()
            
            # تبدیل مبلغ منفی به مثبت برای مقایسه
            abs_amount = abs(float(amount))
            
            cursor.execute("""
                SELECT * FROM AccountingTransactions 
                WHERE bank_id = ? 
                AND transaction_number = ? 
                AND ABS(transaction_amount) = ?
                AND is_reconciled = 0
            """, (bank_id, str(terminal_id), abs_amount))
            
            columns = [description[0] for description in cursor.description]
            result = cursor.fetchone()
            
            if result:
                return dict(zip(columns, result))
            
            return None
            
        except Exception as e:
            logger.error(f"خطا در جستجوی حسابداری بر اساس terminal_id: {str(e)}")
            return None
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_transactions_by_collection_date_and_amount(bank_id, collection_date, amount, transaction_type):
        """
        دریافت تراکنش‌های حسابداری بر اساس collection_date و مبلغ
        
        Args:
            bank_id: شناسه بانک
            collection_date: تاریخ وصول
            amount: مبلغ تراکنش
            transaction_type: نوع تراکنش
            
        Returns:
            list لیست رکوردهای حسابداری
        """
        conn = None
        try:
            conn = create_connection()
            cursor = conn.cursor()
            
            # تبدیل مبلغ منفی به مثبت برای مقایسه
            abs_amount = abs(float(amount))
            
            cursor.execute("""
                SELECT * FROM AccountingTransactions 
                WHERE bank_id = ? 
                AND collection_date = ?
                AND transaction_amount = ?
                AND transaction_type = ?
                AND is_reconciled = 0
            """, (bank_id, collection_date, abs_amount, transaction_type))
            
            columns = [description[0] for description in cursor.description]
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            logger.info(f"یافت شد {len(result)} تراکنش حسابداری برای collection_date={collection_date}, amount={amount}")
            return result
            
        except Exception as e:
            logger.error(f"خطا در جستجوی تراکنش‌های حسابداری: {str(e)}")
            return []
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_accounting_by_date_amount_type_abs(bank_id, transaction_date, amount, transaction_type):
        """
        دریافت تراکنش‌های حسابداری با مقایسه مبلغ مطلق (برای حل مشکل مبالغ منفی بانک)
        
        Args:
            bank_id: شناسه بانک
            transaction_date: تاریخ تراکنش
            amount: مبلغ تراکنش
            transaction_type: نوع تراکنش
            
        Returns:
            list لیست رکوردهای حسابداری
        """
        conn = None
        try:
            conn = create_connection()
            cursor = conn.cursor()
            
            # تبدیل مبلغ منفی به مثبت برای مقایسه
            abs_amount = abs(float(amount))
            
            # تعیین نوع سیستم جدید
            new_system_type = ''
            if transaction_type in ['Pos', 'Received Transfer']:
                new_system_type = 'Pos / Received Transfer'
            elif transaction_type == 'Paid Transfer':
                new_system_type = 'Pos / Paid Transfer'
            
            cursor.execute("""
                SELECT * FROM AccountingTransactions 
                WHERE bank_id = ? 
                AND due_date = ?
                AND ABS(transaction_amount) = ?
                AND (transaction_type = ? OR transaction_type = ?)
                AND is_reconciled = 0
            """, (bank_id, transaction_date, abs_amount, transaction_type, new_system_type))
            
            columns = [description[0] for description in cursor.description]
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            logger.info(f"یافت شد {len(result)} تراکنش از نوع {transaction_type} با مبلغ مطلق {abs_amount} در تاریخ {transaction_date}")
            return result
            
        except Exception as e:
            logger.error(f"خطا در دریافت تراکنش‌ها با مبلغ مطلق: {str(e)}")
            return []
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_pos_transactions_by_terminal_and_date(terminal_number, date):
        """
        دریافت تراکنش‌های POS بر اساس شماره ترمینال و تاریخ
        
        Args:
            terminal_number: شماره ترمینال
            date: تاریخ تراکنش
            
        Returns:
            list لیست رکوردهای POS
        """
        conn = None
        try:
            conn = create_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM PosTransactions 
                WHERE terminal_number = ? 
                AND transaction_date = ?
                AND is_reconciled = 0
            """, (terminal_number, date))
            
            columns = [description[0] for description in cursor.description]
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            logger.info(f"یافت شد {len(result)} تراکنش POS برای terminal={terminal_number}, date={date}")
            return result
            
        except Exception as e:
            logger.error(f"خطا در دریافت تراکنش‌های POS: {str(e)}")
            return []
        finally:
            if conn:
                conn.close()

    @staticmethod
    def mark_pos_transactions_reconciled_by_terminal_date(terminal_id, pos_date):
        """
        علامت‌گذاری تمام تراکنش‌های POS مرتبط در آن روز به عنوان مغایرت‌گیری شده
        
        Args:
            terminal_id: شناسه ترمینال
            pos_date: تاریخ POS
            
        Returns:
            int تعداد رکوردهای به‌روزرسانی شده
        """
        conn = None
        try:
            conn = create_connection()
            cursor = conn.cursor()
            
            # پیدا کردن تمام تراکنش‌های POS با terminal_id و تاریخ مشخص
            cursor.execute("""
                SELECT id FROM PosTransactions 
                WHERE terminal_id = ? 
                AND transaction_date = ?
            """, (terminal_id, pos_date))
            
            pos_transactions = cursor.fetchall()
            
            # علامت‌گذاری هر تراکنش به عنوان reconciled
            from database.pos_transactions_repository import update_reconciliation_status
            
            for (pos_id,) in pos_transactions:
                update_reconciliation_status(pos_id, True)
                logger.debug(f"تراکنش POS {pos_id} به عنوان reconciled علامت‌گذاری شد")
            
            logger.info(f"{len(pos_transactions)} تراکنش POS برای terminal_id={terminal_id} در تاریخ {pos_date} reconciled شدند")
            return len(pos_transactions)
            
        except Exception as e:
            logger.error(f"خطا در علامت‌گذاری POS های مرتبط: {str(e)}")
            return 0
        finally:
            if conn:
                conn.close()

    @staticmethod
    def update_accounting_reconciliation_status(transaction_id, status):
        """
        به‌روزرسانی وضعیت مغایرت‌گیری تراکنش حسابداری
        
        Args:
            transaction_id: شناسه تراکنش
            status: وضعیت جدید (True/False)
            
        Returns:
            bool موفقیت عملیات
        """
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
                logger.debug(f"وضعیت تطبیق تراکنش حسابداری {transaction_id} به {status_int} تغییر کرد")
                return True
            else:
                logger.warning(f"تراکنش حسابداری با شناسه {transaction_id} یافت نشد")
                return False
                
        except Exception as e:
            logger.error(f"خطا در به‌روزرسانی وضعیت تطبیق تراکنش حسابداری: {str(e)}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

# Helper Functions برای common operations
class ReconciliationHelpers:
    """کلاس کمکی برای عملیات مشترک مغایرت‌گیری"""

    @staticmethod
    def verify_tracking_number(bank_transaction, accounting_transaction):
        """
        بررسی تطابق شماره پیگیری
        
        Args:
            bank_transaction: رکورد بانکی
            accounting_transaction: رکورد حسابداری
            
        Returns:
            bool تطابق شماره پیگیری
        """
        # شماره پیگیری در تراکنش حسابداری
        acc_tracking = str(accounting_transaction.get('transaction_number', ''))
        
        # شماره‌های پیگیری در تراکنش بانک
        bank_extracted_tracking = str(bank_transaction.get('extracted_tracking_number', ''))
        bank_reference = str(bank_transaction.get('reference_number', ''))
        bank_description = str(bank_transaction.get('description', ''))
        
        # بررسی تطابق
        if acc_tracking and (
            acc_tracking in bank_extracted_tracking or
            acc_tracking in bank_reference or  
            acc_tracking in bank_description
        ):
            return True
        
        return False

    @staticmethod
    def find_matching_by_tracking_number(bank_transaction, accounting_transactions):
        """
        پیدا کردن تراکنش حسابداری مناسب بر اساس شماره پیگیری
        
        Args:
            bank_transaction: رکورد بانکی
            accounting_transactions: لیست رکوردهای حسابداری
            
        Returns:
            dict رکورد تطبیق یافته یا None
        """
        for acc_transaction in accounting_transactions:
            if ReconciliationHelpers.verify_tracking_number(bank_transaction, acc_transaction):
                return acc_transaction
        
        return None

    @staticmethod
    def calculate_pos_date_from_bank_date(bank_date_str):
        """
        محاسبه تاریخ POS (یک روز کمتر از تاریخ بانک)
        
        Args:
            bank_date_str: تاریخ بانک به صورت رشته
            
        Returns:
            str تاریخ POS یا None
        """
        try:
            from datetime import datetime, timedelta
            # فرض می‌کنیم format تاریخ YYYY-MM-DD است
            bank_date = datetime.strptime(bank_date_str, '%Y-%m-%d')
            pos_date = bank_date - timedelta(days=1)
            return pos_date.strftime('%Y-%m-%d')
        except Exception as e:
            logger.error(f"خطا در محاسبه تاریخ POS: {str(e)}")
            return None