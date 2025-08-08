import sqlite3
import os
from config.settings import DB_PATH, DATA_DIR
from utils.logger_config import setup_logger

# راه‌اندازی لاگر برای ثبت عملیات دیتابیس
logger = setup_logger('database.init_db')
from utils.logger_config import setup_logger

# راه‌اندازی لاگر
logger = setup_logger('database.init_db')
from utils.logger_config import setup_logger

# راه‌اندازی لاگر
logger = setup_logger('database')

def create_connection():
    """ایجاد اتصال به دیتابیس"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        return conn
    except Exception as e:
        logger.error(f"خطا در اتصال به دیتابیس: {str(e)}")
        raise

def init_db():
    """راه‌اندازی اولیه دیتابیس و ایجاد جداول"""
    conn = None
    try:
        conn = create_connection()
        cursor = conn.cursor()
        logger.info("شروع ایجاد جداول دیتابیس")

        tables = {
            'BankTransactions': """
                CREATE TABLE IF NOT EXISTS BankTransactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bank_id INTEGER NOT NULL,
                    transaction_date TEXT,
                    transaction_time TEXT,
                    amount FLOAT NOT NULL,
                    description TEXT,
                    reference_number TEXT,
                    extracted_terminal_id TEXT,
                    extracted_tracking_number TEXT,
                    transaction_type TEXT,
                    is_reconciled BOOLEAN DEFAULT 0,
                    FOREIGN KEY (bank_id) REFERENCES Banks(id)
                )
            """,
        }
        # جدول بانک‌ها
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Banks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_name TEXT NOT NULL UNIQUE
            )
        """)
        # جدول ترمینال‌ها
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Terminals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                terminal_number TEXT NOT NULL UNIQUE,
                terminal_name TEXT NOT NULL UNIQUE
            )
        """)
        # جدول تراکنش‌های پوز
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS PosTransactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                terminal_number TEXT NOT NULL,
                bank_id INTEGER NOT NULL,
                card_number TEXT,
                transaction_date TEXT,
                transaction_amount FLOAT,
                tracking_number TEXT,
                is_reconciled BOOLEAN DEFAULT 0,
                FOREIGN KEY (bank_id) REFERENCES Banks(id)
            )
        """)
        # جدول تراکنش‌های حسابداری
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS AccountingTransactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                -- transaction_type can be 'income', 'expense', etc.
                transaction_number TEXT,
                transaction_amount FLOAT NOT NULL,
                due_date TEXT NOT NULL,
                collection_date TEXT,
                customer_name TEXT,
                description TEXT,
                is_reconciled BOOLEAN DEFAULT 0,
                FOREIGN KEY (bank_id) REFERENCES Banks(id)
            )
        """)
        conn.commit()
    except Exception as e:
        logger.error(f"خطا در ایجاد جداول دیتابیس: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
