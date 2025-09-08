import sqlite3
import os
from config.settings import DB_PATH, DATA_DIR
from utils.constants import BANKS
from utils.logger_config import setup_logger

# راه‌اندازی لاگر برای ثبت عملیات دیتابیس
logger = setup_logger('database.init_db')

def create_connection():
    """ایجاد اتصال به دیتابیس"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
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

      
        # جدول بانک‌ها
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Banks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_name TEXT NOT NULL UNIQUE
            )
        """)

        # افزودن بانک‌های پیش‌فرض
        try:
            for bank_key, bank_name in BANKS.items():
                cursor.execute("INSERT OR IGNORE INTO Banks (bank_name) VALUES (?)", (bank_name,))
            logger.info("بانک‌های پیش‌فرض با موفقیت اضافه شدند.")
        except Exception as e:
            logger.error(f"خطا در افزودن بانک‌های پیش‌فرض: {str(e)}")

          # جدول تراکنش‌های بانکی
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS BankTransactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_id INTEGER NOT NULL,
                transaction_date TEXT,
                transaction_time TEXT,
                amount FLOAT NOT NULL,
                description TEXT NULL,
                reference_number TEXT,
                extracted_terminal_id TEXT,
                extracted_tracking_number TEXT,
                transaction_type TEXT,
                source_card_number TEXT,
                is_reconciled BOOLEAN DEFAULT 0,
                FOREIGN KEY (bank_id) REFERENCES Banks(id)
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
                is_new_system BOOLEAN DEFAULT 0,
                is_reconciled BOOLEAN DEFAULT 0,
                FOREIGN KEY (bank_id) REFERENCES Banks(id)
            )
        """)
        # Reconciliation Results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ReconciliationResults (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pos_id INTEGER NULL,
                acc_id INTEGER NULL,
                bank_record_id INTEGER NULL,
                description TEXT NULL,
                type_matched TEXT NULL,
                date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pos_id) REFERENCES PosTransactions(id),
                FOREIGN KEY (acc_id) REFERENCES AccountingTransactions(id),
                FOREIGN KEY (bank_record_id) REFERENCES BankTransactions(id)
            )
        """)
        
        # جدول کارمزدهای تجمیع شده
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS BankFees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_id INTEGER NOT NULL,
                fee_date TEXT NOT NULL,
                total_amount FLOAT NOT NULL,
                transaction_count INTEGER NOT NULL,
                description TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
