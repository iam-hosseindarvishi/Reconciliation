import sqlite3
from typing import List, Dict, Any, Optional

class DatabaseManager:
    _instance = None

    def __new__(cls, db_path='reconciliation.db'):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db_path = db_path
            cls._instance.conn = None
            # اطمینان از ایجاد جداول در اولین نمونه
            cls._instance.setup_database()
        return cls._instance

    def __enter__(self):
        """ایجاد اتصال به پایگاه داده"""
        if self.conn is None:
            try:
                self.conn = sqlite3.connect(self.db_path)
                self.conn.row_factory = sqlite3.Row
            except sqlite3.Error as e:
                print(f"خطا در اتصال به پایگاه داده: {e}")
                raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """بستن اتصال پایگاه داده و مدیریت تراکنش‌ها"""
        if self.conn:
            try:
                if exc_type is None:
                    self.conn.commit()
                else:
                    self.conn.rollback()
            finally:
                self.conn.close()
                self.conn = None

    def setup_database(self):
        """یک بار در هنگام مقداردهی اولیه، جداول را ایجاد می‌کند"""
        with self:
            cursor = self.conn.cursor()
            self.create_tables(cursor)

    def create_tables(self, cursor):
        """ایجاد جداول پایگاه داده در صورتی که وجود نداشته باشند"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Banks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS BankTransactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                BankID INTEGER NOT NULL,
                Branch_Code TEXT,
                Branch_Name TEXT,
                Transaction_Date TEXT NOT NULL,
                Transaction_Time TEXT,
                Transaction_Type_Bank TEXT NOT NULL,
                Description_Bank TEXT,
                Reference_Number TEXT,
                Amount_Debit REAL,
                Amount_Credit REAL,
                is_reconciled INTEGER DEFAULT 0,
                FOREIGN KEY (BankID) REFERENCES Banks(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS PosTransactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                BankID INTEGER NOT NULL,
                Terminal_ID TEXT NOT NULL,
                Transaction_Date TEXT NOT NULL,
                Amount REAL NOT NULL,
                is_reconciled INTEGER DEFAULT 0,
                FOREIGN KEY (BankID) REFERENCES Banks(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS AccountingEntries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                BankID INTEGER NOT NULL,
                Branch_Code TEXT,
                Branch_Name TEXT,
                Entry_Number TEXT,
                Entry_Type_Acc TEXT NOT NULL,
                Document_Number TEXT,
                Document_Date TEXT,
                Accounting_Transaction_Date TEXT NOT NULL,
                Account_Reference_Suffix TEXT,
                Description_Notes_Acc TEXT,
                Price REAL NOT NULL,
                Date_Of_Receipt TEXT NULL,
                is_reconciled INTEGER DEFAULT 0,
                FOREIGN KEY (BankID) REFERENCES Banks(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ReconciliationResults (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_transaction_id INTEGER,
                accounting_entry_id INTEGER,
                pos_transaction_id INTEGER,
                reconciliation_type TEXT NOT NULL,
                reconciliation_date TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY (bank_transaction_id) REFERENCES BankTransactions(id),
                FOREIGN KEY (accounting_entry_id) REFERENCES AccountingEntries(id),
                FOREIGN KEY (pos_transaction_id) REFERENCES PosTransactions(id)
            )
        ''')

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """یک کوئری SELECT اجرا کرده و نتایج را به صورت دیکشنری برمی‌گرداند"""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def execute_update(self, query: str, params: tuple = ()) -> None:
        """یک کوئری INSERT, UPDATE, DELETE اجرا می‌کند"""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()

    def get_bank_id(self, bank_name: str) -> Optional[int]:
        """دریافت شناسه بانک بر اساس نام آن"""
        rows = self.execute_query('SELECT id FROM Banks WHERE name = ?', (bank_name,))
        return rows[0]['id'] if rows else None

    def add_bank(self, bank_name: str) -> int:
        """اضافه کردن یک بانک جدید و برگرداندن شناسه آن"""
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO Banks (name) VALUES (?)', (bank_name,))
        self.conn.commit()
        return cursor.lastrowid

    def get_or_create_bank(self, bank_name: str) -> int:
        """دریافت شناسه بانک موجود یا ایجاد یک بانک جدید"""
        bank_id = self.get_bank_id(bank_name)
        if bank_id is None:
            bank_id = self.add_bank(bank_name)
        return bank_id

    def bulk_insert_bank_transactions(self, data: List[Dict[str, Any]]) -> None:
        """درج دسته‌ای تراکنش‌های بانکی"""
        cursor = self.conn.cursor()
        cursor.executemany('''
            INSERT INTO BankTransactions (BankID, Branch_Code, Branch_Name, Transaction_Date, Transaction_Time, Transaction_Type_Bank, Description_Bank, Reference_Number, Amount_Debit, Amount_Credit)
            VALUES (:BankID, :Branch_Code, :Branch_Name, :Transaction_Date, :Transaction_Time, :Transaction_Type_Bank, :Description_Bank, :Reference_Number, :Amount_Debit, :Amount_Credit)
        ''', data)
        self.conn.commit()

    def bulk_insert_pos_transactions(self, data: List[Dict[str, Any]]) -> None:
        """درج دسته‌ای تراکنش‌های پوز"""
        cursor = self.conn.cursor()
        cursor.executemany('''
            INSERT INTO PosTransactions (BankID, Terminal_ID, Transaction_Date, Amount)
            VALUES (:BankID, :Terminal_ID, :Transaction_Date, :Amount)
        ''', data)
        self.conn.commit()

    def bulk_insert_accounting_entries(self, data: List[Dict[str, Any]]) -> None:
        """درج دسته‌ای اسناد حسابداری"""
        cursor = self.conn.cursor()
        cursor.executemany('''
            INSERT INTO AccountingEntries (BankID, Branch_Code, Branch_Name, Entry_Number, Entry_Type_Acc, Document_Number, Document_Date, Accounting_Transaction_Date, Account_Reference_Suffix, Description_Notes_Acc, Price, Date_Of_Receipt)
            VALUES (:BankID, :Branch_Code, :Branch_Name, :Entry_Number, :Entry_Type_Acc, :Document_Number, :Document_Date, :Accounting_Transaction_Date, :Account_Reference_Suffix, :Description_Notes_Acc, :Price, :Date_Of_Receipt)
        ''', data)
        self.conn.commit()

    def get_unreconciled_bank_transactions(self, bank_id: int, transaction_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """دریافت تراکنش‌های بانکی مغایرت‌گیری نشده با قابلیت فیلتر بر اساس نوع تراکنش"""
        query = 'SELECT * FROM BankTransactions WHERE BankID = ? AND is_reconciled = 0'
        params = [bank_id]
        if transaction_types:
            placeholders = ', '.join('?' for _ in transaction_types)
            query += f' AND Transaction_Type_Bank IN ({placeholders})'
            params.extend(transaction_types)
        return self.execute_query(query, tuple(params))

    def get_matching_accounting_entries_for_transfer(self, bank_id: int, normalized_bank_date: str, target_amount: float, target_acc_entry_type: str) -> List[Dict[str, Any]]:
        """بازیابی ورودی‌های حسابداری مغایرت‌گیری نشده برای حواله/فیش، بر اساس تاریخ، مبلغ، و نوع سند"""
        query = 'SELECT * FROM AccountingEntries WHERE is_reconciled = 0 AND BankID = ? AND Accounting_Transaction_Date = ? AND Price = ? AND Entry_Type_Acc = ?'
        return self.execute_query(query, (bank_id, normalized_bank_date, target_amount, target_acc_entry_type))

    def get_matching_accounting_entries_for_check(self, bank_id: int, normalized_date_of_receipt: str, amount: float, acc_type: str) -> List[Dict[str, Any]]:
        """بازیابی ورودی‌های حسابداری مغایرت‌گیری نشده برای چک، بر اساس تاریخ وصول، مبلغ، و نوع چک"""
        query = 'SELECT * FROM AccountingEntries WHERE is_reconciled = 0 AND BankID = ? AND Date_Of_Receipt = ? AND Price = ? AND Entry_Type_Acc = ?'
        return self.execute_query(query, (bank_id, normalized_date_of_receipt, amount, acc_type))

    def get_pos_transactions_by_terminal_and_date(self, bank_id: int, terminal_id: str, norm_date_pos: str) -> List[Dict[str, Any]]:
        """بازیابی تراکنش‌های پوز مغایرت‌گیری نشده برای یک ترمینال و تاریخ خاص"""
        query = 'SELECT * FROM PosTransactions WHERE is_reconciled = 0 AND BankID = ? AND Terminal_ID = ? AND Transaction_Date = ?'
        return self.execute_query(query, (bank_id, terminal_id, norm_date_pos))

    def get_pos_transactions_for_terminal(self, bank_id: int, terminal_id: str) -> List[Dict[str, Any]]:
        """بازیابی تمام تراکنش‌های پوز برای یک ترمینال و بانک مشخص (بدون فیلتر تاریخ یا وضعیت مغایرت)"""
        query = 'SELECT * FROM PosTransactions WHERE BankID = ? AND Terminal_ID = ?'
        return self.execute_query(query, (bank_id, terminal_id))

    def get_accounting_aggregate_pos_entry(self, bank_id: int, terminal_id: str, norm_bank_date: str) -> Optional[Dict[str, Any]]:
        """بازیابی رکورد سرجمع پوز از حسابداری"""
        query = """SELECT * FROM AccountingEntries 
                   WHERE is_reconciled = 0 AND BankID = ? AND Entry_Type_Acc='پوز دریافتنی' 
                   AND Account_Reference_Suffix = ? AND Description_Notes_Acc LIKE '%سرجمع%' 
                   AND Accounting_Transaction_Date = ?"""
        results = self.execute_query(query, (bank_id, terminal_id, norm_bank_date))
        return results[0] if results else None

    def get_matching_accounting_entries_for_pos_detail(self, bank_id: int, norm_pos_date: str, amount: float, suffix_6: str, suffix_5: str) -> List[Dict[str, Any]]:
        """بازیابی ورودی‌های حسابداری مغایرت‌گیری نشده برای جزئیات پوز (با استفاده از 5 یا 6 رقم آخر پیگیری)"""
        query = """SELECT * FROM AccountingEntries 
                   WHERE is_reconciled = 0 AND BankID = ? AND Accounting_Transaction_Date = ? 
                   AND Price = ? AND Entry_Type_Acc = 'پوز دریافتنی' 
                   AND (Account_Reference_Suffix = ? OR Account_Reference_Suffix = ?)"""
        return self.execute_query(query, (bank_id, norm_pos_date, amount, suffix_6, suffix_5))

    def update_bank_transaction_reconciled_status(self, transaction_id: int, status: int) -> None:
        """به‌روزرسانی وضعیت مغایرت یک تراکنش بانکی"""
        self.execute_update('UPDATE BankTransactions SET is_reconciled = ? WHERE id = ?', (status, transaction_id))

    def update_accounting_entry_reconciled_status(self, entry_id: int, status: int) -> None:
        """به‌روزرسانی وضعیت مغایرت یک سند حسابداری"""
        self.execute_update('UPDATE AccountingEntries SET is_reconciled = ? WHERE id = ?', (status, entry_id))

    def update_pos_transaction_reconciled_status(self, transaction_id: int, status: int) -> None:
        """به‌روزرسانی وضعیت مغایرت یک تراکنش پوز"""
        self.execute_update('UPDATE PosTransactions SET is_reconciled = ? WHERE id = ?', (status, transaction_id))

    def record_reconciliation_result(self, reconciliation_type: str, reconciliation_date: str, bank_transaction_id: Optional[int] = None, accounting_entry_id: Optional[int] = None, pos_transaction_id: Optional[int] = None, notes: Optional[str] = None) -> None:
        """ثبت نتیجه یک عملیات مغایرت‌گیری"""
        query = '''
            INSERT INTO ReconciliationResults (bank_transaction_id, accounting_entry_id, pos_transaction_id, reconciliation_type, reconciliation_date, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        self.execute_update(query, (bank_transaction_id, accounting_entry_id, pos_transaction_id, reconciliation_type, reconciliation_date, notes))