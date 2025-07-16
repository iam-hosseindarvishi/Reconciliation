#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ماژول مدیریت پایگاه داده
این ماژول مسئول ایجاد، اتصال و مدیریت پایگاه داده SQLite است.
"""

import os
import sqlite3
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd

from modules.logger import get_logger

# ایجاد شیء لاگر
logger = get_logger(__name__)


class DatabaseManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    """
    کلاس مدیریت پایگاه داده SQLite
    """
    
    def __init__(self, db_path: str = None):
        """
        مقداردهی اولیه کلاس DatabaseManager

        پارامترها:
            db_path: مسیر فایل پایگاه داده (اختیاری)
        """
        if not hasattr(self, 'initialized'):  # جلوگیری از مقداردهی مجدد
            # تنظیم مسیر پیش‌فرض پایگاه داده اگر مسیر ارائه نشده باشد
            if db_path is None:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                db_path = os.path.join(base_dir, 'data', 'reconciliation_db.sqlite')
            
            self.db_path = db_path
            self.connection = None
            self.cursor = None
            self.connect()
            self.initialized = True
    
    def connect(self) -> None:
        """
        ایجاد اتصال به پایگاه داده
        """
        try:
            # اطمینان از وجود دایرکتوری پایگاه داده
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # ایجاد اتصال به پایگاه داده
            self.connection = sqlite3.connect(self.db_path)
            self.cursor = self.connection.cursor()
            logger.info(f"اتصال به پایگاه داده برقرار شد: {self.db_path}")
        except Exception as e:
            logger.error(f"خطا در اتصال به پایگاه داده: {str(e)}")
            raise
    
    def disconnect(self) -> None:
        """
        قطع اتصال از پایگاه داده
        """
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None
            logger.info("اتصال به پایگاه داده قطع شد.")
    
    def setup_database(self) -> None:
        """
        ایجاد جداول پایگاه داده در صورت عدم وجود
        """
        try:
            if not self.connection:
                self.connect()
            
            # ایجاد جدول بانک‌ها
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Banks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    BankName TEXT UNIQUE NOT NULL,
                    BankCode TEXT UNIQUE
                )
            ''')
            
            # ایجاد جدول تراکنش‌های بانک
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS BankTransactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    BankID INTEGER NOT NULL,
                    Description_Bank TEXT,
                    Payer_Receiver TEXT,
                    Bank_Tracking_ID TEXT UNIQUE,
                    Shaparak_Deposit_Tracking_ID_Raw TEXT,
                    Balance REAL,
                    Deposit_Amount REAL,
                    Withdrawal_Amount REAL,
                    Branch_Code TEXT,
                    Time TEXT,
                    Date TEXT,
                    Extracted_Shaparak_Terminal_ID TEXT,
                    Transaction_Type_Bank TEXT,
                    is_reconciled BOOLEAN DEFAULT 0,
                    FOREIGN KEY (BankID) REFERENCES Banks(id)
                )
            ''')
            
            # ایجاد جدول تراکنش‌های پوز
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS PosTransactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    BankID INTEGER NOT NULL,
                    POS_Tracking_Number TEXT,
                    Card_Number TEXT,
                    Terminal_ID TEXT,
                    Terminal_Name TEXT,
                    Terminal_Identifier TEXT,
                    Transaction_Type TEXT,
                    Transaction_Amount REAL,
                    Transaction_Date TEXT,
                    Transaction_Time TEXT,
                    Transaction_Status TEXT,
                    is_reconciled BOOLEAN DEFAULT 0,
                    FOREIGN KEY (BankID) REFERENCES Banks(id),
                    UNIQUE(POS_Tracking_Number, Terminal_ID)
                )
            ''')
            
            # ایجاد جدول ورودی‌های حسابداری
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS AccountingEntries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    BankID INTEGER NOT NULL,
                    Entry_Type_Acc TEXT,
                    Account_Reference_Suffix INTEGER UNIQUE,
                    Debit REAL,
                    Credit REAL,
                    Due_Date TEXT,
                    Person_Name TEXT,
                    Check_Date TEXT,
                    Description_Notes_Acc TEXT,
                    Extracted_Card_Suffix_Acc TEXT,
                    is_reconciled BOOLEAN DEFAULT 0,
                    FOREIGN KEY (BankID) REFERENCES Banks(id)
                )
            ''')
            
            # ایجاد جدول نتایج مغایرت‌گیری
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS ReconciliationResults (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bank_transaction_id INTEGER,
                    pos_transaction_id INTEGER,
                    accounting_entry_id INTEGER,
                    reconciliation_type TEXT,
                    reconciliation_date TEXT,
                    notes TEXT,
                    FOREIGN KEY (bank_transaction_id) REFERENCES BankTransactions(id),
                    FOREIGN KEY (pos_transaction_id) REFERENCES PosTransactions(id),
                    FOREIGN KEY (accounting_entry_id) REFERENCES AccountingEntries(id)
                )
            ''')
            
            self.connection.commit()
            logger.info("جداول پایگاه داده با موفقیت ایجاد شدند.")
            
        except Exception as e:
            logger.error(f"خطا در راه‌اندازی پایگاه داده: {str(e)}")
            raise
        finally:
            pass  # اتصال را باز نگه می‌داریم
    
    def insert_bank_transactions(self, df: pd.DataFrame, bank_id: int) -> int:
        """
        درج داده‌های تراکنش بانک در پایگاه داده
        
        پارامترها:
            df: دیتافریم حاوی داده‌های تراکنش بانک
            bank_id: شناسه بانک
            
        خروجی:
            تعداد رکوردهای درج شده
        """
        try:
            if not self.connection:
                self.connect()
            inserted_count = 0
            
            for _, row in df.iterrows():
                try:
                    self.cursor.execute('''
                        INSERT OR IGNORE INTO BankTransactions (
                            BankID, Description_Bank, Payer_Receiver, Bank_Tracking_ID,
                            Shaparak_Deposit_Tracking_ID_Raw, Balance, Deposit_Amount,
                            Withdrawal_Amount, Branch_Code, Time, Date,
                            Extracted_Shaparak_Terminal_ID, Transaction_Type_Bank, is_reconciled
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        bank_id,
                        row.get('Description_Bank'),
                        row.get('Payer_Receiver'),
                        row.get('Bank_Tracking_ID'),
                        row.get('Shaparak_Deposit_Tracking_ID_Raw'),
                        row.get('Balance'),
                        row.get('Deposit_Amount'),
                        row.get('Withdrawal_Amount'),
                        row.get('Branch_Code'),
                        row.get('Time'),
                        row.get('Date'),
                        row.get('Extracted_Shaparak_Terminal_ID'),
                        row.get('Transaction_Type_Bank'),
                        False
                    ))
                    
                    if self.cursor.rowcount > 0:
                        inserted_count += 1
                        
                except sqlite3.IntegrityError:
                    # رکورد تکراری - نادیده گرفتن
                    logger.warning(f"رکورد تکراری بانک با شناسه پیگیری {row.get('Bank_Tracking_ID')} نادیده گرفته شد.")
                except Exception as e:
                    logger.error(f"خطا در درج رکورد بانک: {str(e)}")
            
            self.connection.commit()
            logger.info(f"{inserted_count} رکورد بانک با موفقیت درج شد.")
            return inserted_count
            
        except Exception as e:
            logger.error(f"خطا در درج داده‌های بانک: {str(e)}")
            raise
        finally:
            pass  # اتصال را باز نگه می‌داریم
    
    def insert_pos_transactions(self, df: pd.DataFrame, bank_id: int) -> int:
        """
        درج داده‌های تراکنش پوز در پایگاه داده
        
        پارامترها:
            df: دیتافریم حاوی داده‌های تراکنش پوز
            bank_id: شناسه بانک
            
        خروجی:
            تعداد رکوردهای درج شده
        """
        try:
            if not self.connection:
                self.connect()
            inserted_count = 0
            
            for _, row in df.iterrows():
                try:
                    self.cursor.execute('''
                        INSERT OR IGNORE INTO PosTransactions (
                            BankID, POS_Tracking_Number, Card_Number, Terminal_ID,
                            Terminal_Name, Terminal_Identifier, Transaction_Type,
                            Transaction_Amount, Transaction_Date, Transaction_Time,
                            Transaction_Status, is_reconciled
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        bank_id,
                        row.get('POS_Tracking_Number'),
                        row.get('Card_Number'),
                        row.get('Terminal_ID'),
                        row.get('Terminal_Name'),
                        row.get('Terminal_Identifier'),
                        row.get('Transaction_Type'),
                        row.get('Transaction_Amount'),
                        row.get('Transaction_Date'),
                        row.get('Transaction_Time'),
                        row.get('Transaction_Status'),
                        False
                    ))
                    
                    if self.cursor.rowcount > 0:
                        inserted_count += 1
                        
                except sqlite3.IntegrityError:
                    # رکورد تکراری - نادیده گرفتن
                    logger.warning(f"رکورد تکراری پوز با شناسه پیگیری {row.get('POS_Tracking_Number')} و ترمینال {row.get('Terminal_ID')} نادیده گرفته شد.")
                except Exception as e:
                    logger.error(f"خطا در درج رکورد پوز: {str(e)}")
            
            self.connection.commit()
            logger.info(f"{inserted_count} رکورد پوز با موفقیت درج شد.")
            return inserted_count
            
        except Exception as e:
            logger.error(f"خطا در درج داده‌های پوز: {str(e)}")
            raise
        finally:
            pass  # اتصال را باز نگه می‌داریم
    
    def insert_accounting_entries(self, df: pd.DataFrame, bank_id: int) -> int:
        """
        درج داده‌های حسابداری در پایگاه داده
        
        پارامترها:
            df: دیتافریم حاوی داده‌های حسابداری
            bank_id: شناسه بانک
            
        خروجی:
            تعداد رکوردهای درج شده
        """
        try:
            if not self.connection:
                self.connect()
            inserted_count = 0
            
            for _, row in df.iterrows():
                try:
                    self.cursor.execute('''
                        INSERT OR IGNORE INTO AccountingEntries (
                            BankID, Entry_Type_Acc, Account_Reference_Suffix, Debit,
                            Credit, Due_Date, Person_Name, Check_Date,
                            Description_Notes_Acc, Extracted_Card_Suffix_Acc, is_reconciled
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        bank_id,
                        row.get('Entry_Type_Acc'),
                        row.get('Account_Reference_Suffix'),
                        row.get('Debit'),
                        row.get('Credit'),
                        row.get('Due_Date'),
                        row.get('Person_Name'),
                        row.get('Check_Date'),
                        row.get('Description_Notes_Acc'),
                        row.get('Extracted_Card_Suffix_Acc'),
                        False
                    ))
                    
                    if self.cursor.rowcount > 0:
                        inserted_count += 1
                        
                except sqlite3.IntegrityError:
                    # رکورد تکراری - نادیده گرفتن
                    logger.warning(f"رکورد تکراری حسابداری با شماره {row.get('Account_Reference_Suffix')} نادیده گرفته شد.")
                except Exception as e:
                    logger.error(f"خطا در درج رکورد حسابداری: {str(e)}")
            
            self.connection.commit()
            logger.info(f"{inserted_count} رکورد حسابداری با موفقیت درج شد.")
            return inserted_count
            
        except Exception as e:
            logger.error(f"خطا در درج داده‌های حسابداری: {str(e)}")
            raise
        finally:
            pass  # اتصال را باز نگه می‌داریم
    
    def get_unreconciled_bank_transactions(self, bank_id: int = None) -> List[Dict[str, Any]]:
        """
        دریافت تراکنش‌های بانکی مغایرت‌گیری نشده
        
        پارامترها:
            bank_id: شناسه بانک (اختیاری - اگر مشخص نشود، همه بانک‌ها)
        
        خروجی:
            لیستی از دیکشنری‌های حاوی اطلاعات تراکنش‌های بانکی
        """
        try:
            self.connect()
            if bank_id:
                self.cursor.execute('''
                    SELECT * FROM BankTransactions WHERE is_reconciled = 0 AND BankID = ?
                ''', (bank_id,))
            else:
                self.cursor.execute('''
                    SELECT * FROM BankTransactions WHERE is_reconciled = 0
                ''')
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            return result
        except Exception as e:
            logger.error(f"خطا در دریافت تراکنش‌های بانکی مغایرت‌گیری نشده: {str(e)}")
            raise
        finally:
            self.disconnect()
    
    def get_unreconciled_pos_transactions(self, bank_id: int = None) -> List[Dict[str, Any]]:
        """
        دریافت تراکنش‌های پوز مغایرت‌گیری نشده
        
        پارامترها:
            bank_id: شناسه بانک (اختیاری - اگر مشخص نشود، همه بانک‌ها)
        
        خروجی:
            لیستی از دیکشنری‌های حاوی اطلاعات تراکنش‌های پوز
        """
        try:
            self.connect()
            if bank_id:
                self.cursor.execute('''
                    SELECT * FROM PosTransactions WHERE is_reconciled = 0 AND BankID = ?
                ''', (bank_id,))
            else:
                self.cursor.execute('''
                    SELECT * FROM PosTransactions WHERE is_reconciled = 0
                ''')
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            return result
        except Exception as e:
            logger.error(f"خطا در دریافت تراکنش‌های پوز مغایرت‌گیری نشده: {str(e)}")
            raise
        finally:
            self.disconnect()
    
    def get_unreconciled_accounting_entries(self, bank_id: int = None) -> List[Dict[str, Any]]:
        """
        دریافت ورودی‌های حسابداری مغایرت‌گیری نشده
        
        پارامترها:
            bank_id: شناسه بانک (اختیاری - اگر مشخص نشود، همه بانک‌ها)
        
        خروجی:
            لیستی از دیکشنری‌های حاوی اطلاعات ورودی‌های حسابداری
        """
        try:
            self.connect()
            if bank_id:
                self.cursor.execute('''
                    SELECT * FROM AccountingEntries WHERE is_reconciled = 0 AND BankID = ?
                ''', (bank_id,))
            else:
                self.cursor.execute('''
                    SELECT * FROM AccountingEntries WHERE is_reconciled = 0
                ''')
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            return result
        except Exception as e:
            logger.error(f"خطا در دریافت ورودی‌های حسابداری مغایرت‌گیری نشده: {str(e)}")
            raise
        finally:
            self.disconnect()
    
    def update_reconciliation_status(self, table: str, record_id: int, is_reconciled: bool) -> bool:
        """
        به‌روزرسانی وضعیت مغایرت‌گیری یک رکورد
        
        پارامترها:
            table: نام جدول (BankTransactions, PosTransactions, AccountingEntries)
            record_id: شناسه رکورد
            is_reconciled: وضعیت مغایرت‌گیری
            
        خروجی:
            موفقیت عملیات
        """
        try:
            self.connect()
            
            # بررسی اعتبار نام جدول
            valid_tables = ['BankTransactions', 'PosTransactions', 'AccountingEntries']
            if table not in valid_tables:
                logger.error(f"نام جدول نامعتبر: {table}")
                return False
            
            self.cursor.execute(f'''
                UPDATE {table} SET is_reconciled = ? WHERE id = ?
            ''', (is_reconciled, record_id))
            
            self.connection.commit()
            return self.cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"خطا در به‌روزرسانی وضعیت مغایرت‌گیری: {str(e)}")
            return False
        finally:
            self.disconnect()
    
    def record_reconciliation_result(self, bank_id: Optional[int], pos_id: Optional[int], 
                                    accounting_id: Optional[int], reconciliation_type: str, 
                                    notes: str = None) -> bool:
        """
        ثبت نتیجه مغایرت‌گیری
        
        پارامترها:
            bank_id: شناسه رکورد بانک (اختیاری)
            pos_id: شناسه رکورد پوز (اختیاری)
            accounting_id: شناسه رکورد حسابداری (اختیاری)
            reconciliation_type: نوع مغایرت‌گیری
            notes: یادداشت‌ها (اختیاری)
            
        خروجی:
            موفقیت عملیات
        """
        try:
            self.connect()
            
            from datetime import datetime
            reconciliation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.cursor.execute('''
                INSERT INTO ReconciliationResults (
                    bank_transaction_id, pos_transaction_id, accounting_entry_id,
                    reconciliation_type, reconciliation_date, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (bank_id, pos_id, accounting_id, reconciliation_type, reconciliation_date, notes))
            
            self.connection.commit()
            
            # به‌روزرسانی وضعیت مغایرت‌گیری رکوردها
            if bank_id:
                self.update_reconciliation_status('BankTransactions', bank_id, True)
            if pos_id:
                self.update_reconciliation_status('PosTransactions', pos_id, True)
            if accounting_id:
                self.update_reconciliation_status('AccountingEntries', accounting_id, True)
            
            return True
            
        except Exception as e:
            logger.error(f"خطا در ثبت نتیجه مغایرت‌گیری: {str(e)}")
            return False
        finally:
            self.disconnect()
    
    def get_reconciliation_statistics(self) -> Dict[str, int]:
        """
        دریافت آمار مغایرت‌گیری
        
        خروجی:
            دیکشنری حاوی آمار مغایرت‌گیری
        """
        try:
            self.connect()
            stats = {}
            
            # تعداد کل رکوردها
            self.cursor.execute("SELECT COUNT(*) FROM BankTransactions")
            stats['total_bank'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM PosTransactions")
            stats['total_pos'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM AccountingEntries")
            stats['total_accounting'] = self.cursor.fetchone()[0]
            
            # تعداد رکوردهای مغایرت‌گیری شده
            self.cursor.execute("SELECT COUNT(*) FROM BankTransactions WHERE is_reconciled = 1")
            stats['reconciled_bank'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM PosTransactions WHERE is_reconciled = 1")
            stats['reconciled_pos'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM AccountingEntries WHERE is_reconciled = 1")
            stats['reconciled_accounting'] = self.cursor.fetchone()[0]
            
            # تعداد رکوردهای مغایرت‌گیری نشده
            stats['unreconciled_bank'] = stats['total_bank'] - stats['reconciled_bank']
            stats['unreconciled_pos'] = stats['total_pos'] - stats['reconciled_pos']
            stats['unreconciled_accounting'] = stats['total_accounting'] - stats['reconciled_accounting']
            
            return stats
            
        except Exception as e:
            logger.error(f"خطا در دریافت آمار مغایرت‌گیری: {str(e)}")
            return {}
        finally:
            self.disconnect()
    
    def add_bank(self, bank_name: str, bank_code: str = None) -> bool:
        """
        افزودن بانک جدید
        
        پارامترها:
            bank_name: نام بانک
            bank_code: کد بانک (اختیاری)
            
        خروجی:
            موفقیت عملیات
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                INSERT INTO Banks (BankName, BankCode) VALUES (?, ?)
            ''', (bank_name, bank_code))
            
            self.connection.commit()
            logger.info(f"بانک '{bank_name}' با موفقیت اضافه شد.")
            return True
            
        except Exception as e:
            logger.error(f"خطا در افزودن بانک: {str(e)}")
            return False
        finally:
            self.disconnect()
    
    def get_all_banks(self) -> List[Dict[str, Any]]:
        """
        دریافت تمام بانک‌ها
        
        خروجی:
            لیستی از دیکشنری‌های حاوی اطلاعات بانک‌ها
        """
        try:
            self.connect()
            self.cursor.execute('''
                SELECT * FROM Banks ORDER BY BankName
            ''')
            columns = [desc[0] for desc in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
            return result
        except Exception as e:
            logger.error(f"خطا در دریافت لیست بانک‌ها: {str(e)}")
            return []
        finally:
            self.disconnect()
    
    def update_bank(self, bank_id: int, bank_name: str, bank_code: str = None) -> bool:
        """
        به‌روزرسانی اطلاعات بانک
        
        پارامترها:
            bank_id: شناسه بانک
            bank_name: نام جدید بانک
            bank_code: کد جدید بانک (اختیاری)
            
        خروجی:
            موفقیت عملیات
        """
        try:
            self.connect()
            
            self.cursor.execute('''
                UPDATE Banks SET BankName = ?, BankCode = ? WHERE id = ?
            ''', (bank_name, bank_code, bank_id))
            
            self.connection.commit()
            return self.cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"خطا در به‌روزرسانی بانک: {str(e)}")
            return False
        finally:
            self.disconnect()
    
    def delete_bank(self, bank_id: int) -> bool:
        """
        حذف بانک
        
        پارامترها:
            bank_id: شناسه بانک
            
        خروجی:
            موفقیت عملیات
        """
        try:
            self.connect()
            
            # بررسی وجود تراکنش‌های مرتبط با این بانک
            self.cursor.execute('''
                SELECT COUNT(*) FROM BankTransactions WHERE BankID = ?
            ''', (bank_id,))
            bank_transactions_count = self.cursor.fetchone()[0]
            
            self.cursor.execute('''
                SELECT COUNT(*) FROM PosTransactions WHERE BankID = ?
            ''', (bank_id,))
            pos_transactions_count = self.cursor.fetchone()[0]
            
            self.cursor.execute('''
                SELECT COUNT(*) FROM AccountingEntries WHERE BankID = ?
            ''', (bank_id,))
            accounting_entries_count = self.cursor.fetchone()[0]
            
            total_related_records = bank_transactions_count + pos_transactions_count + accounting_entries_count
            
            if total_related_records > 0:
                logger.warning(f"نمی‌توان بانک را حذف کرد. {total_related_records} رکورد مرتبط وجود دارد.")
                return False
            
            self.cursor.execute('''
                DELETE FROM Banks WHERE id = ?
            ''', (bank_id,))
            
            self.connection.commit()
            return self.cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"خطا در حذف بانک: {str(e)}")
            return False
        finally:
            self.disconnect()