import sqlite3
import os
from config.settings import DB_PATH, DATA_DIR

def create_connection():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    # جدول تراکنش‌های بانک
    cursor.execute("""
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
    """)
    conn = create_connection()
    cursor = conn.cursor()
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
            transaction_number TEXT,
            transaction_amount FLOAT NOT NULL,
            due_date TEXT NOT NULL,
            collection_date TEXT,
            counterparty_bank TEXT,
            customer_name TEXT,
            is_reconciled BOOLEAN DEFAULT 0,
            FOREIGN KEY (bank_id) REFERENCES Banks(id)
        )
    """)
    conn.commit()
    conn.close()
